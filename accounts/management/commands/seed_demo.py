"""Seed the demo account: ``python manage.py seed_demo``.

WHAT A MANAGEMENT COMMAND IS: a small script Django can run from the
command line (``manage.py <name>``). It lives in
``<app>/management/commands/<name>.py`` and its ``handle()`` method runs.
We use one here instead of a data migration because demo data is a
setup convenience, not part of the schema — migrations should only carry
schema and truly permanent data.

THE DEMO ACCOUNT mirrors the original app's public-by-design demo login:
username ``demo``, email ``demo@hiresense.ai``, password ``demo1234``.
Local learning only — never use these credentials on a public server.
Running the command twice is safe: it updates the existing user instead
of creating a duplicate.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create or refresh the demo login (demo / demo1234)."

    def handle(self, *args, **options):
        user, created = User.objects.update_or_create(
            username="demo",
            defaults={
                "email": "demo@hiresense.ai",
                "first_name": "Demo Candidate",
                "is_active": True,
            },
        )
        user.set_password("demo1234")  # hashed on save, never stored plain
        user.save()
        verb = "Created" if created else "Refreshed"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} demo user: demo / demo1234 (email demo@hiresense.ai)"
        ))
