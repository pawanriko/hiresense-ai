"""Django-native session auth for the React frontend.

This replaces the InsForge browser SDK flow. The browser now holds a
Django session cookie (HttpOnly) plus a readable csrftoken cookie;
mutating requests send the token back as X-CSRFToken. Google/GitHub
sign-in is handled by django-allauth under /accounts/ and lands back
on the SPA with the same session cookie set.

Existing InsForge-created Django users keep their rows and data:
they can sign in with Google/GitHub when the provider email matches,
or set a first Django password through the reset flow below.
"""

import json
import re

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.http import JsonResponse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

User = get_user_model()


def configured_providers():
    providers = []
    if getattr(settings, "GOOGLE_OAUTH_CONFIGURED", False):
        providers.append("google")
    if getattr(settings, "GITHUB_OAUTH_CONFIGURED", False):
        providers.append("github")
    return providers


def user_payload(user):
    return {
        "authenticated": True,
        "username": user.username,
        "email": user.email,
        "providers": configured_providers(),
    }


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _unique_username(email):
    local = email.split("@", 1)[0].lower()
    base = re.sub(r"[^a-z0-9._-]", "-", local).strip(".-_") or "user"
    base = base[:140]
    candidate = base
    suffix = 2
    while User.objects.filter(username=candidate).exists():
        tail = f"-{suffix}"
        candidate = f"{base[:150 - len(tail)]}{tail}"
        suffix += 1
    return candidate


def _find_user_for_login(identifier):
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    user = User.objects.filter(username=identifier).first()
    if user is not None:
        return user
    return User.objects.filter(email__iexact=identifier).first()


@ensure_csrf_cookie
@require_GET
def csrf_view(request):
    return JsonResponse({"detail": "ok", "providers": configured_providers()})


@require_POST
def register_view(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"detail": "Enter a valid email address."}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse(
            {
                "detail": "An account with this email already exists. "
                "Sign in, or reset your password to set a new one."
            },
            status=409,
        )
    user = User(username=_unique_username(email), email=email)
    if name:
        parts = name.split(None, 1)
        user.first_name = parts[0][:150]
        user.last_name = parts[1][:150] if len(parts) > 1 else ""
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return JsonResponse({"detail": " ".join(exc.messages)}, status=400)
    user.set_password(password)
    user.save()
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse(user_payload(user), status=201)


@require_POST
def login_view(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    identifier = data.get("email") or data.get("username") or data.get("identifier") or ""
    password = data.get("password") or ""
    candidate = _find_user_for_login(identifier)
    user = None
    if candidate is not None:
        user = authenticate(request, username=candidate.username, password=password)
    if user is None or not user.is_active:
        return JsonResponse({"detail": "Invalid email or password."}, status=401)
    login(request, user)
    return JsonResponse(user_payload(user))


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"detail": "ok"})


@require_GET
def me_view(request):
    if request.user.is_authenticated:
        return JsonResponse(user_payload(request.user))
    return JsonResponse({"authenticated": False, "providers": configured_providers()})


@require_POST
def password_reset_request_view(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    email = (data.get("email") or "").strip().lower()
    # Always answer the same way so the endpoint cannot be used to
    # probe which emails have accounts.
    generic = {
        "detail": "If an account exists for that email, a password reset link has been sent."
    }
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse(generic)
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is not None:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = request.build_absolute_uri(f"/reset-password?uid={uid}&token={token}")
        send_mail(
            "Set your HireSense AI password",
            "Use this link to set a new HireSense AI password:\n\n"
            f"{reset_url}\n\n"
            "If you did not request this, ignore this email.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    return JsonResponse(generic)


@require_POST
def password_reset_confirm_view(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    uid = data.get("uid") or ""
    token = data.get("token") or ""
    password = data.get("password") or ""
    try:
        user_pk = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_pk)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return JsonResponse({"detail": "This reset link is invalid or has expired."}, status=400)
    if not default_token_generator.check_token(user, token):
        return JsonResponse({"detail": "This reset link is invalid or has expired."}, status=400)
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return JsonResponse({"detail": " ".join(exc.messages)}, status=400)
    user.set_password(password)
    user.save(update_fields=["password"])
    return JsonResponse({"detail": "Password updated. Sign in with your new password."})
