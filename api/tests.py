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


from django.core.files.uploadedfile import SimpleUploadedFile


def make_docx_bytes():
    """Build a small but realistic resume .docx in memory, so upload
    tests exercise real parsing + scoring instead of a fake file."""
    from io import BytesIO

    from docx import Document

    doc = Document()
    doc.add_heading("Pawan Kumar", level=0)
    doc.add_paragraph("pawanriko@gmail.com | github.com/pawanriko | New Delhi")
    doc.add_heading("Summary", level=1)
    doc.add_paragraph(
        "BCA student building AI and web projects, learning DSA, "
        "Python, and JavaScript.")
    doc.add_heading("Skills", level=1)
    doc.add_paragraph("Python, Django, JavaScript, React, SQL, Git")
    doc.add_heading("Experience", level=1)
    doc.add_paragraph(
        "Built HireSense AI, an interview-prep platform used by 200 "
        "students, improving mock scores by 30%.")
    doc.add_paragraph(
        "Developed a Django resume scorer processing 50 resumes per minute.")
    doc.add_heading("Projects", level=1)
    doc.add_paragraph(
        "Created a task tracker app with React and Django serving 100 users.")
    doc.add_heading("Education", level=1)
    doc.add_paragraph("BCA, IITM Janakpuri, 2023 - 2026")
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


class ResumeApiTests(TestCase):
    def test_upload_docx_success(self):
        user = make_user("demo")
        self.client.force_login(user)
        response = self.client.post(
            "/api/resumes/upload/",
            {"file": SimpleUploadedFile(
                "resume.docx", make_docx_bytes())},
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["original_name"], "resume.docx")
        self.assertIsInstance(data["ats_score"], int)
        self.assertTrue(0 <= data["ats_score"] <= 100)
        names = [c["name"] for c in data["breakdown"]["categories"]]
        self.assertEqual(
            names,
            ["Sections", "Quantification", "Action verbs",
             "Contact & links", "Length & format"])

    def test_upload_txt_rejected(self):
        user = make_user("demo")
        self.client.force_login(user)
        response = self.client.post(
            "/api/resumes/upload/",
            {"file": SimpleUploadedFile("notes.txt", b"hello")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("PDF and DOCX", response.json()["detail"])

    def test_upload_no_file(self):
        user = make_user("demo")
        self.client.force_login(user)
        response = self.client.post("/api/resumes/upload/", {})
        self.assertEqual(response.status_code, 400)

    def test_upload_corrupt_pdf(self):
        user = make_user("demo")
        self.client.force_login(user)
        response = self.client.post(
            "/api/resumes/upload/",
            {"file": SimpleUploadedFile("broken.pdf", b"not a pdf at all")},
        )
        self.assertEqual(response.status_code, 400)

    def test_list_only_own(self):
        user = make_user("demo")
        other = make_user("other")
        make_resume(user, "mine.pdf", 60)
        make_resume(other, "theirs.pdf", 90)
        self.client.force_login(user)
        data = self.client.get("/api/resumes/").json()
        self.assertEqual(len(data["resumes"]), 1)
        self.assertEqual(data["resumes"][0]["original_name"], "mine.pdf")

    def test_detail_own_and_other_404(self):
        user = make_user("demo")
        other = make_user("other")
        mine = make_resume(user, "mine.pdf", 60)
        theirs = make_resume(other, "theirs.pdf", 90)
        self.client.force_login(user)
        detail = self.client.get(f"/api/resumes/{mine.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["ats_score"], 60)
        missing = self.client.get(f"/api/resumes/{theirs.id}/")
        self.assertEqual(missing.status_code, 404)

    def test_resumes_anonymous_is_401(self):
        self.assertEqual(self.client.get("/api/resumes/").status_code, 401)
        response = self.client.post(
            "/api/resumes/upload/",
            {"file": SimpleUploadedFile(
                "resume.docx", make_docx_bytes())},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            self.client.get("/api/resumes/1/").status_code, 401)
