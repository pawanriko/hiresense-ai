"""InsForge JWT authentication for the JSON API.

WHAT THIS IS: the credential check for "sign in with InsForge". The
React app signs the user in against InsForge (email + password, or
Google via InsForge) and sends the resulting access token on every API
call as ``Authorization: Bearer <token>``. This module verifies that
token and turns it into the Django user the rest of the app already
knows — so every view, every ``request.user`` check, and every
``owner`` foreign key works unchanged.

WHERE IT LIVES: this module + ``api/models.py`` (the
``InsforgeIdentity`` link table) + one MIDDLEWARE line in
``config/settings.py``. No view is modified: the middleware sets
``request.user`` before the view runs.

WHY JWKS, NOT A SHARED SECRET: InsForge signs access tokens with
RS256 (an asymmetric key pair) and publishes the public keys at
``/.well-known/jwks.json`` on the project URL. Django verifies the
signature with the PUBLIC key, so no secret ever has to live in this
codebase or in Render's env vars — and when InsForge rotates keys,
the ``kid`` header tells Django which public key to use. (Proven by
the Phase 0 spike against the real project; the old docs' HS256
table is stale.)

HOW IT WORKS, STEP BY STEP:
  1. The middleware runs on /api/ requests only, after Django's own
     AuthenticationMiddleware. In the DUAL window
     (INSFORGE_AUTH_ENABLED, INSFORGE_AUTH_REQUIRED off) a logged-in
     session user wins — the token is only consulted when the
     session says "anonymous". After CUTOVER (both flags on) the
     token is the ONLY credential for /api/: a session-only request
     is forced anonymous, and a bad token never falls back to the
     session. The HTML pages and /admin/ never pass through here,
     so they keep Django sessions in every state.
  2. ``verify_token`` checks the JWT header (must be RS256), fetches
     the JWKS document (cached, refetched once on an unknown ``kid``),
     and lets PyJWT verify the signature + expiry. InsForge tokens
     carry no ``iss``/``aud`` claims, so those are not checked; the
     ``role`` claim is not enforced either — Django's authorization
     is per-user ownership, not roles.
  3. ``resolve_user`` maps the verified ``sub`` claim to a Django
     user via InsforgeIdentity. Unknown ``sub`` + unused email ->
     a new Django user is created with an unusable password (it can
     never sign in with a password — InsForge owns the credential).
     Unknown ``sub`` + email that already belongs to an unlinked
     Django account -> 409: the link must come from the approved
     mapping (``link_insforge_users``), never silently, because with
     email verification off an email match alone proves nothing.
  4. A verified Bearer request is CSRF-exempt: the middleware sets
     ``request._dont_enforce_csrf_checks`` (the flag Django's own
     CsrfViewMiddleware honours). CSRF protection exists for cookie
     credentials — a Bearer token is not a cookie, it is not sent
     automatically by the browser, and a malicious site cannot read
     it out of this app's JS memory. The frontend therefore sends
     no CSRF header. HTML form posts (which carry no Bearer token)
     are unaffected — they still go through the CSRF check.

WHAT IT DOES NOT DO: it never mints tokens, never talks to InsForge
about passwords, and never revokes anything. Logout is the frontend
dropping the token (InsForge access tokens are stateless — the spike
proved a logged-out token stays valid until its 15-minute expiry).
"""

import json
import logging
import re
import time

import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.http import JsonResponse

from .models import InsforgeIdentity

logger = logging.getLogger(__name__)


class InsforgeAuthError(Exception):
    """The token is missing, malformed, expired, or badly signed."""


class InsforgeEmailCollision(InsforgeAuthError):
    """The token's email belongs to an unlinked Django account.

    Separate from InsforgeAuthError so the middleware can answer 409
    ("link pending") instead of the anonymous 401.
    """


# One process-wide JWKS cache: {keys: [...], fetched_at: monotonic}.
# gunicorn runs one worker by default on this project, and even with
# more workers each would just fetch its own copy — the document is
# public and tiny, so per-process caching is fine.
_jwks_cache = {"keys": None, "fetched_at": 0.0}


def _jwks_url():
    return settings.INSFORGE_BASE_URL.rstrip("/") + "/.well-known/jwks.json"


def _fetch_jwks(force=False):
    """Return the project's JWKS key list, cached for
    INSFORGE_JWKS_CACHE_TTL seconds. ``force=True`` refetches even
    when the cache is fresh (used on an unknown ``kid`` — rotation).
    Raises InsforgeAuthError on any fetch/parse failure.
    """
    now = time.monotonic()
    if (
        not force
        and _jwks_cache["keys"] is not None
        and now - _jwks_cache["fetched_at"] < settings.INSFORGE_JWKS_CACHE_TTL
    ):
        return _jwks_cache["keys"]
    try:
        response = requests.get(_jwks_url(), timeout=10)
        response.raise_for_status()
        keys = response.json().get("keys", [])
    except (requests.RequestException, ValueError) as exc:
        logger.warning("InsForge JWKS fetch failed: %s", exc)
        raise InsforgeAuthError("Could not fetch InsForge signing keys") from exc
    _jwks_cache.update({"keys": keys, "fetched_at": now})
    return keys


def _signing_key(kid):
    """The RSA public key for ``kid``, or None. Refetches once on a
    miss so a rotated key works without waiting out the cache TTL.
    """
    for attempt in range(2):
        for jwk in _fetch_jwks(force=attempt == 1):
            if jwk.get("kid") == kid:
                return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    return None


def verify_token(token):
    """Verify an InsForge access token. Returns the claims dict
    (``sub``, ``email``, ``role``, ``iat``, ``exp``) or raises
    InsforgeAuthError.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise InsforgeAuthError("Malformed token") from exc
    if header.get("alg") != "RS256":
        raise InsforgeAuthError("Unexpected signing algorithm")
    key = _signing_key(header.get("kid"))
    if key is None:
        raise InsforgeAuthError("Unknown signing key")
    try:
        # No `aud` claim exists on InsForge tokens (spike-proven), so
        # audience verification is off; `exp` + `sub` are required.
        # `leeway` tolerates the ~1-2s clock skew between InsForge's
        # servers and this one (see INSFORGE_JWT_LEEWAY in settings).
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False, "require": ["exp", "sub"]},
            leeway=settings.INSFORGE_JWT_LEEWAY,
        )
    except jwt.PyJWTError as exc:
        raise InsforgeAuthError("Token verification failed") from exc


def _unique_username(email):
    """A Django username derived from the email's local part, made
    unique with a numeric suffix if the base is taken. Usernames are
    display-only after the swap (sign-in uses email), so the exact
    form does not matter — only uniqueness does.
    """
    base = re.sub(r"[^a-zA-Z0-9_.-]", "_", (email.split("@")[0] or "user"))
    base = base[:30] or "user"
    user_model = get_user_model()
    candidate, n = base, 0
    while user_model.objects.filter(username__iexact=candidate).exists():
        n += 1
        candidate = f"{base}_{n}"
    return candidate


def resolve_user(claims):
    """Map verified claims to a Django user (see module docstring).

    Raises InsforgeEmailCollision when the token's email already
    belongs to an unlinked Django account.
    """
    sub = claims["sub"]
    email = (claims.get("email") or "").strip()
    user_model = get_user_model()
    # RACE-SAFE creation, up to 3 attempts: two requests carrying
    # the same fresh token (a double-mounted app, or me() +
    # dashboard() fired together) can both pass the lookup below.
    # Creation runs in one transaction; a unique-constraint loss
    # means a concurrent request won the race (or took the
    # username) — loop back, re-look-up, and either return the
    # winner's row or retry with a fresh username.
    for _attempt in range(3):
        try:
            identity = InsforgeIdentity.objects.select_related("user").get(
                sub=sub
            )
        except InsforgeIdentity.DoesNotExist:
            identity = None
        if identity is not None:
            user = identity.user
            if email and user.email != email:
                user.email = email
                user.save(update_fields=["email"])
            return user
        if email and user_model.objects.filter(email__iexact=email).exists():
            raise InsforgeEmailCollision(
                "An account with this email already exists and is not "
                "linked to InsForge yet."
            )
        try:
            with transaction.atomic():
                user = user_model.objects.create_user(
                    username=_unique_username(email), email=email
                )
                # create_user with no password already sets an
                # unusable one; state it explicitly so the intent
                # survives a future reader's skim.
                user.set_unusable_password()
                user.save(update_fields=["password"])
                InsforgeIdentity.objects.create(
                    user=user, sub=sub, email=email
                )
        except IntegrityError:
            continue
        return user
    raise InsforgeAuthError("Could not provision a user for this token")


class InsforgeAuthMiddleware:
    """Set ``request.user`` from a verified InsForge Bearer token.

    Runs after AuthenticationMiddleware (see MIDDLEWARE in settings),
    on /api/ requests only. Inert unless INSFORGE_AUTH_ENABLED.
    Dual window (INSFORGE_AUTH_REQUIRED off): session users are
    untouched, and only session-anonymous requests carrying
    ``Authorization: Bearer`` are verified. Cutover (REQUIRED on):
    the Bearer token is the only credential — session-only requests
    are forced anonymous, and an unverifiable token never falls
    back to the session. An unverifiable token otherwise leaves the
    request anonymous (views answer 401 as before); an email
    collision short-circuits with 409.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self._authenticate(request)
        if response is not None:
            return response
        return self.get_response(request)

    def _authenticate(self, request):
        if not getattr(settings, "INSFORGE_AUTH_ENABLED", False):
            return None
        if not request.path.startswith("/api/"):
            return None
        required = getattr(settings, "INSFORGE_AUTH_REQUIRED", False)
        # Dual window, Phase 1 semantics preserved exactly: a
        # logged-in session wins and the token is never consulted.
        if not required and request.user.is_authenticated:
            return None
        auth = request.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.startswith("Bearer ") else ""
        if token:
            try:
                request.user = resolve_user(verify_token(token))
            except InsforgeEmailCollision as exc:
                return JsonResponse({"detail": str(exc)}, status=409)
            except InsforgeAuthError:
                if required:
                    request.user = AnonymousUser()
                return None
            # Verified: this request authenticates by token, not by
            # cookie, so Django's CSRF check does not apply (see
            # step 4 in the module docstring). The flag must be set
            # here, before the view layer runs CsrfViewMiddleware's
            # process_view — middleware __call__ code always runs
            # first, whatever the MIDDLEWARE order.
            request._dont_enforce_csrf_checks = True
            return None
        if required:
            # No usable token: after cutover a session cookie does
            # not authenticate an /api/ request. (Already-anonymous
            # requests are unaffected — AnonymousUser replaces
            # AnonymousUser.)
            request.user = AnonymousUser()
        return None
