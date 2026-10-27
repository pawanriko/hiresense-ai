"""Tests for the ported interview bank + checklist scorer.

These mirror the original app's coverage tests, including the relevance
regression: a strong project answer must score relevance above 50 even
though it never says the topic label word ("ownership").
"""

from django.test import SimpleTestCase

from resumes.interview import pick_questions, score_answer_checklist


class QuestionBankTests(SimpleTestCase):
    def test_always_returns_5_questions_deterministically(self):
        self.assertEqual(len(pick_questions("DSA", "medium")), 5)
        self.assertEqual(pick_questions("DSA", "medium"),
                         pick_questions("DSA", "medium"))

    def test_easy_difficulty_leads_with_easy_questions(self):
        self.assertEqual(pick_questions("HR", "easy")[0]["difficulty"], "easy")

    def test_unknown_track_falls_back_to_hr(self):
        self.assertEqual(len(pick_questions("Nope", "medium")), 5)


class ChecklistScorerTests(SimpleTestCase):
    def test_project_answer_scores_relevance_without_topic_label_word(self):
        result = score_answer_checklist(
            "Describe a project you are most proud of. What was your exact contribution?",
            "I built a React dashboard project for my college fest. My exact "
            "contribution was the frontend and caching layer, which cut load "
            "time by 40% for 500 users.",
            ["ownership"],
        )
        self.assertGreater(result["relevance"], 50)

    def test_one_line_answer_scores_low_on_depth(self):
        result = score_answer_checklist(
            "Tell me about yourself.", "I like coding.", [])
        self.assertLess(result["depth"], 50)
        self.assertGreater(len(result["feedback"]), 10)

    def test_structured_keyword_rich_answer_scores_higher(self):
        short = score_answer_checklist(
            "Tell me about a project.", "Built it.", ["project"])
        long = score_answer_checklist(
            "Tell me about a project.",
            "First, the situation was a slow dashboard. Then I built a React "
            "project with caching, and as a result load time fell by 40% for "
            "200 users because we shipped the fix.",
            ["project"],
        )
        self.assertGreater(long["overall"], short["overall"])
        self.assertGreater(long["structure"], short["structure"])
