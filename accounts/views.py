"""Views for the accounts app.

WHAT'S HERE (AND WHAT ISN'T): Django ships ready-made login/logout views
(``django.contrib.auth.views``) — writing our own password checking would
be reinventing a security-critical wheel, badly. So we just subclass
LoginView to point it at our template, and use LogoutView as-is.

LOGIN FLOW: GET /accounts/login/ shows the form. POST checks the username
and password against Django's user table (passwords are stored hashed, never
plain). Success -> LOGIN_REDIRECT_URL (the dashboard). Failure -> the form
re-renders with an error, no redirect.

This login page serves ONLY the HTML pages and /admin/ (the dev
interface). The React app signs in through InsForge instead — email +
password or Google, handled in the browser by the InsForge SDK (see
frontend/src/insforge.js). Google sign-in used to live here via
django-allauth; the InsForge swap (Phase 5) removed allauth entirely,
and Google moved with the rest of auth into InsForge.
"""

from django.contrib.auth.views import LoginView, LogoutView


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
