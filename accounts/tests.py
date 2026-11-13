"""Tests for the accounts app: the demo seed command + the HTML login.

``call_command`` runs a management command in-process, so tests can prove
``seed_demo`` works without touching a shell. ``authenticate`` checks the
password the same way the login view does (hashed comparison).

Google sign-in used to be tested here too (django-allauth); the InsForge
swap (Phase 5) removed allauth, and Google moved into InsForge — its
tests live with the InsForge auth tests in api/tests.py.
"""

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


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

    def test_anonymous_redirect_lands_on_working_login_page(self):
        # The React SPA owns / now (see SPA_ROUTES in config/urls.py), so
        # the old "dashboard home redirects to login" flow is checked
        # against an HTML page instead: anonymous visitors still end up
        # on a working login page that shows the demo account.
        response = self.client.get(reverse("resumes:upload"))
        self.assertRedirects(
            response, reverse("accounts:login") + "?next=" + reverse("resumes:upload")
        )
        login_page = self.client.get(response.url)
        self.assertEqual(login_page.status_code, 200)
        self.assertContains(login_page, "Demo account")
