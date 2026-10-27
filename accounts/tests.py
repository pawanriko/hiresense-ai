"""Tests for the accounts app: the demo seed command, plus Google OAuth.

``call_command`` runs a management command in-process, so tests can prove
``seed_demo`` works without touching a shell. ``authenticate`` checks the
password the same way the login view does (hashed comparison).

GOOGLE TESTS, AND WHAT THEY MOCK: the real Google flow needs a browser
round-trip to accounts.google.com, which tests must never do. So the
"configured" tests below flip the configuration ON with
``override_settings`` (fake id/secret — allauth only needs them to be
non-empty to build a settings-backed app) and, for the callback test,
mock exactly the two network calls: the code-for-token exchange and the
userinfo fetch. Everything else — state handling, user creation, login,
redirect — runs for real. The "unconfigured" tests use the default
settings (no env vars in the test environment) and prove the app degrades
gracefully instead of crashing.
"""

from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()

# Fake-but-plausible Google configuration, used with override_settings to
# switch Google OAuth ON inside tests without touching real credentials.
GOOGLE_ON = override_settings(
    GOOGLE_OAUTH_CONFIGURED=True,
    SOCIALACCOUNT_PROVIDERS={
        "google": {
            "APP": {"client_id": "test-client-id", "secret": "test-secret", "key": ""},
        },
    },
)

# What Google's userinfo endpoint would return for a test user. Both "id"
# and "sub" are included because allauth's Google provider reads the uid
# from one of them (the exact key changed across allauth versions).
GOOGLE_USERINFO = {
    "id": "12345",
    "sub": "12345",
    "email": "googletest@example.com",
    "verified_email": True,
    "name": "Google Test",
    "given_name": "Google",
    "family_name": "Test",
    "picture": "https://example.com/photo.jpg",
}


class SeedDemoTests(TestCase):
    def test_seed_creates_demo_user_with_working_password(self):
        call_command("seed_demo")
        user = User.objects.get(username="demo")
        self.assertEqual(user.email, "demo@hiresense.ai")
        self.assertIsNotNone(authenticate(username="demo", password="demo1234"))

    def test_seed_is_idempotent(self):
        call_command("seed_demo")
        call_command("seed_demo")
        self.assertEqual(User.objects.filter(username="demo").count(), 1)
        self.assertIsNotNone(authenticate(username="demo", password="demo1234"))


class DemoLoginTests(TestCase):
    """The demo login (slice 1) must keep working unchanged."""

    def test_demo_login_posts_to_dashboard(self):
        call_command("seed_demo")
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "demo", "password": "demo1234"},
        )
        self.assertRedirects(response, reverse("dashboard:home"))

    def test_anonymous_dashboard_redirect_lands_on_working_login_page(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertRedirects(
            response, reverse("accounts:login") + "?next=" + reverse("dashboard:home")
        )
        login_page = self.client.get(response.url)
        self.assertEqual(login_page.status_code, 200)
        self.assertContains(login_page, "Demo account")


class GoogleUnconfiguredTests(TestCase):
    """Keys absent (the default): no button, no crash, demo login intact."""

    def test_login_page_hides_google_button_and_says_so(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Sign in with Google")
        self.assertContains(response, "Google sign-in is not configured yet")

    def test_direct_google_login_url_redirects_to_login_page(self):
        response = self.client.get(reverse("google_login"))
        self.assertRedirects(response, reverse("accounts:login"))
        # Follow-up page shows the guard's explanation (messages render).
        followed = self.client.get(reverse("google_login"), follow=True)
        self.assertContains(followed, "Google sign-in isn")

    def test_direct_google_callback_url_redirects_to_login_page(self):
        response = self.client.get(reverse("google_callback"))
        self.assertRedirects(response, reverse("accounts:login"))


@GOOGLE_ON
class GoogleConfiguredTests(TestCase):
    """Keys present (fake values via override_settings): the flow appears."""

    def test_login_page_shows_google_button(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in with Google")
        self.assertContains(response, reverse("google_login"))

    def test_google_login_url_exists_and_posts_to_google(self):
        # GET shows allauth's "Continue" confirmation page (LOGIN_ON_GET
        # stays False on purpose — see settings.py), POST goes to Google.
        get_response = self.client.get(reverse("google_login"))
        self.assertEqual(get_response.status_code, 200)
        post_response = self.client.post(reverse("google_login"))
        self.assertEqual(post_response.status_code, 302)
        self.assertTrue(
            post_response.url.startswith(
                "https://accounts.google.com/o/oauth2/v2/auth"
            )
        )
        self.assertIn("client_id=test-client-id", post_response.url)

    def test_google_callback_creates_user_and_logs_them_in(self):
        from allauth.socialaccount.models import SocialAccount

        # Step 1: start the flow, so allauth stashes a state in the session.
        start = self.client.post(reverse("google_login"))
        state = parse_qs(urlparse(start.url).query)["state"][0]

        # Step 2: Google "calls back" with a code. Mock the two network
        # calls (token exchange, userinfo fetch); everything else is real.
        with (
            mock.patch(
                "allauth.socialaccount.providers.oauth2.client.OAuth2Client.get_access_token",
                return_value={"access_token": "fake-token"},
            ),
            mock.patch(
                "allauth.socialaccount.providers.google.views.GoogleOAuth2Adapter._fetch_user_info",
                return_value=GOOGLE_USERINFO,
            ),
        ):
            callback = self.client.get(
                reverse("google_callback"), {"code": "fake-code", "state": state}
            )
        self.assertRedirects(callback, reverse("dashboard:home"))

        user = User.objects.get(email="googletest@example.com")
        self.assertEqual(
            SocialAccount.objects.get(user=user, provider="google").uid, "12345"
        )
        # The test client is now authenticated as the new Google user.
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
