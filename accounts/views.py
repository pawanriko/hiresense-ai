"""Views for the accounts app.

WHAT'S HERE (AND WHAT ISN'T): Django ships ready-made login/logout views
(``django.contrib.auth.views``) — writing our own password checking would
be reinventing a security-critical wheel, badly. So we just subclass
LoginView to point it at our template, and use LogoutView as-is. No real
OAuth yet (Google sign-in is a later slice); the demo login below covers
learning and demos.

LOGIN FLOW: GET /accounts/login/ shows the form. POST checks the username
and password against Django's user table (passwords are stored hashed, never
plain). Success -> LOGIN_REDIRECT_URL (the dashboard). Failure -> the form
re-renders with an error, no redirect.

GOOGLE FLOW (django-allauth, added after slice 4): the login template
shows a "Sign in with Google" button ONLY when GOOGLE_OAUTH_CONFIGURED is
True (both env vars set). Clicking it goes to allauth's Google login URL,
which shows a "Continue" confirmation page, then redirects to Google,
then Google redirects back to /accounts/google/login/callback/, and
allauth creates (first time) or reuses the Django user and logs them in.
The two guard views below sit in front of allauth's Google URLs: when the
keys are absent, allauth would crash looking up a Google app that does
not exist, so the guards redirect to our login page with a message
instead. When the keys ARE present, the guards simply hand the request to
allauth's own views, unchanged.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect


class DemoLoginView(LoginView):
    """Django's login view, pointed at our template.

    The template gets a ``form`` (username + password) and a ``next``
    value (where to go after login). Everything else — session cookies,
    password hashing, brute-force-safe error messages — is Django's.
    """

    template_name = "accounts/login.html"


class DemoLogoutView(LogoutView):
    """Logs out on POST only (Django 5 removed GET logout: a plain link
    could otherwise log you out via a malicious image or preview). The
    header in base.html therefore uses a tiny POST form, not a link."""

    template_name = "accounts/logged_out.html"


def _google_guard(request, allauth_view_name):
    """Shared guard for allauth's Google URLs (see module docstring).

    ``allauth_view_name`` is "oauth2_login" or "oauth2_callback" — the
    function views allauth builds for Google. The import lives inside the
    function so that importing accounts.views never depends on allauth's
    provider modules being importable at startup.
    """
    if not settings.GOOGLE_OAUTH_CONFIGURED:
        messages.info(
            request,
            "Google sign-in isn't set up yet — sign in with the demo "
            "account, or add GOOGLE_OAUTH_CLIENT_ID and "
            "GOOGLE_OAUTH_CLIENT_SECRET (see the README's Google OAuth "
            "section) and restart the server.",
        )
        return redirect("accounts:login")
    from allauth.socialaccount.providers.google import views as google_views

    return getattr(google_views, allauth_view_name)(request)


def google_login_guard(request):
    """Front door for /accounts/google/login/ (see _google_guard)."""
    return _google_guard(request, "oauth2_login")


def google_callback_guard(request):
    """Front door for /accounts/google/login/callback/ (see _google_guard)."""
    return _google_guard(request, "oauth2_callback")
