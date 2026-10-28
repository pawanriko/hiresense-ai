"""Tests for the React JSON API (slice A: auth + dashboard).

The Django test client does not enforce CSRF by default, so these
tests check the view logic (credentials, ownership, shapes) rather
than the CSRF handshake — the browser flow covers that (see
frontend/src/api.js, which fetches /api/auth/csrf/ first).
"""

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase

from applications.models import Application, GapTask
from resumes.models import Resume

User = get_user_model()


def make_user(username):
    return User.objects.create_user(username=username, password="pw123456")


def make_resume(owner, name="resume.pdf", score=56):
    resume = Resume(owner=owner, original_name=name, ats_score=score)
    resume.file.save(name, ContentFile(b"fake pdf bytes"), save=True)
    return resume


class AuthApiTests(TestCase):
    def test_csrf_endpoint_sets_cookie(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_me_anonymous(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.json(), {"authenticated": False})

    def test_login_success_then_me(self):
        make_user("demo")
        response = self.client.post(
            "/api/auth/login/",
            {"username": "demo", "password": "pw123456"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"username": "demo"})
        me = self.client.get("/api/auth/me/")
        self.assertEqual(
            me.json(), {"authenticated": True, "username": "demo"})

    def test_login_wrong_password(self):
        make_user("demo")
        response = self.client.post(
            "/api/auth/login/",
            {"username": "demo", "password": "wrong"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_logout_ends_session(self):
        make_user("demo")
        self.client.post(
            "/api/auth/login/",
            {"username": "demo", "password": "pw123456"},
            content_type="application/json",
        )
        response = self.client.post("/api/auth/logout/")
        self.assertEqual(response.status_code, 200)
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.json(), {"authenticated": False})


class DashboardApiTests(TestCase):
    def test_dashboard_anonymous_is_401(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 401)

    def test_dashboard_shape_and_counts(self):
        user = make_user("demo")
        make_resume(user, "a.pdf", 56)
        make_resume(user, "b.pdf", 70)
        Application.objects.create(
            owner=user, company="TestCorp", role="Intern",
            status=Application.STATUS_INTERVIEW)
        GapTask.objects.create(owner=user, title="Task 1")
        GapTask.objects.create(
            owner=user, title="Task 2", status=GapTask.STATUS_DONE)
        self.client.force_login(user)
        data = self.client.get("/api/dashboard/").json()
        self.assertEqual(len(data["resumes"]), 2)
        self.assertEqual(data["latest"]["original_name"], "b.pdf")
        self.assertEqual(data["latest"]["ats_score"], 70)
        self.assertEqual(data["open_tasks"], 1)
        self.assertEqual(data["done_tasks"], 1)
        self.assertEqual(data["app_counts"]["Interview"], 1)
        self.assertEqual(data["app_counts"]["Applied"], 0)

    def test_dashboard_shows_only_own_rows(self):
        user = make_user("demo")
        other = make_user("other")
        make_resume(other, "theirs.pdf", 90)
        self.client.force_login(user)
        data = self.client.get("/api/dashboard/").json()
        self.assertEqual(data["resumes"], [])
        self.assertIsNone(data["latest"])
