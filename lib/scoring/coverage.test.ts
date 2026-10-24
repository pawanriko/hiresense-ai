import { describe, it, expect } from "vitest";
import { findEvidence, rubricScore } from "./evidence";
import { scoreResume } from "./engine";
import { computeAts } from "./ats";
import { extractCriteriaHeuristic } from "./extract";
import { pickQuestions, scoreAnswerChecklist } from "../interview/questions";

describe("rubric thresholds (docs/03 §3.4)", () => {
  it("experience bullet without verb or number scores 70, not 100", () => {
    const hits = findEvidence(
      { experience: "Worked on the React frontend for the team portal." },
      "React"
    );
    expect(rubricScore(hits).score).toBe(70);
    expect(rubricScore(hits).status).toBe("present");
  });

  it("summary context scores 70", () => {
    const hits = findEvidence(
      { summary: "Frontend developer with experience in React and modern web apps." },
      "React"
    );
    expect(rubricScore(hits).score).toBe(70);
  });

  it("synonym postgres matches postgresql criterion", () => {
    const hits = findEvidence(
      { experience: "Managed Postgres databases for the app." },
      "PostgreSQL"
    );
    expect(hits.length).toBeGreaterThan(0);
  });

  it("missing criterion yields a gap with a fix action", () => {
    const result = scoreResume(
      { skills: "Python" },
      [{ name: "Docker", category: "tool", weight: 100, required: true }]
    );
    expect(result.gaps).toHaveLength(1);
    expect(result.gaps[0].current_status).toBe("missing");
    expect(result.gaps[0].suggested_action.length).toBeGreaterThan(20);
  });

  it("weak and missing gaps get different actions", () => {
    const result = scoreResume(
      { skills: "Docker" },
      [
        { name: "Docker", category: "tool", weight: 50, required: false },
        { name: "Kubernetes", category: "tool", weight: 50, required: false },
      ]
    );
    const [weak, missing] = result.gaps;
    expect(weak.current_status).toBe("weak");
    expect(missing.current_status).toBe("missing");
    expect(weak.suggested_action).not.toBe(missing.suggested_action);
  });
});

describe("ATS edge cases", () => {
  it("a resume with email, links, and quantified bullets scores high", () => {
    const sections = {
      header: "Jane Doe jane@example.com github.com/janedoe",
      summary: "Software developer.",
      skills: "React, TypeScript",
      experience:
        "Built a React app used by 500 users. Reduced load time by 40% in 2024. Improved onboarding for 30 customers.",
      education: "BSc Computer Science 2023",
    };
    const ats = computeAts(sections, Object.values(sections).join(" "));
    expect(ats.score).toBeGreaterThan(70);
    const contact = ats.categories.find((c) => c.name === "Contact & links")!;
    expect(contact.checks.every((c) => c.passed)).toBe(true);
  });

  it("an image-only / near-empty resume fails parseable-text and length checks", () => {
    const ats = computeAts({ header: "Name" }, "Name");
    const lengthCat = ats.categories.find((c) => c.name === "Length & format")!;
    expect(lengthCat.checks.some((c) => !c.passed)).toBe(true);
  });
});

describe("criteria extraction details", () => {
  it("detects an education requirement", () => {
    const criteria = extractCriteriaHeuristic(
      "We are hiring a developer. Bachelor's degree required. Python experience needed."
    );
    expect(criteria.some((c) => c.category === "education")).toBe(true);
    expect(criteria.reduce((s, c) => s + c.weight, 0)).toBe(100);
  });

  it("caps criteria at 12", () => {
    const jd =
      "React JavaScript TypeScript Python Java SQL Node.js HTML CSS Git Docker Kubernetes AWS Figma REST GraphQL Data Structures Machine Learning Communication Teamwork Problem Solving Leadership";
    expect(extractCriteriaHeuristic(jd).length).toBeLessThanOrEqual(12);
  });
});

describe("interview question bank and checklist scoring", () => {
  it("always returns 5 questions, deterministically", () => {
    expect(pickQuestions("DSA", "medium")).toHaveLength(5);
    expect(pickQuestions("DSA", "medium")).toEqual(pickQuestions("DSA", "medium"));
  });

  it("easy difficulty leads with easy questions", () => {
    expect(pickQuestions("HR", "easy")[0].difficulty).toBe("easy");
  });

  it("a one-line answer scores low on depth", () => {
    const s = scoreAnswerChecklist("Tell me about yourself.", "I like coding.", []);
    expect(s.depth).toBeLessThan(50);
    expect(s.feedback.length).toBeGreaterThan(10);
  });

  it("a structured, keyword-rich answer scores higher", () => {
    const short = scoreAnswerChecklist(
      "Tell me about a project.",
      "Built it.",
      ["project"]
    );
    const long = scoreAnswerChecklist(
      "Tell me about a project.",
      "First, the situation was a slow dashboard. Then I built a React project with caching, and as a result load time fell by 40% for 200 users because we shipped the fix.",
      ["project"]
    );
    expect(long.overall).toBeGreaterThan(short.overall);
    expect(long.structure).toBeGreaterThan(short.structure);
  });
});
