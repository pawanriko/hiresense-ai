"""App config for the interview app (slice 3).

WHAT: this tells Django the app exists and what to call it in the admin.
WHY: an app must be registered here AND listed in INSTALLED_APPS, or
Django ignores its models, views, and templates entirely.
"""

from django.apps import AppConfig


class InterviewConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "interview"
