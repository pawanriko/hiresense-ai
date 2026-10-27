"""Tests for the provider dispatch (resumes/ai_provider.py).

WHAT: which provider answers, under every key/pin combination — the
rule the views depend on. Provider functions are mocked; only the
selection logic is under test.

THE RULE, restated so the tests read as its spec:
  * No keys -> nothing configured, every call returns None.
  * One key -> that provider answers.
  * Both keys, no pin -> Groq answers (first-provider default).
  * Pin set to a provider -> that provider answers, and a missing key
    for the pinned provider means None, NOT a silent switch.
  * Unknown pin value -> treated as unset (both-keys default applies).
"""

from unittest.mock import patch

from django.test import TestCase, override_settings

from resumes import ai_provider

CANNED_CRITERIA = [
    {"name": "React", "category": "skill", "weight": 100, "required": True},
]


class DispatchTests(TestCase):
    def test_no_keys_nothing_configured(self):
        with override_settings(GROQ_API_KEY="", GEMINI_API_KEY="", AI_PROVIDER=""):
            self.assertFalse(ai_provider.is_ai_configured())
            self.assertIsNone(ai_provider.extract_criteria("T", "C", "JD"))

    @override_settings(GROQ_API_KEY="gsk", GEMINI_API_KEY="", AI_PROVIDER="")
    def test_groq_only_groq_answers(self):
        with patch(
            "resumes.ai_provider.groq.extract_criteria_ai",
            return_value=CANNED_CRITERIA,
        ) as mock_groq, patch(
            "resumes.ai_provider.gemini.extract_criteria_ai"
        ) as mock_gemini:
            self.assertTrue(ai_provider.is_ai_configured())
            self.assertEqual(
                ai_provider.extract_criteria("T", "C", "JD"), CANNED_CRITERIA
            )
            mock_groq.assert_called_once()
            mock_gemini.assert_not_called()

    @override_settings(GROQ_API_KEY="", GEMINI_API_KEY="AIza", AI_PROVIDER="")
    def test_gemini_only_gemini_answers(self):
        with patch(
            "resumes.ai_provider.gemini.extract_criteria_ai",
            return_value=CANNED_CRITERIA,
        ) as mock_gemini, patch(
            "resumes.ai_provider.groq.extract_criteria_ai"
        ) as mock_groq:
            self.assertEqual(
                ai_provider.extract_criteria("T", "C", "JD"), CANNED_CRITERIA
            )
            mock_gemini.assert_called_once()
            mock_groq.assert_not_called()

    @override_settings(GROQ_API_KEY="gsk", GEMINI_API_KEY="AIza", AI_PROVIDER="")
    def test_both_keys_no_pin_groq_wins_default(self):
        with patch(
            "resumes.ai_provider.groq.extract_criteria_ai",
            return_value=CANNED_CRITERIA,
        ) as mock_groq, patch(
            "resumes.ai_provider.gemini.extract_criteria_ai"
        ) as mock_gemini:
            ai_provider.extract_criteria("T", "C", "JD")
            mock_groq.assert_called_once()
            mock_gemini.assert_not_called()

    @override_settings(GROQ_API_KEY="gsk", GEMINI_API_KEY="AIza", AI_PROVIDER="gemini")
    def test_pin_gemini_gemini_answers(self):
        with patch(
            "resumes.ai_provider.gemini.extract_criteria_ai",
            return_value=CANNED_CRITERIA,
        ) as mock_gemini, patch(
            "resumes.ai_provider.groq.extract_criteria_ai"
        ) as mock_groq:
            self.assertEqual(
                ai_provider.extract_criteria("T", "C", "JD"), CANNED_CRITERIA
            )
            mock_gemini.assert_called_once()
            mock_groq.assert_not_called()

    @override_settings(GROQ_API_KEY="gsk", GEMINI_API_KEY="", AI_PROVIDER="gemini")
    def test_pin_gemini_without_gemini_key_returns_none(self):
        # A pin is a promise, not a preference: no silent switch to
        # Groq just because its key happens to be set.
        self.assertFalse(ai_provider.is_ai_configured())
        self.assertIsNone(ai_provider.extract_criteria("T", "C", "JD"))

    @override_settings(GROQ_API_KEY="gsk", GEMINI_API_KEY="AIza", AI_PROVIDER="bogus")
    def test_unknown_pin_treated_as_unset(self):
        with patch(
            "resumes.ai_provider.groq.extract_criteria_ai",
            return_value=CANNED_CRITERIA,
        ) as mock_groq:
            ai_provider.extract_criteria("T", "C", "JD")
            mock_groq.assert_called_once()

    @override_settings(GROQ_API_KEY="", GEMINI_API_KEY="AIza", AI_PROVIDER="")
    def test_questions_and_scoring_dispatch_to_gemini(self):
        questions = [{"question": f"Q{i}", "topic": "T"} for i in range(5)]
        with patch(
            "resumes.ai_provider.gemini.interview_questions_ai",
            return_value=questions,
        ) as mock_q, patch(
            "resumes.ai_provider.gemini.score_answer_ai",
            return_value={"overall": 72},
        ) as mock_s:
            self.assertEqual(
                ai_provider.interview_questions("HR", "medium", "JD", "Acme"),
                questions,
            )
            self.assertEqual(
                ai_provider.score_answer("Q?", "A"), {"overall": 72}
            )
            mock_q.assert_called_once()
            mock_s.assert_called_once()
