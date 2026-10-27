"""Tests for the ported scoring library.

WHAT THESE TESTS ARE: the original app's vitest cases, translated to
Django's TestCase style. They pin the EXACT numbers the original produces
for the same inputs — if a porting mistake changes a score, a test here
fails. That is the whole point: the two apps must agree.

HOW TO RUN: ``python manage.py test`` (from the project root, venv active).
"""

from django.test import SimpleTestCase

from resumes.scoring import (
    compute_ats,
    extract_criteria_heuristic,
    find_evidence,
    rubric_score,
    score_resume,
)

# Same shape as the worked example in the original docs (weights 35/25/20/20),
# but with stronger evidence bullets, so the engine must return 74.0:
# React 100 (verb + number), JavaScript 100 (verb + number),
# TypeScript 0 (missing), Git 70 (experience mention, no verb/number).
SAMPLE_SECTIONS = {
    "header": "Pawan Kumar pawanriko@gmail.com github.com/pawanriko",
    "skills": "React, JavaScript, Git",
    "experience": (
        "Frontend Intern — Built a React dashboard used by 200 users. "
        "Wrote JavaScript utilities that reduced load time by 30%. "
        "Managed code with Git and GitHub."
    ),
    "projects": "HireSense AI — React app for resume scoring.",
    "education": "BCA — Bachelor of Computer Applications",
}


class JdMatchEngineTests(SimpleTestCase):
    def test_sample_resume_scores_74_with_per_criterion_evidence(self):
        result = score_resume(SAMPLE_SECTIONS, [
            {"name": "React", "category": "skill", "weight": 35, "required": True},
            {"name": "JavaScript", "category": "skill", "weight": 25, "required": True},
            {"name": "TypeScript", "category": "skill", "weight": 20, "required": False},
            {"name": "Git", "category": "tool", "weight": 20, "required": True},
        ])
        by_name = {r["name"]: r for r in result["criteria_results"]}
        self.assertEqual(by_name["React"]["score"], 100)
        self.assertEqual(by_name["JavaScript"]["score"], 100)
        self.assertEqual(by_name["TypeScript"]["score"], 0)
        self.assertEqual(by_name["TypeScript"]["status"], "missing")
        self.assertEqual(by_name["Git"]["score"], 70)
        # (35*100 + 25*100 + 20*0 + 20*70) / 100
        self.assertEqual(result["match_score"], 74)
        self.assertIn("TypeScript", [g["criterion"] for g in result["gaps"]])

    def test_deterministic_same_inputs_same_outputs(self):
        criteria = [{"name": "React", "category": "skill", "weight": 100,
                     "required": True}]
        self.assertEqual(score_resume(SAMPLE_SECTIONS, criteria),
                         score_resume(SAMPLE_SECTIONS, criteria))

    def test_skills_list_only_mention_scores_40(self):
        result = score_resume(
            {"skills": "Docker, Kubernetes"},
            [{"name": "Docker", "category": "tool", "weight": 100, "required": False}],
        )
        self.assertEqual(result["criteria_results"][0]["score"], 40)
        self.assertEqual(result["criteria_results"][0]["status"], "weak")

    def test_synonyms_resolve(self):
        hits = find_evidence(
            {"experience": "Built features in JS and ReactJS."}, "JavaScript")
        self.assertGreater(len(hits), 0)
        self.assertEqual(rubric_score(hits)[0], 100)

    def test_no_criteria_scores_zero(self):
        self.assertEqual(score_resume(SAMPLE_SECTIONS, [])["match_score"], 0)

    def test_experience_bullet_without_verb_or_number_scores_70(self):
        hits = find_evidence(
            {"experience": "Worked on the React frontend for the team portal."},
            "React",
        )
        score, status, _ = rubric_score(hits)
        self.assertEqual(score, 70)
        self.assertEqual(status, "present")

    def test_summary_context_scores_70(self):
        hits = find_evidence(
            {"summary": "Frontend developer with experience in React and modern web apps."},
            "React",
        )
        self.assertEqual(rubric_score(hits)[0], 70)

    def test_synonym_postgres_matches_postgresql(self):
        hits = find_evidence(
            {"experience": "Managed Postgres databases for the app."},
            "PostgreSQL",
        )
        self.assertGreater(len(hits), 0)

    def test_missing_criterion_yields_gap_with_fix_action(self):
        result = score_resume(
            {"skills": "Python"},
            [{"name": "Docker", "category": "tool", "weight": 100, "required": True}],
        )
        self.assertEqual(len(result["gaps"]), 1)
        self.assertEqual(result["gaps"][0]["current_status"], "missing")
        self.assertGreater(len(result["gaps"][0]["suggested_action"]), 20)

    def test_weak_and_missing_gaps_get_different_actions(self):
        result = score_resume(
            {"skills": "Docker"},
            [
                {"name": "Docker", "category": "tool", "weight": 50, "required": False},
                {"name": "Kubernetes", "category": "tool", "weight": 50, "required": False},
            ],
        )
        weak, missing = result["gaps"]
        self.assertEqual(weak["current_status"], "weak")
        self.assertEqual(missing["current_status"], "missing")
        self.assertNotEqual(weak["suggested_action"], missing["suggested_action"])


class AtsTests(SimpleTestCase):
    def test_complete_resume_scores_high_and_every_check_explains_itself(self):
        text = " ".join(SAMPLE_SECTIONS.values())
        ats = compute_ats(SAMPLE_SECTIONS, text)
        self.assertGreater(ats["score"], 60)
        for category in ats["categories"]:
            for check in category["checks"]:
                self.assertGreater(len(check["detail"]), 0)

    def test_bare_resume_is_penalised(self):
        ats = compute_ats({"header": "Name"}, "Name")
        self.assertLess(ats["score"], 40)
        self.assertTrue(any(not c["passed"]
                            for cat in ats["categories"] for c in cat["checks"]))

    def test_email_links_and_quantified_bullets_score_high(self):
        sections = {
            "header": "Jane Doe jane@example.com github.com/janedoe",
            "summary": "Software developer.",
            "skills": "React, TypeScript",
            "experience": (
                "Built a React app used by 500 users. "
                "Reduced load time by 40% in 2024. "
                "Improved onboarding for 30 customers."
            ),
            "education": "BSc Computer Science 2023",
        }
        ats = compute_ats(sections, " ".join(sections.values()))
        self.assertGreater(ats["score"], 70)
        contact = next(c for c in ats["categories"] if c["name"] == "Contact & links")
        self.assertTrue(all(c["passed"] for c in contact["checks"]))

    def test_near_empty_resume_fails_length_checks(self):
        ats = compute_ats({"header": "Name"}, "Name")
        length_cat = next(c for c in ats["categories"] if c["name"] == "Length & format")
        self.assertTrue(any(not c["passed"] for c in length_cat["checks"]))


class CriteriaExtractionTests(SimpleTestCase):
    def test_finds_skills_and_normalises_weights_to_100(self):
        criteria = extract_criteria_heuristic(
            "Frontend Developer Intern. Requirements: React and JavaScript "
            "required. TypeScript preferred. Must know Git."
        )
        names = [c["name"] for c in criteria]
        self.assertIn("React", names)
        self.assertIn("JavaScript", names)
        self.assertIn("TypeScript", names)
        self.assertEqual(sum(c["weight"] for c in criteria), 100)

    def test_empty_when_no_known_skill_appears(self):
        self.assertEqual(
            extract_criteria_heuristic("We are looking for a wonderful human being."),
            [],
        )

    def test_detects_education_requirement(self):
        criteria = extract_criteria_heuristic(
            "We are hiring a developer. Bachelor's degree required. "
            "Python experience needed."
        )
        self.assertTrue(any(c["category"] == "education" for c in criteria))
        self.assertEqual(sum(c["weight"] for c in criteria), 100)

    def test_caps_criteria_at_12(self):
        jd = ("React JavaScript TypeScript Python Java SQL Node.js HTML CSS Git "
              "Docker Kubernetes AWS Figma REST GraphQL Data Structures "
              "Machine Learning Communication Teamwork Problem Solving Leadership")
        self.assertLessEqual(len(extract_criteria_heuristic(jd)), 12)
