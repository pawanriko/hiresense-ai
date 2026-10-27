"""Tests for the Groq client (resumes/groq.py).

WHAT: the client is the app's only LLM contact, so these prove its
contract without ever calling Groq: configured flag, transport failure
-> None (never an exception), JSON parsing (including fenced replies),
and each feature function's validation — bad AI output must fall back,
not crash a page.

HOW: urllib is mocked, never the network. ``groq_chat`` itself is
mocked for the feature functions, so they are tested on canned model
text, exactly like a real reply minus the API call.
"""

import json
import urllib.error
from unittest.mock import patch

from django.test import TestCase, override_settings

from resumes.groq import (
    _parse_json_object,
    extract_criteria_ai,
    groq_chat,
    interview_questions_ai,
    is_groq_configured,
    score_answer_ai,
)


class FakeResponse:
    """A urlopen result: read() returns JSON bytes, usable as a context
    manager, exactly like the real HTTPResponse in this code's use."""

    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


GROQ_OK = {
    "choices": [{"message": {"content": "hello from groq"}}],
}


class ConfiguredTests(TestCase):
    def test_unconfigured_without_key(self):
        with override_settings(GROQ_API_KEY=""):
            self.assertFalse(is_groq_configured())

    def test_configured_with_key(self):
        with override_settings(GROQ_API_KEY="gsk_test"):
            self.assertTrue(is_groq_configured())

    def test_groq_chat_returns_none_without_key(self):
        with override_settings(GROQ_API_KEY=""):
            self.assertIsNone(groq_chat("sys", "user"))


class GroqChatTests(TestCase):
    @override_settings(GROQ_API_KEY="gsk_test", GROQ_MODEL="llama-test")
    def test_success_returns_content_and_sends_bearer_key(self):
        seen = {}

        def fake_urlopen(request, timeout=None):
            seen["request"] = request
            return FakeResponse(GROQ_OK)

        with patch("resumes.groq.urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(groq_chat("sys", "user"), "hello from groq")
        request = seen["request"]
        self.assertEqual(request.get_header("Authorization"), "Bearer gsk_test")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "llama-test")
        self.assertEqual(body["messages"][0]["role"], "system")

    @override_settings(GROQ_API_KEY="gsk_test")
    def test_transport_failure_returns_none(self):
        with patch(
            "resumes.groq.urllib.request.urlopen",
            side_effect=urllib.error.URLError("no network"),
        ):
            self.assertIsNone(groq_chat("sys", "user"))

    @override_settings(GROQ_API_KEY="gsk_test")
    def test_malformed_reply_returns_none(self):
        with patch(
            "resumes.groq.urllib.request.urlopen",
            return_value=FakeResponse({"unexpected": "shape"}),
        ):
            self.assertIsNone(groq_chat("sys", "user"))


class ParseTests(TestCase):
    def test_plain_object(self):
        self.assertEqual(_parse_json_object('{"a": 1}'), {"a": 1})

    def test_fenced_json_object(self):
        self.assertEqual(
            _parse_json_object('```json\n{"a": 1}\n```'), {"a": 1}
        )

    def test_garbage_and_lists_return_none(self):
        self.assertIsNone(_parse_json_object("not json"))
        self.assertIsNone(_parse_json_object("[1, 2]"))
        self.assertIsNone(_parse_json_object(""))


class CriteriaAiTests(TestCase):
    @patch(
        "resumes.groq.groq_chat",
        return_value=json.dumps({"criteria": [
            {"name": "React", "category": "skill", "weight": 30,
             "required": True},
            {"name": "Teamwork", "category": "soft", "weight": 20,
             "required": False},
        ]}),
    )
    def test_weights_normalised_to_100(self, _mock):
        criteria = extract_criteria_ai("Frontend Intern", "Acme", "React...")
        self.assertEqual(sum(c["weight"] for c in criteria), 100)
        self.assertEqual(criteria[0]["name"], "React")  # heaviest first

    @patch(
        "resumes.groq.groq_chat",
        return_value=json.dumps({"criteria": [
            {"name": "React", "category": "made-up", "weight": 50,
             "required": True},
            {"name": "", "category": "skill", "weight": 50,
             "required": False},
        ]}),
    )
    def test_bad_category_defaults_and_blank_rows_dropped(self, _mock):
        criteria = extract_criteria_ai("T", "C", "JD")
        self.assertEqual(len(criteria), 1)
        self.assertEqual(criteria[0]["category"], "skill")
        self.assertEqual(criteria[0]["weight"], 100)

    @patch("resumes.groq.groq_chat", return_value=None)
    def test_failed_call_returns_none(self, _mock):
        self.assertIsNone(extract_criteria_ai("T", "C", "JD"))

    @patch("resumes.groq.groq_chat", return_value='{"criteria": []}')
    def test_empty_criteria_returns_none(self, _mock):
        self.assertIsNone(extract_criteria_ai("T", "C", "JD"))


class QuestionsAiTests(TestCase):
    FIVE = json.dumps({"questions": [
        {"question": f"Q{i}", "topic": f"T{i}"} for i in range(1, 6)
    ]})

    @patch("resumes.groq.groq_chat", return_value=FIVE)
    def test_five_questions_returned(self, _mock):
        questions = interview_questions_ai("HR", "medium", "JD", "Acme")
        self.assertEqual(len(questions), 5)
        self.assertEqual(questions[0]["question"], "Q1")

    @patch(
        "resumes.groq.groq_chat",
        return_value=json.dumps({"questions": [
            {"question": "Q1", "topic": "T1"},
            {"question": "Q2", "topic": "T2"},
        ]}),
    )
    def test_fewer_than_five_returns_none(self, _mock):
        # The session invariant is 5 questions; a short AI reply must
        # fall back to the bank, not start a 2-question session.
        self.assertIsNone(interview_questions_ai("HR", "medium", "JD", "Acme"))

    @patch("resumes.groq.groq_chat", return_value="garbage")
    def test_bad_json_returns_none(self, _mock):
        self.assertIsNone(interview_questions_ai("HR", "medium", "JD", "Acme"))


class ScoreAiTests(TestCase):
    @patch(
        "resumes.groq.groq_chat",
        return_value=json.dumps({
            "relevance": 80, "depth": 70, "structure": 60,
            "confidence": 90, "conciseness": 50,
            "feedback": "Add a number to your example.",
        }),
    )
    def test_overall_uses_rubric_weights(self, _mock):
        scored = score_answer_ai("Q?", "I built...")
        # 80*.3 + 70*.25 + 60*.2 + 90*.15 + 50*.1 = 72.0
        self.assertEqual(scored["overall"], 72)
        self.assertEqual(scored["feedback"], "Add a number to your example.")

    @patch(
        "resumes.groq.groq_chat",
        return_value=json.dumps({
            "relevance": 150, "depth": -5, "structure": 60,
            "confidence": 90, "conciseness": 50, "feedback": "f",
        }),
    )
    def test_scores_clamped_to_0_100(self, _mock):
        scored = score_answer_ai("Q?", "A")
        self.assertEqual(scored["relevance"], 100)
        self.assertEqual(scored["depth"], 0)

    @patch(
        "resumes.groq.groq_chat",
        return_value=json.dumps({"relevance": 80, "feedback": "f"}),
    )
    def test_missing_subscore_returns_none(self, _mock):
        self.assertIsNone(score_answer_ai("Q?", "A"))
