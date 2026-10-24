// Heuristic JD criteria extraction — the no-AI fallback for criteria drafting.
// Scans JD text against a skill vocabulary, weights required > preferred >
// education/soft. The candidate always edits criteria before scoring.
// (When GROQ_API_KEY is set, the AI extraction replaces this draft.)

import { normalize } from "./evidence";
import type { Criterion } from "./engine";

interface VocabEntry {
  name: string;
  category: string;
  aliases: string[];
}

const SKILLS: VocabEntry[] = [
  { name: "React", category: "skill", aliases: ["reactjs", "react.js"] },
  { name: "Next.js", category: "skill", aliases: ["nextjs", "next js"] },
  { name: "JavaScript", category: "skill", aliases: ["js", "javascript"] },
  { name: "TypeScript", category: "skill", aliases: ["ts", "typescript"] },
  { name: "Python", category: "skill", aliases: ["python"] },
  { name: "Java", category: "skill", aliases: ["java"] },
  { name: "C++", category: "skill", aliases: ["c++", "cpp"] },
  { name: "SQL", category: "skill", aliases: ["sql", "mysql", "postgres", "postgresql"] },
  { name: "Node.js", category: "skill", aliases: ["nodejs", "node js", "node"] },
  { name: "HTML", category: "skill", aliases: ["html", "html5"] },
  { name: "CSS", category: "skill", aliases: ["css", "css3", "tailwind", "tailwindcss"] },
  { name: "Git", category: "tool", aliases: ["git", "github", "gitlab"] },
  { name: "Docker", category: "tool", aliases: ["docker"] },
  { name: "Kubernetes", category: "tool", aliases: ["kubernetes", "k8s"] },
  { name: "AWS", category: "tool", aliases: ["aws", "amazon web services"] },
  { name: "Figma", category: "tool", aliases: ["figma"] },
  { name: "REST APIs", category: "skill", aliases: ["rest", "rest api", "rest apis", "api"] },
  { name: "GraphQL", category: "skill", aliases: ["graphql"] },
  { name: "Data Structures", category: "skill", aliases: ["data structures", "dsa", "algorithms"] },
  { name: "Machine Learning", category: "skill", aliases: ["machine learning", "ml"] },
];

const SOFT: VocabEntry[] = [
  { name: "Communication", category: "soft", aliases: ["communication", "communicator"] },
  { name: "Teamwork", category: "soft", aliases: ["teamwork", "team player", "collaboration"] },
  { name: "Problem Solving", category: "soft", aliases: ["problem solving", "problem-solving", "analytical"] },
  { name: "Leadership", category: "soft", aliases: ["leadership", "leading"] },
];

function contains(haystack: string, term: string): boolean {
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^a-z0-9])${escaped}([^a-z0-9]|$)`).test(haystack);
}

function looksRequired(text: string, term: string): boolean {
  const idx = text.indexOf(term);
  if (idx === -1) return false;
  const window = text.slice(Math.max(0, idx - 80), idx + term.length + 40);
  return /(required|must have|must-have|mandatory|essential)/.test(window);
}

export function extractCriteriaHeuristic(jdText: string): Criterion[] {
  const norm = normalize(jdText);
  const found: Criterion[] = [];

  for (const entry of [...SKILLS, ...SOFT]) {
    const hitAlias = [entry.name, ...entry.aliases].find((a) => contains(norm, normalize(a)));
    if (!hitAlias) continue;
    const required = looksRequired(norm, normalize(hitAlias));
    found.push({
      name: entry.name,
      category: entry.category,
      weight: required ? 35 : entry.category === "soft" ? 10 : 20,
      required,
    });
  }

  // Education requirement.
  if (/(bachelor|b\.tech|btech|bca|degree|undergraduate)/.test(norm)) {
    found.push({ name: "Bachelor's degree (or pursuing)", category: "education", weight: 15, required: true });
  }

  if (found.length === 0) return [];
  const limited = found.slice(0, 12);
  const total = limited.reduce((s, c) => s + c.weight, 0);
  // Normalize weights to sum 100, keeping the largest criterion absorbing rounding.
  let acc = 0;
  const normalized = limited.map((c, i) => {
    if (i === limited.length - 1) return { ...c, weight: 100 - acc };
    const w = Math.round((c.weight / total) * 100);
    acc += w;
    return { ...c, weight: w };
  });
  return normalized.sort((a, b) => b.weight - a.weight);
}
