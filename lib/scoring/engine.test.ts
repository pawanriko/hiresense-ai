import { describe, it, expect } from "vitest";
import { scoreResume } from "./engine";
import { computeAts } from "./ats";
import { extractCriteriaHeuristic } from "./extract";
import { findEvidence, rubricScore } from "./evidence";

// Same shape as the worked example in docs/03 §3.6 (weights 35/25/20/20),
// but with stronger evidence bullets here, so the engine must return 74.0:
// React 100 (verb + number), JavaScript 100 (verb + number),
// TypeScript 0 (missing), Git 70 (experience mention, no verb/number).
const SAMPLE_SECTIONS = {
  header: "Pawan Kumar pawanriko@gmail.com github.com/pawanriko",
  skills: "React, JavaScript, Git",
  experience:
    "Frontend Intern — Built a React dashboard used by 200 users. Wrote JavaScript utilities that reduced load time by 30%. Managed code with Git and GitHub.",
  projects: "HireSense AI — React app for resume scoring.",
  education: "BCA — Bachelor of Computer Applications",
};

describe("scoring engine (docs worked example)", () => {
  it("scores the sample resume at 74.0/100 with per-criterion evidence", () => {
    const result = scoreResume(SAMPLE_SECTIONS, [
      { name: "React", category: "skill", weight: 35, required: true },
      { name: "JavaScript", category: "skill", weight: 25, required: true },
      { name: "TypeScript", category: "skill", weight: 20, required: false },
      { name: "Git", category: "tool", weight: 20, required: true },
    ]);
    const byName = Object.fromEntries(result.criteria_results.map((r) => [r.name, r]));
    expect(byName["React"].score).toBe(100); // experience bullet with verb + number
    expect(byName["JavaScript"].score).toBe(100);
    expect(byName["TypeScript"].score).toBe(0);
    expect(byName["TypeScript"].status).toBe("missing");
    expect(byName["Git"].score).toBe(70); // experience mention without verb/number in that sentence
    expect(result.match_score).toBe(74); // (35*100 + 25*100 + 20*0 + 20*70) / 100
    expect(result.gaps.map((g) => g.criterion)).toContain("TypeScript");
  });

  it("is deterministic: same inputs, same outputs", () => {
    const criteria = [{ name: "React", category: "skill", weight: 100, required: true }];
    expect(scoreResume(SAMPLE_SECTIONS, criteria)).toEqual(
      scoreResume(SAMPLE_SECTIONS, criteria)
    );
  });

  it("gives 40 for a skills-list-only mention", () => {
    const result = scoreResume(
      { skills: "Docker, Kubernetes" },
      [{ name: "Docker", category: "tool", weight: 100, required: false }]
    );
    expect(result.criteria_results[0].score).toBe(40);
    expect(result.criteria_results[0].status).toBe("weak");
  });

  it("resolves synonyms (js -> javascript, reactjs -> react)", () => {
    const hits = findEvidence({ experience: "Built features in JS and ReactJS." }, "JavaScript");
    expect(hits.length).toBeGreaterThan(0);
    expect(rubricScore(hits).score).toBe(100);
  });

  it("returns 0 with no criteria", () => {
    expect(scoreResume(SAMPLE_SECTIONS, []).match_score).toBe(0);
  });
});

describe("ATS engine", () => {
  it("scores a complete resume high and names every failed check", () => {
    const ats = computeAts(SAMPLE_SECTIONS, Object.values(SAMPLE_SECTIONS).join(" "));
    expect(ats.score).toBeGreaterThan(60);
    for (const cat of ats.categories) {
      for (const check of cat.checks) {
        expect(check.detail.length).toBeGreaterThan(0);
      }
    }
  });

  it("penalizes a bare resume", () => {
    const ats = computeAts({ header: "Name" }, "Name");
    expect(ats.score).toBeLessThan(40);
    expect(ats.categories.flatMap((c) => c.checks).some((c) => !c.passed)).toBe(true);
  });
});

describe("heuristic criteria extraction", () => {
  it("finds skills in a JD and normalizes weights to 100", () => {
    const criteria = extractCriteriaHeuristic(
      "Frontend Developer Intern. Requirements: React and JavaScript required. TypeScript preferred. Must know Git."
    );
    const names = criteria.map((c) => c.name);
    expect(names).toContain("React");
    expect(names).toContain("JavaScript");
    expect(names).toContain("TypeScript");
    expect(criteria.reduce((s, c) => s + c.weight, 0)).toBe(100);
  });

  it("returns empty when no known skill appears", () => {
    expect(extractCriteriaHeuristic("We are looking for a wonderful human being.")).toEqual([]);
  });
});
