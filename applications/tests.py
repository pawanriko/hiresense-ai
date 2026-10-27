"""Tests for the Applications tracker + gap tasks (slice 4).

HOW THESE TESTS WORK: Django's TestCase gives a throwaway test database
and a test Client that makes requests without a real server. Fixtures
are built directly in setUp: two users, a JD + analysis with two gaps,
and a completed interview session with two weakest areas — the exact
inputs the push buttons turn into tasks.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from interview.models import InterviewSession
from jdmatch.models import JobDescription, MatchAnalysis
from resumes.models import Resume

from .models import Application, GapTask

User = get_user_model()

GAPS = [
    {"criterion": "Docker", "current_status": "missing",
     "suggested_action": "Ship one small thing with Docker."},
    {"criterion": "Kubernetes", "current_status": "missing",
     "suggested_action": "Ship one small thing with Kubernetes."},
]


class ApplicationsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("demo", password="demo1234")
        self.other = User.objects.create_user("other", password="demo1234")
        self.client.force_login(self.user)
        resume = Resume.objects.create(
            owner=self.user, original_name="resume.docx",
            extracted_text="x", ats_score=80, breakdown={},
        )
        jd = JobDescription.objects.create(
            owner=self.user, title="Frontend Intern",
            raw_text="We are hiring a Frontend Intern. " * 3, criteria=[],
        )
        self.analysis = MatchAnalysis.objects.create(
            owner=self.user, resume=resume, jd=jd, match_score=50.0,
            criteria_results=[], gaps=GAPS,
        )
        self.session = InterviewSession.objects.create(
            owner=self.user, track="HR", difficulty="medium",
            status=InterviewSession.STATUS_COMPLETED, overall_score=60,
            transcript=[],
            report={
                "topic_scores": [],
                "weakest_areas": ["Ownership", "Teamwork"],
                "weakest_question": None,
                "feedback_source": "checklist",
            },
        )

    # -- Applications: create / validation ---------------------------------

    def test_create_application_defaults_to_applied(self):
        response = self.client.post(reverse("applications:index"), {
            "action": "create", "company": "TestCorp", "role": "Intern",
            "status": "Applied", "notes": "", "jd": "",
        })
        self.assertEqual(response.status_code, 302)
        app = Application.objects.get(company="TestCorp")
        self.assertEqual(app.status, "Applied")
        self.assertEqual(app.owner, self.user)

    def test_create_requires_company_and_role(self):
        for data in (
            {"company": "", "role": "Intern"},
            {"company": "TestCorp", "role": ""},
        ):
            response = self.client.post(reverse("applications:index"), {
                "action": "create", "status": "Applied", "notes": "",
                "jd": "", **data,
            })
            self.assertEqual(response.status_code, 200)  # form re-shown
        self.assertEqual(Application.objects.count(), 0)

    def test_create_rejects_invented_status(self):
        response = self.client.post(reverse("applications:index"), {
            "action": "create", "company": "TestCorp", "role": "Intern",
            "status": "Dreaming", "notes": "", "jd": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Application.objects.count(), 0)

    # -- Applications: status change, edit, delete, ordering, counts ------

    def _make_app(self, company="A", role="R", status="Applied"):
        return Application.objects.create(
            owner=self.user, company=company, role=role, status=status
        )

    def test_status_change_from_list_and_invalid_ignored(self):
        app = self._make_app()
        response = self.client.post(reverse("applications:index"), {
            "action": "set_status", "application_id": str(app.pk),
            "status": "Interview",
        })
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, "Interview")
        # A crafted invalid status must not be saved.
        self.client.post(reverse("applications:index"), {
            "action": "set_status", "application_id": str(app.pk),
            "status": "Dreaming",
        })
        app.refresh_from_db()
        self.assertEqual(app.status, "Interview")

    def test_status_change_bumps_updated_order(self):
        # Recently updated first: touching the older row moves it on top.
        first = self._make_app(company="OldCo")
        self._make_app(company="NewCo")
        self.client.post(reverse("applications:index"), {
            "action": "set_status", "application_id": str(first.pk),
            "status": "Offer",
        })
        response = self.client.get(reverse("applications:index"))
        shown = list(response.context["applications"])
        self.assertEqual(shown[0].company, "OldCo")

    def test_status_counts_on_index(self):
        self._make_app(company="A", status="Applied")
        self._make_app(company="B", status="Interview")
        self._make_app(company="C", status="Interview")
        response = self.client.get(reverse("applications:index"))
        counts = response.context["counts"]
        self.assertEqual(
            counts, {"Applied": 1, "Interview": 2, "Offer": 0, "Rejected": 0}
        )

    def test_detail_edit_and_delete(self):
        app = self._make_app()
        url = reverse("applications:detail", kwargs={"pk": app.pk})
        response = self.client.post(url, {
            "action": "save", "company": "RenamedCo", "role": "Dev",
            "status": "Offer", "notes": "Onsite next week", "jd": "",
        })
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual((app.company, app.status), ("RenamedCo", "Offer"))
        response = self.client.post(url, {"action": "delete"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Application.objects.filter(pk=app.pk).exists())

    def test_applications_owner_only(self):
        app = self._make_app()
        self.client.force_login(self.other)
        detail = reverse("applications:detail", kwargs={"pk": app.pk})
        self.assertEqual(self.client.get(detail).status_code, 404)
        # Another user's row cannot be moved or deleted either.
        self.client.post(reverse("applications:index"), {
            "action": "set_status", "application_id": str(app.pk),
            "status": "Offer",
        })
        self.client.post(detail, {"action": "delete"})
        app.refresh_from_db()
        self.assertEqual(app.status, "Applied")
        self.assertTrue(Application.objects.filter(pk=app.pk).exists())
        # And the other user's index leaks nothing.
        response = self.client.get(reverse("applications:index"))
        self.assertEqual(list(response.context["applications"]), [])

    # -- Gap tasks: manual CRUD, toggle, status, filters -------------------

    def test_manual_task_create_toggle_and_status(self):
        response = self.client.post(reverse("applications:tasks"), {
            "action": "create", "title": "Build a Docker demo",
            "source_gap": "",
        })
        self.assertEqual(response.status_code, 302)
        task = GapTask.objects.get(title="Build a Docker demo")
        self.assertEqual(task.status, "todo")
        # Toggle: todo -> done -> todo.
        url = reverse("applications:tasks")
        self.client.post(url, {"action": "toggle", "task_id": str(task.pk)})
        task.refresh_from_db()
        self.assertEqual(task.status, "done")
        self.client.post(url, {"action": "toggle", "task_id": str(task.pk)})
        task.refresh_from_db()
        self.assertEqual(task.status, "todo")
        # Status dropdown also offers "doing" (the original's third state).
        self.client.post(url, {
            "action": "set_status", "task_id": str(task.pk),
            "status": "doing",
        })
        task.refresh_from_db()
        self.assertEqual(task.status, "doing")

    def test_task_title_capped_at_200(self):
        response = self.client.post(reverse("applications:tasks"), {
            "action": "create", "title": "x" * 201, "source_gap": "",
        })
        self.assertEqual(response.status_code, 200)  # form re-shown
        self.assertEqual(GapTask.objects.count(), 0)

    def test_task_filters(self):
        GapTask.objects.create(owner=self.user, title="open one")
        GapTask.objects.create(
            owner=self.user, title="done one", status="done"
        )
        url = reverse("applications:tasks")
        open_titles = [t.title for t in
                       self.client.get(url, {"filter": "open"})
                       .context["tasks"]]
        self.assertEqual(open_titles, ["open one"])
        done_titles = [t.title for t in
                       self.client.get(url, {"filter": "done"})
                       .context["tasks"]]
        self.assertEqual(done_titles, ["done one"])
        all_titles = [t.title for t in
                      self.client.get(url, {"filter": "all"})
                      .context["tasks"]]
        self.assertEqual(set(all_titles), {"open one", "done one"})

    # -- Gap tasks: pushes --------------------------------------------------

    def test_push_from_analysis_creates_exact_tasks_and_skips_dupes(self):
        url = reverse(
            "applications:push_from_analysis",
            kwargs={"pk": self.analysis.pk},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        tasks = GapTask.objects.filter(owner=self.user).order_by("title")
        self.assertEqual(
            [t.title for t in tasks],
            ["Close gap: Docker", "Close gap: Kubernetes"],
        )
        docker = tasks.get(title="Close gap: Docker")
        self.assertEqual(docker.source_gap, "Ship one small thing with Docker.")
        self.assertEqual(docker.analysis, self.analysis)
        # Pushing again adds nothing — the original's skip rule.
        self.client.post(url)
        self.assertEqual(GapTask.objects.count(), 2)

    def test_push_from_analysis_owner_only(self):
        self.client.force_login(self.other)
        url = reverse(
            "applications:push_from_analysis",
            kwargs={"pk": self.analysis.pk},
        )
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(GapTask.objects.count(), 0)

    def test_push_from_interview_creates_exact_tasks_and_skips_dupes(self):
        url = reverse(
            "applications:push_from_interview",
            kwargs={"pk": self.session.pk},
        )
        self.client.post(url)
        tasks = GapTask.objects.filter(owner=self.user).order_by("title")
        self.assertEqual(
            [t.title for t in tasks],
            ["Practise interview topic: Ownership",
             "Practise interview topic: Teamwork"],
        )
        ownership = tasks.get(title="Practise interview topic: Ownership")
        self.assertIn("Weakest area in your HR mock interview.",
                      ownership.source_gap)
        self.assertEqual(ownership.interview_session, self.session)
        self.client.post(url)
        self.assertEqual(GapTask.objects.count(), 2)

    def test_push_from_in_progress_interview_creates_nothing(self):
        session = InterviewSession.objects.create(
            owner=self.user, track="DSA", difficulty="easy",
            status=InterviewSession.STATUS_IN_PROGRESS, transcript=[],
            report={},
        )
        url = reverse(
            "applications:push_from_interview",
            kwargs={"pk": session.pk},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(GapTask.objects.count(), 0)

    # -- Dashboard counts ----------------------------------------------------

    def test_dashboard_open_and_done_counts(self):
        GapTask.objects.create(owner=self.user, title="open one")
        GapTask.objects.create(owner=self.user, title="doing one",
                               status="doing")
        GapTask.objects.create(owner=self.user, title="done one",
                               status="done")
        self._make_app(company="A", status="Applied")
        self._make_app(company="B", status="Offer")
        response = self.client.get(reverse("dashboard:home"))
        # Open means anything not done (todo + doing), like the original.
        self.assertEqual(response.context["open_tasks"], 2)
        self.assertEqual(response.context["done_tasks"], 1)
        self.assertEqual(
            response.context["app_counts"],
            {"Applied": 1, "Interview": 0, "Offer": 1, "Rejected": 0},
        )

    # -- Anonymous access -----------------------------------------------------

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        for url in (
            reverse("applications:index"),
            reverse("applications:tasks"),
            reverse(
                "applications:push_from_analysis",
                kwargs={"pk": self.analysis.pk},
            ),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/accounts/login/", response["Location"])
