"""App config for the applications app (slice 4).

WHAT THIS APP DOES: the job-application tracker plus the gap-task
checklist — the two halves of the original app's Prep Dashboard that
slices 1–3 left out. Same one-app-per-feature pattern as the other apps.
"""

from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "applications"
