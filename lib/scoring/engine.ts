// The JD Match scoring engine. Deterministic: identical inputs always give
// identical outputs. The AI never computes a score — it only drafts criteria.

import { findEvidence, rubricScore, type ResumeSections } from "./evidence";

export interface Criterion {
  name: string;
  category: string;
  weight: number;
  required: boolean;
}

export interface CriterionResult {
  name: string;
  category: string;
  weight: number;
  score: number;
  status: "strong" | "present" | "weak" | "missing";
  evidence: string | null;
  section: string | null;
}

export interface Gap {
  criterion: string;
  current_status: "weak" | "missing";
  suggested_action: string;
}

export interface MatchResult {
  match_score: number;
  criteria_results: CriterionResult[];
  gaps: Gap[];
}

const ACTION_TEMPLATES: Record<string, { weak: string; missing: string }> = {
  skill: {
    weak: "Add a project or experience bullet showing this skill in use, with a result — a Skills-list mention alone scores 40.",
    missing:
      "Build or convert a small project using this skill, then add an evidence bullet describing what you built and its result.",
  },
  tool: {
    weak: "Show this tool in a project bullet (what you used it for, what it changed) instead of only listing it.",
    missing:
      "Ship one small thing with this tool and write it up as a bullet: tool, task, and outcome.",
  },
  language: {
    weak: "Add a bullet where you used this language to build or fix something real, not just a Skills mention.",
    missing: "Complete a small project in this language and add it to Projects with a concrete outcome.",
  },
  education: {
    weak: "Make the education evidence explicit: degree, institution, and any relevant coursework or grade.",
    missing: "If you are pursuing this qualification, list it as in-progress with an expected date; otherwise cover it with equivalent coursework or a certification.",
  },
  default: {
    weak: "Turn this mention into evidence: a bullet showing where you applied it and what changed.",
    missing: "Create one concrete proof point for this requirement — a project, a contribution, or coursework — and add it to the resume.",
  },
};

function actionFor(category: string, status: "weak" | "missing"): string {
  const key = category.toLowerCase();
  const template =
    ACTION_TEMPLATES[key] ??
    (key.includes("tool") ? ACTION_TEMPLATES.tool : ACTION_TEMPLATES.default);
  return template[status];
}

export function scoreResume(
  sections: ResumeSections,
  criteria: Criterion[]
): MatchResult {
  const criteria_results: CriterionResult[] = criteria.map((c) => {
    const hits = findEvidence(sections, c.name);
    const { score, status, best } = rubricScore(hits);
    return {
      name: c.name,
      category: c.category,
      weight: c.weight,
      score,
      status,
      evidence: best?.quote ?? null,
      section: best?.section ?? null,
    };
  });

  const totalWeight = criteria_results.reduce((sum, r) => sum + r.weight, 0);
  const match_score =
    totalWeight > 0
      ? Math.round(
          (criteria_results.reduce((sum, r) => sum + r.weight * r.score, 0) / totalWeight) * 10
        ) / 10
      : 0;

  const gaps: Gap[] = criteria_results
    .filter((r) => r.status === "weak" || r.status === "missing")
    .map((r) => ({
      criterion: r.name,
      current_status: r.status as "weak" | "missing",
      suggested_action: actionFor(r.category, r.status as "weak" | "missing"),
    }));

  return { match_score, criteria_results, gaps };
}
