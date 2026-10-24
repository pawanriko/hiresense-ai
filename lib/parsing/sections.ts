// Deterministic resume section segmentation.
// Splits extracted plain text into named sections using heading heuristics.
// Pure function — unit-testable, no I/O, no AI.

export type ResumeSections = Record<string, string>;

const HEADINGS: Record<string, string[]> = {
  contact: ["contact", "contact information", "personal details"],
  summary: ["summary", "professional summary", "profile", "objective", "about me", "about"],
  skills: ["skills", "technical skills", "core skills", "technologies", "tech stack", "key skills"],
  experience: ["experience", "work experience", "professional experience", "employment history", "internship experience", "internships"],
  projects: ["projects", "personal projects", "key projects", "academic projects", "side projects"],
  education: ["education", "academic background", "qualifications", "academics"],
  certifications: ["certifications", "certificates", "courses", "achievements", "awards"],
  links: ["links", "profiles", "social links", "online profiles"],
};

function normalizeHeading(line: string): string {
  return line
    .toLowerCase()
    .replace(/[^a-z\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function matchSection(line: string): string | null {
  const normalized = normalizeHeading(line);
  if (normalized.length === 0 || normalized.length > 40) return null;
  for (const [section, variants] of Object.entries(HEADINGS)) {
    if (variants.includes(normalized)) return section;
  }
  return null;
}

export function segmentSections(text: string): ResumeSections {
  const sections: ResumeSections = {};
  let current = "header";
  const buffer: string[] = [];
  const flush = () => {
    const body = buffer.join("\n").trim();
    if (body) sections[current] = sections[current] ? `${sections[current]}\n${body}` : body;
    buffer.length = 0;
  };
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    const matched = line ? matchSection(line) : null;
    if (matched) {
      flush();
      current = matched;
      continue;
    }
    buffer.push(rawLine);
  }
  flush();
  return sections;
}

export const SECTION_ORDER = [
  "header",
  "contact",
  "summary",
  "skills",
  "experience",
  "projects",
  "education",
  "certifications",
  "links",
];
