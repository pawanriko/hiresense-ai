"""Tests for the Gemini provider (resumes/gemini.py).

Mirrors the Groq client tests: same contract, different transport.
The Gemini-specific parts under test are the endpoint shape (model in
the URL, key in the x-goog-api-key header — never in the URL), the
systemInstruction/contents body, and the candidates -> parts -> text
reply parsing. Feature functions are tested on canned model text via a
mocked gemini_chat, never a real API call.
"""

import json
import urllib.error
from unittest.mock import patch

from django.test import TestCase, override_settings

from resumes.gemini import (
    extract_criteria_ai,
    gemini_chat,
    interview_questions_ai,
    is_gemini_configured,
    score_answer_ai,
)
from resumes.tests.test_groq import FakeResponse

GEMINI_OK = {
    "candidates": [{"content": {"parts": [{"text": "hello from gemini"}]}}],
}


class ConfiguredTests(TestCase):
    def test_unconfigured_without_key(self):
        with override_settings(GEMINI_API_KEY=""):
            self.assertFalse(is_gemini_configured())

    def test_configured_with_key(self):
        with override_settings(GEMINI_API_KEY="AIza_test"):
            self.assertTrue(is_gemini_configured())

    def test_gemini_chat_returns_none_without_key(self):
        with override_settings(GEMINI_API_KEY=""):
            self.assertIsNone(gemini_chat("sys", "user"))


class GeminiChatTests(TestCase):
    @override_settings(GEMINI_API_KEY="AIza_test", GEMINI_MODEL="gemini-test")
    def test_success_returns_text_and_keeps_key_out_of_url(self):
        seen = {}

        def fake_urlopen(request, timeout=None):
            seen["request"] = request
            return FakeResponse(GEMINI_OK)

        with patch("resumes.gemini.urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(gemini_chat("sys", "user"), "hello from gemini")
        request = seen["request"]
        # Key in the header, never in the URL (URLs land in logs).
        self.assertEqual(request.get_header("X-goog-api-key"), "AIza_test")
        self.assertNotIn("AIza_test", request.full_url)
        self.assertIn("gemini-test:generateContent", request.full_url)
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(
            body["systemInstruction"]["parts"][0]["text"], "sys"
        )
        self.assertEqual(
            body["generationConfig"]["responseMimeType"], "application/json"
        )

    @override_settings(GEMINI_API_KEY="AIza_test")
    def test_transport_failure_returns_none(self):
        with patch(
            "resumes.gemini.urllib.request.urlopen",
            side_effect=urllib.error.URLError("no network"),
        ):
            self.assertIsNone(gemini_chat("sys", "user"))

    @override_settings(GEMINI_API_KEY="AIza_test")
    def test_empty_candidates_returns_none(self):
        with patch(
            "resumes.gemini.urllib.request.urlopen",
            return_value=FakeResponse({"candidates": []}),
        ):
            self.assertIsNone(gemini_chat("sys", "user"))

    @override_settings(GEMINI_API_KEY="AIza_test")
    def test_blocked_reply_without_candidates_returns_none(self):
        with patch(
            "resumes.gemini.urllib.request.urlopen",
            return_value=FakeResponse({"promptFeedback": {"blockReason": "OTHER"}}),
        ):
            self.assertIsNone(gemini_chat("sys", "user"))


class GeminiFeatureTests(TestCase):
    @patch(
        "resumes.gemini.gemini_chat",
        return_value=json.dumps({"criteria": [
            {"name": "React", "category": "skill", "weight": 30,
             "required": True},
            {"name": "Teamwork", "category": "soft", "weight": 20,
             "required": False},
        ]}),
    )
    def test_criteria_normalised_to_100(self, _mock):
        criteria = extract_criteria_ai("Frontend Intern", "Acme", "React...")
        self.assertEqual(sum(c["weight"] for c in criteria), 100)

    @patch(
        "resumes.gemini.gemini_chat",
        return_value=json.dumps({"questions": [
            {"question": f"Q{i}", "topic": f"T{i}"} for i in range(1, 6)
        ]}),
    )
    def test_five_questions_returned(self, _mock):
        questions = interview_questions_ai("HR", "medium", "JD", "Acme")
        self.assertEqual(len(questions), 5)

    @patch(
        "resumes.gemini.gemini_chat",
        return_value=json.dumps({
            "relevance": 80, "depth": 70, "structure": 60,
            "confidence": 90, "conciseness": 50,
            "feedback": "Add a number to your example.",
        }),
    )
    def test_score_overall_uses_rubric_weights(self, _mock):
        scored = score_answer_ai("Q?", "I built...")
        self.assertEqual(scored["overall"], 72)
