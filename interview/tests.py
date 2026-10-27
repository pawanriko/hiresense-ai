"""Tests for the interview app (slice 3).

WHAT: these prove the page behaves like the original's interview flow —
start a 5-question session, answer one question at a time, finish with a
report — without ever touching the AI scoring path. The checklist scorer
itself is tested in resumes/tests; here we test the page around it:
routing, saving, report math, and owner-only access.

HOW: Django's test Client pretends to be a browser (GET/POST, login,
redirects) against a throwaway test database, so no real data is touched.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from resumes.interview import (
    build_report,
    pick_questions,
    score_answer_checklist,
    topic_keywords,
)

from .models import InterviewSession

User = get_user_model()

# A strong, generic answer: starts with "I built" (confidence), carries
# STAR words (structure), numbers (depth of evidence), and stays short
# (conciseness). Its exact score varies by question keywords — tests that
# need an exact number compute it through the scorer, never by hand.
STRONG_ANSWER = (
    "I built a React dashboard for my college fest. My exact contribution "
    "was the frontend and the caching layer, which cut load time by 40 "
    "percent for 500 users. First I mapped the slow pages, then I rebuilt "
    "the data layer, and finally I measured the result because the outcome "
    "mattered to the organisers."
)


def make_session(owner, track="HR", difficulty="medium"):
    """A fresh in-progress session, exactly as the start view creates it."""
    questions = pick_questions(track, difficulty)
    transcript = [
        {
            "question": q["question"],
            "topic": q["topic"],
            "answer": None,
            "feedback": None,
            "scores": None,
            "overall": None,
        }
        for q in questions
    ]
    return InterviewSession.objects.create(
        owner=owner, track=track, difficulty=difficulty, transcript=transcript
    )


class StartTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="demo", password="demo1234")
        self.client = Client()
        self.client.force_login(self.user)

    def test_start_creates_five_question_session(self):
        response = self.client.post(
            reverse("interview:index"), {"track": "HR", "difficulty": "medium"}
        )
        self.assertEqual(response.status_code, 302)
        session = InterviewSession.objects.get(owner=self.user)
        self.assertEqual(session.status, "in_progress")
        self.assertEqual(len(session.transcript), 5)
        # Medium difficulty comes first in the original's ordering, so the
        # first question is the medium Ownership one, not an easy one.
        self.assertEqual(session.transcript[0]["topic"], "Ownership")
        self.assertIsNone(session.transcript[0]["answer"])
        self.assertEqual(
            response.url, reverse("interview:detail", kwargs={"pk": session.pk})
        )

    def test_start_invalid_difficulty_rejected(self):
        # ChoiceField validation: a value outside the offered choices never
        # reaches pick_questions, so no session is created at all.
        response = self.client.post(
            reverse("interview:index"), {"track": "HR", "difficulty": "impossible"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(InterviewSession.objects.filter(owner=self.user).exists())

    def test_start_invalid_track_rejected(self):
        response = self.client.post(
            reverse("interview:index"), {"track": "Cooking", "difficulty": "medium"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(InterviewSession.objects.filter(owner=self.user).exists())


class AnswerFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="demo", password="demo1234")
        self.client = Client()
        self.client.force_login(self.user)
        self.session = make_session(self.user)

    def detail_url(self):
        return reverse("interview:detail", kwargs={"pk": self.session.pk})

    def test_answer_scores_and_advances(self):
        response = self.client.post(self.detail_url(), {"answer": STRONG_ANSWER})
        self.assertEqual(response.status_code, 302)
        self.session.refresh_from_db()
        first = self.session.transcript[0]
        self.assertEqual(first["answer"], STRONG_ANSWER)
        self.assertIsNotNone(first["overall"])
        self.assertIsNotNone(first["feedback"])
        self.assertEqual(
            set(first["scores"]),
            {"relevance", "depth", "structure", "confidence", "conciseness"},
        )
        # The detail page now shows the SECOND question (first unanswered).
        page = self.client.get(self.detail_url())
        self.assertContains(page, "Question 2 of 5")
        self.assertContains(page, self.session.transcript[1]["question"])

    def test_short_answer_rejected(self):
        # Mirrors the original's "at least a few words" rule: a 2-character
        # answer fails validation and the transcript is untouched.
        response = self.client.post(self.detail_url(), {"answer": "hi"})
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertIsNone(self.session.transcript[0]["answer"])
        self.assertEqual(self.session.status, "in_progress")

    def test_full_session_report_math(self):
        # Answer all 5, then check the report aggregation (not the scorer:
        # expected per-answer overalls come from the scorer itself, and
        # the test proves the page aggregates them the original's way).
        for _ in range(5):
            response = self.client.post(self.detail_url(), {"answer": STRONG_ANSWER})
            self.assertEqual(response.status_code, 302)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "completed")
        transcript = self.session.transcript
        expected_overalls = [
            score_answer_checklist(
                item["question"], STRONG_ANSWER, topic_keywords(item["topic"])
            )["overall"]
            for item in transcript
        ]
        # The saved overalls must equal the scorer's, one per question.
        self.assertEqual(
            [item["overall"] for item in transcript], expected_overalls
        )
        import math

        expected_overall = math.floor(
            sum(expected_overalls) / len(expected_overalls) + 0.5
        )
        self.assertEqual(self.session.overall_score, expected_overall)
        report = self.session.report
        self.assertEqual(report["feedback_source"], "checklist")
        # Topic scores cover every topic in the session, weakest areas are
        # the 2 lowest, weakest question is the lowest overall answer.
        self.assertEqual(
            {t["topic"] for t in report["topic_scores"]},
            {item["topic"] for item in transcript},
        )
        self.assertEqual(len(report["weakest_areas"]), 2)
        self.assertEqual(
            report["weakest_question"]["overall"], min(expected_overalls)
        )
        page = self.client.get(self.detail_url())
        self.assertContains(page, "Interview report")
        self.assertContains(page, f"{expected_overall}/100")

    def test_answer_completed_session_changes_nothing(self):
        for _ in range(5):
            self.client.post(self.detail_url(), {"answer": STRONG_ANSWER})
        self.session.refresh_from_db()
        before = self.session.transcript
        response = self.client.post(self.detail_url(), {"answer": STRONG_ANSWER})
        # Friendlier than the original API's 409: redirect, no change.
        self.assertEqual(response.status_code, 302)
        self.session.refresh_from_db()
        self.assertEqual(self.session.transcript, before)
        self.assertEqual(self.session.status, "completed")

    def test_abandoned_session_resumes_without_crashing(self):
        self.client.post(self.detail_url(), {"answer": STRONG_ANSWER})
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "in_progress")
        page = self.client.get(self.detail_url())
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Question 2 of 5")
        index = self.client.get(reverse("interview:index"))
        self.assertContains(index, "in_progress")
        # In-progress sessions have no score yet — the listing must not
        # print a bogus "None/100".
        self.assertNotContains(index, "None/100")


class OwnerOnlyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="demo", password="demo1234")
        self.other = User.objects.create_user(username="intruder", password="x1234567")
        self.client = Client()
        self.session = make_session(self.user)

    def test_other_user_detail_is_404(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("interview:detail", kwargs={"pk": self.session.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_index_leaks_nothing_to_other_user(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("interview:index"))
        self.assertNotContains(response, "Ownership")
        self.assertNotContains(response, self.session.track + " · ")

    def test_anonymous_redirects_to_login(self):
        anon = Client()
        self.assertEqual(anon.get(reverse("interview:index")).status_code, 302)
        self.assertEqual(
            anon.get(
                reverse("interview:detail", kwargs={"pk": self.session.pk})
            ).status_code,
            302,
        )

    def test_newest_first_listing(self):
        from django.utils import timezone

        older = make_session(self.user)
        newer = make_session(self.user, track="DSA")
        # Force distinct timestamps: created_at is auto-set, so push the
        # older one back explicitly (update() skips auto_now_add).
        InterviewSession.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=1)
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("interview:index"))
        sessions = list(response.context["sessions"])
        # Newest first: the just-created session precedes the one pushed
        # back a day (other sessions from setUp sit between them, which
        # is fine — the test proves relative newest-first order).
        pks = [s.pk for s in sessions]
        self.assertLess(pks.index(newer.pk), pks.index(older.pk))


class ReportHelperTests(TestCase):
    def test_topic_keywords(self):
        self.assertEqual(topic_keywords("Ownership"), ["ownership"])
        self.assertEqual(
            topic_keywords("Arrays & hashing"), ["arrays", "hashing"]
        )

    def test_build_report_math(self):
        # Crafted items: aggregation logic is what's under test, so the
        # inputs are fixed numbers, not scorer output.
        items = [
            {"question": "q1", "topic": "A", "answer": "a", "feedback": "f",
             "scores": {}, "overall": 80},
            {"question": "q2", "topic": "A", "answer": "a", "feedback": "f",
             "scores": {}, "overall": 60},
            {"question": "q3", "topic": "B", "answer": "a", "feedback": "f",
             "scores": {}, "overall": 40},
        ]
        overall, report = build_report(items)
        self.assertEqual(overall, 60)  # mean of 80, 60, 40
        self.assertEqual(
            {t["topic"]: t["score"] for t in report["topic_scores"]},
            {"A": 70, "B": 40},
        )
        self.assertEqual(report["weakest_areas"], ["B", "A"])
        self.assertEqual(report["weakest_question"]["question"], "q3")
        self.assertEqual(report["feedback_source"], "checklist")


class AiInterviewTests(TestCase):
    """AI paths in the interview views (provider-agnostic): tried first when a key is
    configured, bank/checklist on any failure — mocked, never a real
    Groq call."""

    AI_QUESTIONS = [
        {"question": f"Acme question {i}", "topic": f"Acme topic {i}"}
        for i in range(1, 6)
    ]
    AI_SCORE = {
        "relevance": 80, "depth": 70, "structure": 60,
        "confidence": 90, "conciseness": 50, "overall": 72,
        "feedback": "AI feedback: add a number to your example.",
    }

    def setUp(self):
        self.user = User.objects.create_user(username="demo", password="demo1234")
        self.client = Client()
        self.client.force_login(self.user)

    def _start(self):
        return self.client.post(reverse("interview:index"), {
            "track": "HR", "difficulty": "medium",
            "company": "Acme", "jd_text": "We hire for React and teamwork.",
        })

    @override_settings(GROQ_API_KEY="test-key")
    @patch("interview.views.interview_questions", return_value=AI_QUESTIONS)
    def test_start_uses_ai_questions_when_configured(self, mock_ai):
        response = self._start()
        self.assertEqual(response.status_code, 302)
        session = InterviewSession.objects.get(owner=self.user)
        self.assertEqual(session.question_source, "ai")
        self.assertEqual(session.company, "Acme")
        self.assertEqual(
            [item["question"] for item in session.transcript],
            [q["question"] for q in self.AI_QUESTIONS],
        )
        mock_ai.assert_called_once_with(
            "HR", "medium", "We hire for React and teamwork.", "Acme"
        )

    @override_settings(GROQ_API_KEY="test-key")
    @patch("interview.views.interview_questions", return_value=None)
    def test_start_falls_back_to_bank_when_ai_fails(self, _mock_ai):
        response = self._start()
        self.assertEqual(response.status_code, 302)
        session = InterviewSession.objects.get(owner=self.user)
        self.assertEqual(session.question_source, "bank")
        self.assertEqual(len(session.transcript), 5)
        self.assertEqual(session.transcript[0]["topic"], "Ownership")

    @override_settings(GROQ_API_KEY="")
    def test_start_without_key_uses_bank(self):
        response = self._start()
        session = InterviewSession.objects.get(owner=self.user)
        self.assertEqual(session.question_source, "bank")
        self.assertEqual(session.company, "Acme")

    @override_settings(GROQ_API_KEY="test-key")
    @patch("interview.views.interview_questions", return_value=None)
    @patch("interview.views.score_answer", return_value=AI_SCORE)
    def test_answer_uses_ai_scoring_when_configured(self, _mock_score, _mock_q):
        # Start is forced to the bank (AI questions mocked to None) so
        # no real Groq call happens while setting the session up.
        self._start()
        session = InterviewSession.objects.get(owner=self.user)
        response = self.client.post(
            reverse("interview:detail", kwargs={"pk": session.pk}),
            {"answer": STRONG_ANSWER},
        )
        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        item = session.transcript[0]
        self.assertEqual(item["source"], "ai")
        self.assertEqual(item["overall"], 72)
        self.assertEqual(item["feedback"], self.AI_SCORE["feedback"])

    @override_settings(GROQ_API_KEY="test-key")
    @patch("interview.views.interview_questions", return_value=None)
    @patch("interview.views.score_answer", return_value=None)
    def test_answer_falls_back_to_checklist_when_ai_fails(self, _mock_score, _mock_q):
        self._start()  # bank questions, as above
        session = InterviewSession.objects.get(owner=self.user)
        self.client.post(
            reverse("interview:detail", kwargs={"pk": session.pk}),
            {"answer": STRONG_ANSWER},
        )
        session.refresh_from_db()
        self.assertEqual(session.transcript[0]["source"], "checklist")

    def test_build_report_feedback_source_from_item_sources(self):
        ai_items = [
            {"question": "q", "topic": "A", "answer": "a", "feedback": "f",
             "scores": {}, "overall": 80, "source": "ai"},
        ]
        _overall, report = build_report(ai_items)
        self.assertEqual(report["feedback_source"], "ai")
        mixed = ai_items + [
            {"question": "q", "topic": "B", "answer": "a", "feedback": "f",
             "scores": {}, "overall": 60, "source": "checklist"},
        ]
        _overall, report = build_report(mixed)
        self.assertEqual(report["feedback_source"], "mixed")
