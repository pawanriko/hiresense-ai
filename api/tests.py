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
from jdmatch.models import JobDescription
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

    def test_register_creates_hashed_user_and_signs_in(self):
        response = self.client.post(
            "/api/auth/register/",
            {"username": "pawan", "password": "Str0ng!Pass99"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"username": "pawan"})
        user = User.objects.get(username="pawan")
        # Stored hashed, never as plaintext, and verifiable.
        self.assertNotEqual(user.password, "Str0ng!Pass99")
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertTrue(user.check_password("Str0ng!Pass99"))
        # Registering also signs the new user in.
        me = self.client.get("/api/auth/me/")
        self.assertEqual(
            me.json(), {"authenticated": True, "username": "pawan"})

    def test_register_rejects_duplicate_username(self):
        make_user("demo")
        response = self.client.post(
            "/api/auth/register/",
            {"username": "Demo", "password": "Str0ng!Pass99"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(username__iexact="demo").count(), 1)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            "/api/auth/register/",
            {"username": "pawan", "password": "12345678"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="pawan").exists())

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


JD_TEXT = (
    "We are hiring a Frontend Intern. You will work with React and "
    "JavaScript to build user interfaces, and collaborate with the team. "
    "Experience with Python is a plus. Strong communication skills required."
)

RESUME_TEXT = (
    "Pawan Kumar\n"
    "pawanriko@gmail.com | github.com/pawanriko\n"
    "Summary\n"
    "BCA student building AI and web projects.\n"
    "Skills\n"
    "Python, Django, JavaScript, React, SQL, Git\n"
    "Experience\n"
    "Built HireSense AI with React and Django, used by 200 students, "
    "improving mock scores by 30%.\n"
    "Developed REST APIs with Python and Django serving 50 requests "
    "per minute.\n"
    "Education\n"
    "BCA, IITM Janakpuri, 2023 - 2026\n"
)


def make_parsed_resume(owner):
    """A resume whose extracted text is already filled in, so it is
    eligible for JD matching (the HTML run form's 'parsed' filter)."""
    resume = Resume(owner=owner, original_name="resume.pdf",
                    extracted_text=RESUME_TEXT, ats_score=90)
    resume.file.save("resume.pdf", ContentFile(b"fake pdf bytes"), save=True)
    return resume


def make_jd(owner, criteria=None):
    if criteria is None:
        criteria = [
            {"name": "React", "category": "skill", "weight": 35,
             "required": True},
            {"name": "Python", "category": "skill", "weight": 35,
             "required": False},
        ]
    return JobDescription.objects.create(
        owner=owner, title="Frontend Intern", company="TestCorp",
        raw_text=JD_TEXT, criteria=criteria)


class JDMatchApiTests(TestCase):
    def test_create_jd_drafts_criteria(self):
        user = make_user("demo")
        self.client.force_login(user)
        response = self.client.post(
            "/api/jdmatch/jds/",
            {"title": "Frontend Intern", "company": "TestCorp",
             "raw_text": JD_TEXT},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], "Frontend Intern")
        names = [c["name"] for c in data["criteria"]]
        # No AI keys on this machine, so the heuristic draft runs: the
        # JD text mentions React, Python, and communication.
        self.assertIn("React", names)
        self.assertIn("Python", names)
        self.assertIn("Communication", names)

    def test_create_jd_validation(self):
        user = make_user("demo")
        self.client.force_login(user)
        short = self.client.post(
            "/api/jdmatch/jds/",
            {"title": "Intern", "raw_text": "too short"},
            content_type="application/json",
        )
        self.assertEqual(short.status_code, 400)
        no_title = self.client.post(
            "/api/jdmatch/jds/",
            {"title": "  ", "raw_text": JD_TEXT},
            content_type="application/json",
        )
        self.assertEqual(no_title.status_code, 400)

    def test_criteria_save_and_validation(self):
        user = make_user("demo")
        jd = make_jd(user)
        self.client.force_login(user)
        response = self.client.put(
            f"/api/jdmatch/jds/{jd.id}/criteria/",
            {"criteria": [
                {"name": "React", "category": "skill", "weight": 50,
                 "required": True},
                {"name": "  ", "category": "skill", "weight": 50,
                 "required": False},
                {"name": "Django", "category": "skill", "weight": 50,
                 "required": False},
            ]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        # The blank-name row is dropped, like the HTML formset.
        self.assertEqual(
            [c["name"] for c in response.json()["criteria"]],
            ["React", "Django"])
        bad_category = self.client.put(
            f"/api/jdmatch/jds/{jd.id}/criteria/",
            {"criteria": [{"name": "X", "category": "magic", "weight": 10}]},
            content_type="application/json",
        )
        self.assertEqual(bad_category.status_code, 400)
        no_weight = self.client.put(
            f"/api/jdmatch/jds/{jd.id}/criteria/",
            {"criteria": [{"name": "X", "category": "skill"}]},
            content_type="application/json",
        )
        self.assertEqual(no_weight.status_code, 400)

    def test_redraft_and_other_user_404(self):
        user = make_user("demo")
        other = make_user("other")
        jd = make_jd(user, criteria=[])
        self.client.force_login(user)
        response = self.client.post(f"/api/jdmatch/jds/{jd.id}/redraft/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json()["criteria"]) > 0)
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(f"/api/jdmatch/jds/{jd.id}/").status_code, 404)

    def test_run_analysis_success(self):
        user = make_user("demo")
        jd = make_jd(user)
        resume = make_parsed_resume(user)
        self.client.force_login(user)
        response = self.client.post(
            "/api/jdmatch/analyses/",
            {"jd_id": jd.id, "resume_id": resume.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(0 < data["match_score"] <= 100)
        react = [r for r in data["criteria_results"]
                 if r["name"] == "React"][0]
        self.assertIsNotNone(react["evidence"])
        self.assertGreaterEqual(react["score"], 70)
        self.assertEqual(data["jd_title"], "Frontend Intern")
        self.assertEqual(data["resume_name"], "resume.pdf")

    def test_run_analysis_empty_criteria_400(self):
        user = make_user("demo")
        jd = make_jd(user, criteria=[])
        resume = make_parsed_resume(user)
        self.client.force_login(user)
        response = self.client.post(
            "/api/jdmatch/analyses/",
            {"jd_id": jd.id, "resume_id": resume.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_run_analysis_other_resume_404(self):
        user = make_user("demo")
        other = make_user("other")
        jd = make_jd(user)
        theirs = make_parsed_resume(other)
        self.client.force_login(user)
        response = self.client.post(
            "/api/jdmatch/analyses/",
            {"jd_id": jd.id, "resume_id": theirs.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_analyses_list_and_detail_ownership(self):
        user = make_user("demo")
        other = make_user("other")
        jd = make_jd(user)
        resume = make_parsed_resume(user)
        self.client.force_login(user)
        created = self.client.post(
            "/api/jdmatch/analyses/",
            {"jd_id": jd.id, "resume_id": resume.id},
            content_type="application/json",
        ).json()
        data = self.client.get("/api/jdmatch/analyses/").json()
        self.assertEqual(len(data["analyses"]), 1)
        self.client.force_login(other)
        self.assertEqual(len(
            self.client.get("/api/jdmatch/analyses/").json()["analyses"]), 0)
        self.assertEqual(
            self.client.get(
                f"/api/jdmatch/analyses/{created['id']}/").status_code, 404)

    def test_jdmatch_anonymous_is_401(self):
        self.assertEqual(
            self.client.get("/api/jdmatch/jds/").status_code, 401)
        self.assertEqual(
            self.client.get("/api/jdmatch/analyses/").status_code, 401)


ANSWER = (
    "I led a team of four students to build a college event website "
    "using React, delivering it two weeks early and increasing "
    "registrations by 40%."
)


def start_session(client, track="HR", difficulty="easy"):
    return client.post(
        "/api/interview/sessions/",
        {"track": track, "difficulty": difficulty},
        content_type="application/json",
    )


class InterviewApiTests(TestCase):
    def test_start_session_success(self):
        user = make_user("demo")
        self.client.force_login(user)
        response = start_session(self.client)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["track"], "HR")
        self.assertEqual(data["status"], "in_progress")
        # No AI keys on this machine, so the bank supplies the questions.
        self.assertEqual(data["question_source"], "bank")
        self.assertEqual(len(data["transcript"]), 5)
        self.assertTrue(all(i["answer"] is None for i in data["transcript"]))
        self.assertEqual(data["answered_count"], 0)
        self.assertIsNotNone(data["current"])

    def test_start_session_validation(self):
        user = make_user("demo")
        self.client.force_login(user)
        self.assertEqual(
            start_session(self.client, track="Magic").status_code, 400)
        self.assertEqual(
            start_session(self.client, difficulty="extreme").status_code, 400)

    def test_answer_flow_and_resume(self):
        user = make_user("demo")
        self.client.force_login(user)
        session = start_session(self.client).json()
        first_question = session["current"]["question"]
        response = self.client.post(
            f"/api/interview/sessions/{session['id']}/answer/",
            {"answer": ANSWER},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["answered_count"], 1)
        item = data["transcript"][0]
        self.assertEqual(item["answer"], ANSWER)
        self.assertIsInstance(item["overall"], int)
        self.assertTrue(item["feedback"])
        # No AI keys here, so the checklist scores it.
        self.assertEqual(item["source"], "checklist")
        # An abandoned session resumes at the next unanswered question.
        self.assertEqual(data["current"]["question"],
                         data["transcript"][1]["question"])
        self.assertNotEqual(data["current"]["question"], first_question)

    def test_answer_too_short(self):
        user = make_user("demo")
        self.client.force_login(user)
        session = start_session(self.client).json()
        response = self.client.post(
            f"/api/interview/sessions/{session['id']}/answer/",
            {"answer": "hi"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("few words", response.json()["detail"])

    def test_complete_flow_and_completed_unchanged(self):
        user = make_user("demo")
        self.client.force_login(user)
        session = start_session(self.client).json()
        data = session
        for _ in range(5):
            data = self.client.post(
                f"/api/interview/sessions/{session['id']}/answer/",
                {"answer": ANSWER},
                content_type="application/json",
            ).json()
        self.assertEqual(data["status"], "completed")
        self.assertIsInstance(data["overall_score"], int)
        self.assertEqual(data["report"]["feedback_source"], "checklist")
        self.assertIn("topic_scores", data["report"])
        self.assertIn("weakest_areas", data["report"])
        self.assertIn("weakest_question", data["report"])
        before = [i["answer"] for i in data["transcript"]]
        again = self.client.post(
            f"/api/interview/sessions/{session['id']}/answer/",
            {"answer": ANSWER},
            content_type="application/json",
        ).json()
        self.assertEqual(again["status"], "completed")
        self.assertEqual([i["answer"] for i in again["transcript"]], before)

    def test_session_ownership_and_anonymous(self):
        user = make_user("demo")
        other = make_user("other")
        self.client.force_login(user)
        session = start_session(self.client).json()
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(
                f"/api/interview/sessions/{session['id']}/").status_code, 404)
        self.assertEqual(len(
            self.client.get("/api/interview/sessions/").json()["sessions"]), 0)
        self.client.logout()
        self.assertEqual(
            self.client.get("/api/interview/sessions/").status_code, 401)


from applications.models import Application, GapTask
from interview.models import InterviewSession
from jdmatch.models import MatchAnalysis


def make_application(owner, company="TestCorp", role="Intern",
                     status="Applied"):
    return Application.objects.create(
        owner=owner, company=company, role=role, status=status)


class ApplicationsApiTests(TestCase):
    def test_create_and_counts(self):
        user = make_user("demo")
        self.client.force_login(user)
        response = self.client.post(
            "/api/applications/",
            {"company": "TestCorp", "role": "Frontend Intern",
             "status": "Interview", "notes": "Recruiter call done."},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["company"], "TestCorp")
        self.assertEqual(data["status"], "Interview")
        counts = self.client.get("/api/applications/").json()["counts"]
        self.assertEqual(counts["Interview"], 1)
        self.assertEqual(counts["Applied"], 0)

    def test_create_validation(self):
        user = make_user("demo")
        self.client.force_login(user)
        no_role = self.client.post(
            "/api/applications/",
            {"company": "TestCorp"},
            content_type="application/json",
        )
        self.assertEqual(no_role.status_code, 400)
        bad_status = self.client.post(
            "/api/applications/",
            {"company": "X", "role": "Y", "status": "Hired"},
            content_type="application/json",
        )
        self.assertEqual(bad_status.status_code, 400)
        other = make_user("other")
        jd = make_jd(other)
        bad_jd = self.client.post(
            "/api/applications/",
            {"company": "X", "role": "Y", "jd_id": jd.id},
            content_type="application/json",
        )
        self.assertEqual(bad_jd.status_code, 400)

    def test_edit_delete_and_reorder(self):
        user = make_user("demo")
        first = make_application(user, company="Alpha")
        make_application(user, company="Beta")
        self.client.force_login(user)
        # Editing bumps updated_at, moving the row to the top.
        updated = self.client.put(
            f"/api/applications/{first.id}/",
            {"status": "Offer"},
            content_type="application/json",
        ).json()
        self.assertEqual(updated["status"], "Offer")
        listed = self.client.get("/api/applications/").json()["applications"]
        self.assertEqual(listed[0]["company"], "Alpha")
        deleted = self.client.delete(f"/api/applications/{first.id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            self.client.get(f"/api/applications/{first.id}/").status_code,
            404)

    def test_applications_ownership(self):
        user = make_user("demo")
        other = make_user("other")
        app = make_application(other)
        self.client.force_login(user)
        self.assertEqual(len(
            self.client.get("/api/applications/").json()["applications"]), 0)
        self.assertEqual(
            self.client.get(f"/api/applications/{app.id}/").status_code, 404)

    def test_tasks_create_filter_toggle(self):
        user = make_user("demo")
        self.client.force_login(user)
        task = self.client.post(
            "/api/applications/tasks/",
            {"title": "Build a React project"},
            content_type="application/json",
        ).json()
        self.assertEqual(task["status"], "todo")
        done = self.client.put(
            f"/api/applications/tasks/{task['id']}/",
            {"status": "done"},
            content_type="application/json",
        ).json()
        self.assertEqual(done["status"], "done")
        open_list = self.client.get(
            "/api/applications/tasks/?filter=open").json()
        self.assertEqual(open_list["tasks"], [])
        self.assertEqual(open_list["done_count"], 1)
        done_list = self.client.get(
            "/api/applications/tasks/?filter=done").json()
        self.assertEqual(len(done_list["tasks"]), 1)
        bad = self.client.put(
            f"/api/applications/tasks/{task['id']}/",
            {"status": "finished"},
            content_type="application/json",
        )
        self.assertEqual(bad.status_code, 400)

    def test_push_analysis_gaps_skips_duplicates(self):
        user = make_user("demo")
        jd = make_jd(user)
        resume = make_parsed_resume(user)
        analysis = MatchAnalysis.objects.create(
            owner=user, resume=resume, jd=jd, match_score=50.0,
            criteria_results=[],
            gaps=[{"criterion": "Python", "current_status": "missing",
                   "suggested_action": "Add a Python project."}])
        self.client.force_login(user)
        first = self.client.post(
            f"/api/applications/push/analysis/{analysis.id}/").json()
        self.assertEqual(first["created"], 1)
        tasks = self.client.get("/api/applications/tasks/").json()["tasks"]
        self.assertEqual(tasks[0]["title"], "Close gap: Python")
        self.assertEqual(tasks[0]["source_gap"], "Add a Python project.")
        second = self.client.post(
            f"/api/applications/push/analysis/{analysis.id}/").json()
        self.assertEqual(second["created"], 0)

    def test_push_interview_areas_and_in_progress_zero(self):
        user = make_user("demo")
        completed = InterviewSession.objects.create(
            owner=user, track="HR", difficulty="easy",
            status=InterviewSession.STATUS_COMPLETED,
            report={"weakest_areas": ["Introduction", "Motivation"],
                    "topic_scores": [], "weakest_question": None,
                    "feedback_source": "checklist"},
            transcript=[])
        in_progress = InterviewSession.objects.create(
            owner=user, track="HR", difficulty="easy",
            transcript=[])
        self.client.force_login(user)
        pushed = self.client.post(
            f"/api/applications/push/interview/{completed.id}/").json()
        self.assertEqual(pushed["created"], 2)
        titles = [t["title"] for t in self.client.get(
            "/api/applications/tasks/").json()["tasks"]]
        self.assertIn("Practise interview topic: Introduction", titles)
        none = self.client.post(
            f"/api/applications/push/interview/{in_progress.id}/").json()
        self.assertEqual(none["created"], 0)

    def test_applications_anonymous_is_401(self):
        self.assertEqual(
            self.client.get("/api/applications/").status_code, 401)
        self.assertEqual(
            self.client.get("/api/applications/tasks/").status_code, 401)
