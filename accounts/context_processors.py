"""Template context processors for the accounts app.

WHAT'S A CONTEXT PROCESSOR? A function Django calls on every request that
renders a template, whose return value is merged into that template's
variables. We use one here for a single flag, so templates never have to
know WHERE the Google keys live (environment, .env, settings) — they just
ask ``google_oauth_configured``.

WHY A FLAG AT ALL? django-allauth's ``{% provider_login_url "google" %}``
tag raises an error when no Google app is configured (there is nothing to
build a login URL from). So the login template must NOT render that tag
when the keys are absent — it checks this flag first. The flag is True
only when BOTH environment variables are set; one half of a key pair is
as useless as none, so both are required.
"""

from django.conf import settings


def google_oauth(request):
    """Expose ``google_oauth_configured`` to every template."""
    return {
        "google_oauth_configured": bool(
            getattr(settings, "GOOGLE_OAUTH_CONFIGURED", False)
        ),
    }
