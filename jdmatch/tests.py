"""Tests for the JD Match flow (slice 2).

HOW THESE TESTS WORK: Django's TestCase gives a throwaway test database
and a test Client that makes requests without a real server. Resumes are
created directly with extracted_text (like slice 1's owner-only test does)
because scoring only reads extracted text, never the file itself.

RESUME TEXT used below: a frontend intern resume with a strong React
bullet ("Built a React dashboard used by 200 users") and no Docker
mention, so React scores 100 with a verbatim evidence quote and Docker
scores 0 with a gap fix action.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from resumes.models import Resume

from .models import JobDescription, MatchAnalysis

User = get_user_model()

RESUME_TEXT = "\n".join([
    "Asha Sharma asha@example.com github.com/ashasharma",
    "Summary",
    "BCA student building AI and web projects.",
    "Skills",
    "React, JavaScript, Git",
    "Experience",
    "Frontend Intern — Built a React dashboard used by 200 users. "
    "Wrote JavaScript utilities that reduced load time by 30%.",
    "Education",
    "BCA — Bachelor of Computer Applications, 2024",
])

# Long enough to pass the 30-character JD minimum, and it names React
# (a heuristic vocabulary skill) plus Docker (a tool the resume lacks).
JD_TEXT = (
    "We are hiring a Frontend Intern. You must have React experience "
    "and JavaScript skills. Docker experience is a plus for deployment work."
)


def formset_data(rows):
    """Build POST data for the criteria formset from a list of row dicts.

    Django formsets need management-form fields or they refuse the POST
    entirely — TOTAL_FORMS counts every row sent, INITIAL_FORMS counts the
    rows that already existed. Unchecked checkboxes are simply omitted.
    """
    data = {
        "form-TOTAL_FORMS": str(len(rows)),
        "form-INITIAL_FORMS": str(len(rows)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for i, row in enumerate(rows):
        data[f"form-{i}-name"] = row.get("name", "")
        # A browser always sends the <select> value, even for a blank row;
        # weight is left empty for blank rows, exactly like the real page.
        data[f"form-{i}-category"] = row.get("category", "skill")
        weight = row.get("weight", "")
        data[f"form-{i}-weight"] = "" if weight == "" else str(weight)
        if row.get("required"):
            data[f"form-{i}-required"] = "on"
        if row.get("delete"):
            data[f"form-{i}-DELETE"] = "on"
    return data


class JdMatchFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="demo", password="demo1234")
        self.other = User.objects.create_user(username="other", password="other1234")
        self.resume = Resume.objects.create(
            owner=self.user, original_name="resume.docx",
            extracted_text=RESUME_TEXT, ats_score=80, breakdown={},
        )

    def _make_jd(self, criteria=None):
        if criteria is None:
            criteria = [
                {"name": "React", "category": "skill", "weight": 50,
                 "required": True},
                {"name": "Docker", "category": "tool", "weight": 50,
                 "required": False},
            ]
        return JobDescription.objects.create(
            owner=self.user, title="Frontend Intern", company="Acme",
            raw_text=JD_TEXT, criteria=criteria,
        )

    def test_anonymous_index_redirects_to_login(self):
        response = self.client.get(reverse("jdmatch:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_create_jd_drafts_criteria(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("jdmatch:index"), {
            "title": "Frontend Intern", "company": "Acme", "raw_text": JD_TEXT,
        })
        jd = JobDescription.objects.get(owner=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("jdmatch:detail", kwargs={"pk": jd.pk}))
        names = [c["name"] for c in jd.criteria]
        self.assertIn("React", names)
        self.assertIn("JavaScript", names)
        # Drafted weights are normalised to sum exactly 100 (ported rule).
        self.assertEqual(sum(c["weight"] for c in jd.criteria), 100)

    def test_short_jd_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("jdmatch:index"), {
            "title": "Tiny", "company": "", "raw_text": "Too short.",
        })
        self.assertEqual(response.status_code, 200)  # form re-rendered
        self.assertContains(response, "at least 30 characters")
        self.assertEqual(JobDescription.objects.count(), 0)

    def test_edit_criteria_before_scoring(self):
        self.client.force_login(self.user)
        jd = self._make_jd()
        url = reverse("jdmatch:detail", kwargs={"pk": jd.pk})
        # The page renders 2 saved rows + 1 blank "add" row (extra=1), so
        # the POST carries exactly 3 rows: rename React and change its
        # weight, delete Docker, fill the blank row with Python.
        rows = [
            {"name": "React.js", "category": "skill", "weight": 70,
             "required": True},
            {"name": "Docker", "category": "tool", "weight": 50,
             "delete": True},
            {"name": "Python", "category": "skill", "weight": 30},
        ]
        data = formset_data(rows)
        data["form-INITIAL_FORMS"] = "2"
        data["action"] = "save_criteria"
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        jd.refresh_from_db()
        names = [c["name"] for c in jd.criteria]
        self.assertEqual(names, ["React.js", "Python"])
        self.assertEqual(jd.criteria[0]["weight"], 70)

    def test_blank_extra_row_is_ignored(self):
        # Leaving the blank "add" row empty must not save an empty criterion.
        self.client.force_login(self.user)
        jd = self._make_jd()
        url = reverse("jdmatch:detail", kwargs={"pk": jd.pk})
        rows = [
            {"name": "React", "category": "skill", "weight": 50,
             "required": True},
            {"name": "Docker", "category": "tool", "weight": 50},
            {},  # blank extra row, left empty
        ]
        data = formset_data(rows)
        data["form-INITIAL_FORMS"] = "2"
        data["action"] = "save_criteria"
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        jd.refresh_from_db()
        self.assertEqual(
            [c["name"] for c in jd.criteria], ["React", "Docker"])

    def test_run_match_scores_shows_evidence_and_gaps(self):
        self.client.force_login(self.user)
        jd = self._make_jd()
        url = reverse("jdmatch:detail", kwargs={"pk": jd.pk})
        response = self.client.post(url, {
            "action": "run_match", "resume": str(self.resume.pk),
        })
        analysis = MatchAnalysis.objects.get(owner=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("jdmatch:result", kwargs={"pk": analysis.pk}))
        # React: strong bullet with verb + number -> 100; Docker: absent -> 0.
        # Weighted average of 100 and 0 at equal weights is 50.
        self.assertEqual(analysis.match_score, 50)
        results = {r["name"]: r for r in analysis.criteria_results}
        self.assertEqual(results["React"]["score"], 100)
        self.assertEqual(results["React"]["status"], "strong")
        self.assertIn("React dashboard", results["React"]["evidence"])
        self.assertEqual(results["Docker"]["score"], 0)
        self.assertIsNone(results["Docker"]["evidence"])
        gaps = {g["criterion"]: g for g in analysis.gaps}
        self.assertIn("Docker", gaps)
        self.assertTrue(gaps["Docker"]["suggested_action"])
        result_page = self.client.get(
            reverse("jdmatch:result", kwargs={"pk": analysis.pk}))
        self.assertEqual(result_page.status_code, 200)
        self.assertContains(result_page, "50")
        self.assertContains(result_page, "React dashboard")
        self.assertContains(result_page, "Docker")

    def test_run_match_uses_edited_criteria(self):
        self.client.force_login(self.user)
        jd = self._make_jd()
        url = reverse("jdmatch:detail", kwargs={"pk": jd.pk})
        # First run: React 100 + Docker 0 at equal weights -> 50.
        self.client.post(url, {"action": "run_match",
                               "resume": str(self.resume.pk)})
        first = MatchAnalysis.objects.latest("created_at")
        self.assertEqual(first.match_score, 50)
        # Edit: drop Docker (the missing one), keep React alone -> 100.
        rows = [{"name": "React", "category": "skill", "weight": 100,
                 "required": True},
                {"name": "Docker", "category": "tool", "weight": 50,
                 "delete": True}]
        data = formset_data(rows)
        data["form-INITIAL_FORMS"] = "2"
        data["action"] = "save_criteria"
        self.client.post(url, data)
        self.client.post(url, {"action": "run_match",
                               "resume": str(self.resume.pk)})
        second = MatchAnalysis.objects.latest("created_at")
        self.assertEqual(second.match_score, 100)
        self.assertGreater(second.match_score, first.match_score)

    def test_run_match_without_criteria_fails_cleanly(self):
        self.client.force_login(self.user)
        jd = self._make_jd(criteria=[])
        url = reverse("jdmatch:detail", kwargs={"pk": jd.pk})
        response = self.client.post(url, {
            "action": "run_match", "resume": str(self.resume.pk),
        })
        self.assertEqual(response.status_code, 200)  # re-rendered, not saved
        self.assertContains(response, "no criteria yet")
        self.assertEqual(MatchAnalysis.objects.count(), 0)

    def test_run_match_rejects_foreign_resume(self):
        self.client.force_login(self.user)
        jd = self._make_jd()
        foreign = Resume.objects.create(
            owner=self.other, original_name="theirs.docx",
            extracted_text=RESUME_TEXT, ats_score=80, breakdown={},
        )
        url = reverse("jdmatch:detail", kwargs={"pk": jd.pk})
        response = self.client.post(url, {
            "action": "run_match", "resume": str(foreign.pk),
        })
        # The dropdown queryset excludes other users' resumes, so the
        # choice is invalid and nothing is scored or saved.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MatchAnalysis.objects.count(), 0)

    def test_redraft_replaces_edited_criteria(self):
        self.client.force_login(self.user)
        jd = self._make_jd(criteria=[
            {"name": "CustomThing", "category": "skill", "weight": 100,
             "required": False},
        ])
        url = reverse("jdmatch:detail", kwargs={"pk": jd.pk})
        response = self.client.post(url, {"action": "redraft"})
        self.assertEqual(response.status_code, 302)
        jd.refresh_from_db()
        names = [c["name"] for c in jd.criteria]
        self.assertNotIn("CustomThing", names)
        self.assertIn("React", names)

    def test_pages_are_owner_only(self):
        jd = self._make_jd()
        analysis = MatchAnalysis.objects.create(
            owner=self.user, resume=self.resume, jd=jd, match_score=50,
            criteria_results=[], gaps=[],
        )
        self.client.force_login(self.other)
        for url in [
            reverse("jdmatch:detail", kwargs={"pk": jd.pk}),
            reverse("jdmatch:result", kwargs={"pk": analysis.pk}),
        ]:
            self.assertEqual(self.client.get(url).status_code, 404)
        # And the other user's index links neither the JD nor the analysis.
        # (The JD form's own label mentions "Frontend Intern" as an example,
        # so the link URL — not the title text — is what proves ownership.)
        index = self.client.get(reverse("jdmatch:index"))
        self.assertNotContains(
            index, reverse("jdmatch:detail", kwargs={"pk": jd.pk}))
        self.assertNotContains(
            index, reverse("jdmatch:result", kwargs={"pk": analysis.pk}))

    def test_listing_is_newest_first(self):
        self.client.force_login(self.user)
        first = MatchAnalysis.objects.create(
            owner=self.user, resume=self.resume,
            jd=self._make_jd(), match_score=10,
            criteria_results=[], gaps=[],
        )
        second = MatchAnalysis.objects.create(
            owner=self.user, resume=self.resume,
            jd=self._make_jd(), match_score=90,
            criteria_results=[], gaps=[],
        )
        response = self.client.get(reverse("jdmatch:index"))
        body = response.content.decode()
        self.assertLess(body.index("90/100"), body.index("10/100"))
        self.assertNotEqual(first.pk, second.pk)


class AiDraftTests(TestCase):
    """AI criteria drafting: tried first when a key is configured,
    heuristic on any failure — mocked, never a real Groq call."""

    AI_CRITERIA = [
        {"name": "React", "category": "skill", "weight": 60,
         "required": True},
        {"name": "Teamwork", "category": "soft", "weight": 40,
         "required": False},
    ]

    def setUp(self):
        self.user = User.objects.create_user(username="demo", password="demo1234")
        self.client.force_login(self.user)

    @override_settings(GROQ_API_KEY="test-key")
    @patch("jdmatch.views.extract_criteria", return_value=AI_CRITERIA)
    def test_create_jd_uses_ai_draft_when_configured(self, _mock_ai):
        response = self.client.post(reverse("jdmatch:index"), {
            "title": "Frontend Intern", "company": "Acme", "raw_text": JD_TEXT,
        })
        self.assertEqual(response.status_code, 302)
        jd = JobDescription.objects.get(owner=self.user)
        self.assertEqual(jd.criteria, self.AI_CRITERIA)

    @override_settings(GROQ_API_KEY="test-key")
    @patch("jdmatch.views.extract_criteria", return_value=None)
    def test_create_jd_falls_back_to_heuristic_when_ai_fails(self, _mock_ai):
        self.client.post(reverse("jdmatch:index"), {
            "title": "Frontend Intern", "company": "Acme", "raw_text": JD_TEXT,
        })
        jd = JobDescription.objects.get(owner=self.user)
        names = [c["name"] for c in jd.criteria]
        self.assertIn("React", names)
        self.assertEqual(sum(c["weight"] for c in jd.criteria), 100)

    @override_settings(GROQ_API_KEY="test-key")
    @patch("jdmatch.views.extract_criteria", return_value=AI_CRITERIA)
    def test_redraft_uses_ai_draft_when_configured(self, _mock_ai):
        jd = JobDescription.objects.create(
            owner=self.user, title="Frontend Intern", company="Acme",
            raw_text=JD_TEXT, criteria=[],
        )
        response = self.client.post(
            reverse("jdmatch:detail", kwargs={"pk": jd.pk}),
            {"action": "redraft"},
        )
        self.assertEqual(response.status_code, 302)
        jd.refresh_from_db()
        self.assertEqual(jd.criteria, self.AI_CRITERIA)
