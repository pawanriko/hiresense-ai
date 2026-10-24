// Deterministic evidence search for the JD Match engine.
// Pure functions: no I/O, no AI. The AI never scores — it only drafts criteria.

export type ResumeSections = Record<string, string>;

export interface EvidenceHit {
  section: string;
  quote: string;
  hasActionVerb: boolean;
  hasQuantifiedResult: boolean;
}

// Canonical skill name -> aliases that mean the same thing on a resume.
const SYNONYMS: Record<string, string[]> = {
  javascript: ["js", "ecmascript", "es6", "es2015"],
  typescript: ["ts"],
  react: ["reactjs", "react.js"],
  "next.js": ["nextjs", "next js"],
  "node.js": ["nodejs", "node js", "node"],
  postgresql: ["postgres", "psql"],
  mongodb: ["mongo"],
  github: ["gh"],
  "c++": ["cpp", "c plus plus"],
  "c#": ["csharp", "c sharp"],
  "machine learning": ["ml"],
  "artificial intelligence": ["ai"],
  "user interface": ["ui"],
  "user experience": ["ux"],
};

const ALIAS_TO_CANONICAL = new Map<string, string>();
for (const [canonical, aliases] of Object.entries(SYNONYMS)) {
  for (const alias of aliases) ALIAS_TO_CANONICAL.set(alias, canonical);
}

export const ACTION_VERBS = [
  "built", "developed", "designed", "implemented", "created", "launched",
  "improved", "increased", "reduced", "optimized", "automated", "led",
  "delivered", "shipped", "engineered", "architected", "migrated",
  "refactored", "integrated", "deployed", "scaled", "boosted", "streamlined",
  "achieved", "grew", "drove", "owned", "mentored", "collaborated",
];

const QUANTIFIED = /(\d+\s?(%|x|k|\+)?|\$|₹|percent|users|customers|requests|ms|s\b)/i;

export function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9+#\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// All searchable forms of a criterion name: itself + its aliases, and the
// canonical name when the criterion itself is an alias (e.g. "js" -> "javascript").
export function searchForms(criterionName: string): string[] {
  const norm = normalize(criterionName);
  const forms = new Set<string>([norm]);
  if (SYNONYMS[norm]) for (const a of SYNONYMS[norm]) forms.add(a);
  const canonical = ALIAS_TO_CANONICAL.get(norm);
  if (canonical) {
    forms.add(canonical);
    for (const a of SYNONYMS[canonical] ?? []) forms.add(a);
  }
  return [...forms];
}

export function splitSentences(text: string): string[] {
  return text
    .split(/[\n\r•·\-–—]+|(?<=[.!?;])\s+/)
    .map((s) => s.replace(/\s+/g, " ").trim())
    .filter((s) => s.length > 1);
}

function sentenceMatches(sentenceNorm: string, forms: string[]): boolean {
  return forms.some((form) => {
    const escaped = form.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(^|\\s)${escaped}(\\s|$)`).test(sentenceNorm);
  });
}

const STRONG_SECTIONS = new Set(["experience", "projects"]);
const CONTEXT_SECTIONS = new Set(["experience", "projects", "summary", "header"]);

/** Find every evidence sentence for a criterion across the resume sections. */
export function findEvidence(
  sections: ResumeSections,
  criterionName: string
): EvidenceHit[] {
  const forms = searchForms(criterionName);
  const hits: EvidenceHit[] = [];
  for (const [section, body] of Object.entries(sections)) {
    if (!body) continue;
    for (const sentence of splitSentences(body)) {
      const norm = normalize(sentence);
      if (!sentenceMatches(norm, forms)) continue;
      const verbHit = ACTION_VERBS.some((v) =>
        new RegExp(`(^|\\s)${v}(\\s|$|ed\\b|ing\\b)`).test(norm)
      );
      hits.push({
        section,
        quote: sentence.length > 220 ? `${sentence.slice(0, 217)}…` : sentence,
        hasActionVerb: verbHit,
        hasQuantifiedResult: QUANTIFIED.test(sentence),
      });
    }
  }
  return hits;
}

/**
 * Rubric (docs/03 §3.4), applied to the evidence hits:
 * 100 — Experience/Projects bullet WITH action verb and/or quantified result
 *  70 — Experience/Projects bullet, or described with context in Summary
 *  40 — Skills list only (claimed, not demonstrated)
 *   0 — not found anywhere
 */
export function rubricScore(
  hits: EvidenceHit[]
): { score: number; status: "strong" | "present" | "weak" | "missing"; best: EvidenceHit | null } {
  if (hits.length === 0) return { score: 0, status: "missing", best: null };
  const strong = hits.find(
    (h) => STRONG_SECTIONS.has(h.section) && (h.hasActionVerb || h.hasQuantifiedResult)
  );
  if (strong) return { score: 100, status: "strong", best: strong };
  const contextual = hits.find((h) => CONTEXT_SECTIONS.has(h.section));
  if (contextual) return { score: 70, status: "present", best: contextual };
  const skillsOnly = hits.find((h) => h.section === "skills");
  if (skillsOnly) return { score: 40, status: "weak", best: skillsOnly };
  return { score: 70, status: "present", best: hits[0] };
}
