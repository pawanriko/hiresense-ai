"""Link existing Django users to their InsForge identities.

WHY THIS EXISTS: Django user data (resumes, JDs, interviews,
applications) hangs off Django User rows, and InsForge sign-ins
arrive keyed by a different id (the JWT ``sub``). A user who signed
up the OLD way owns data under a Django row with no InsForge link —
if they sign in the NEW way first, the middleware sees an unknown
``sub`` + a taken email and answers 409 ("link pending") instead of
silently handing their data to whoever claimed the email (email
verification is off, so an email match alone proves nothing). This
command is the approved bridge: it links ONLY the email -> sub
pairs in an explicit mapping, supplied by the project owner.

WHERE THE MAPPING LIVES: the INSFORGE_LINK_MAP env var, a JSON
object of {"email": "insforge_sub"} pairs, set in Render's
dashboard (or --map on the command line for local runs). The subs
come from the InsForge dashboard / CLI user list. The mapping is
data, not code — it is never committed to the repo.

HOW IT RUNS IN PRODUCTION: render.yaml runs
``link_insforge_users --apply`` on every deploy, right after
seed_demo. With no mapping set it is a no-op. With a mapping it
links the listed pairs idempotently (re-running changes nothing).
Render's free tier has no Shell tab, so the build is the only way
to run it against production — the same pattern seed_demo uses.

MODES:
  * --report (default): read-only. Prints every Django user, their
    email, and their linked InsForge sub (or "unlinked"). Safe to
    run anywhere, any time.
  * --apply: validate EVERY pair first (unknown email, ambiguous
    email, sub already linked elsewhere, user already linked to a
    different sub — any of these aborts the WHOLE run with nothing
    applied), then link the pairs. All-or-nothing on purpose: a
    half-applied mapping is worse than none.
"""

import json
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from api.models import InsforgeIdentity


class Command(BaseCommand):
    help = "Report or apply InsForge identity links for existing users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--report",
            action="store_true",
            help="Read-only: list users and their link state (default).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Link users per the mapping (all-or-nothing).",
        )
        parser.add_argument(
            "--map",
            default="",
            help="JSON mapping {\"email\": \"sub\"} (overrides "
            "INSFORGE_LINK_MAP env var; local runs only).",
        )

    def handle(self, *args, **options):
        if options["apply"]:
            self._apply(options["map"])
        else:
            self._report()

    def _report(self):
        user_model = get_user_model()
        users = user_model.objects.order_by("username")
        linked = {i.user_id: i.sub for i in InsforgeIdentity.objects.all()}
        self.stdout.write("Django users and their InsForge links:")
        for user in users:
            sub = linked.get(user.pk)
            self.stdout.write(
                f"  {user.username} <{user.email or '-'}> -> "
                f"{sub if sub else 'UNLINKED'}"
            )
        self.stdout.write(
            f"{users.count()} user(s), {len(linked)} linked, "
            f"{users.count() - len(linked)} unlinked."
        )

    def _load_mapping(self, map_arg):
        raw = map_arg or os.environ.get("INSFORGE_LINK_MAP", "")
        if not raw.strip():
            return {}
        try:
            mapping = json.loads(raw)
        except ValueError as exc:
            raise CommandError(f"INSFORGE_LINK_MAP is not valid JSON: {exc}")
        if not isinstance(mapping, dict):
            raise CommandError("INSFORGE_LINK_MAP must be a JSON object.")
        for email, sub in mapping.items():
            if not isinstance(email, str) or not isinstance(sub, str):
                raise CommandError(
                    "INSFORGE_LINK_MAP keys and values must be strings."
                )
            if not email.strip() or not sub.strip():
                raise CommandError(
                    "INSFORGE_LINK_MAP must not contain empty emails/subs."
                )
        return {email.strip(): sub.strip() for email, sub in mapping.items()}

    def _apply(self, map_arg):
        mapping = self._load_mapping(map_arg)
        if not mapping:
            self.stdout.write("No mapping set; nothing to link.")
            return
        user_model = get_user_model()
        # VALIDATE EVERYTHING FIRST — nothing is written in this loop.
        planned = []
        problems = []
        for email, sub in sorted(mapping.items()):
            matches = list(
                user_model.objects.filter(email__iexact=email)
            )
            if not matches:
                problems.append(f"{email}: no Django user with this email")
                continue
            if len(matches) > 1:
                problems.append(
                    f"{email}: {len(matches)} Django users share this "
                    "email; ambiguous, refusing to choose"
                )
                continue
            user = matches[0]
            existing = InsforgeIdentity.objects.filter(user=user).first()
            if existing is not None and existing.sub != sub:
                problems.append(
                    f"{email}: user {user.username} is already linked "
                    f"to a different sub ({existing.sub[:8]}...)"
                )
                continue
            other = InsforgeIdentity.objects.filter(sub=sub).first()
            if other is not None and other.user_id != user.pk:
                problems.append(
                    f"{email}: sub {sub[:8]}... is already linked to "
                    f"user {other.user.username}"
                )
                continue
            planned.append((user, sub, existing is not None))
        if problems:
            for problem in problems:
                self.stderr.write(f"CONFLICT: {problem}")
            raise CommandError(
                f"{len(problems)} mapping problem(s); nothing was applied. "
                "Fix INSFORGE_LINK_MAP and redeploy."
            )
        # All pairs validated: apply.
        for user, sub, already in planned:
            if already:
                self.stdout.write(
                    f"  {user.username} <{user.email}>: already linked"
                )
                continue
            InsforgeIdentity.objects.create(
                user=user, sub=sub, email=user.email
            )
            self.stdout.write(
                f"  {user.username} <{user.email}>: linked to {sub[:8]}..."
            )
        self.stdout.write(f"Linked {len(planned)} user(s).")
