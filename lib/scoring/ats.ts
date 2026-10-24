// ATS health score — rule-based, independent of any JD (docs/03 §4).
// Every deduction names the failed check. Pure function, unit-tested.

import { ACTION_VERBS, splitSentences, type ResumeSections } from "./evidence";

export interface AtsCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface AtsCategory {
  name: string;
  weight: number;
  score: number;
  checks: AtsCheck[];
}

export interface AtsResult {
  score: number;
  categories: AtsCategory[];
}

const EMAIL = /[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/i;
const LINK = /(github\.com|linkedin\.com|portfolio|vercel\.app|netlify\.app|behance|dribbble)/i;
const DATE_LIKE = /\b(20\d{2}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b/i;

function bullets(sections: ResumeSections): string[] {
  const body = [sections.experience ?? "", sections.projects ?? ""].join("\n");
  return splitSentences(body).filter((s) => s.length > 10);
}

export function computeAts(
  sections: ResumeSections,
  parsedText: string | null
): AtsResult {
  const allText = Object.values(sections).join("\n");
  const words = (parsedText ?? allText).split(/\s+/).filter(Boolean).length;
  const present = (key: string) => Boolean(sections[key]?.trim());
  const bulletsList = bullets(sections);
  const quantified = bulletsList.filter((b) => /\d/.test(b)).length;
  const verbLed = bulletsList.filter((b) =>
    ACTION_VERBS.some((v) => b.toLowerCase().startsWith(v) || b.toLowerCase().includes(` ${v} `))
  ).length;

  const categories: AtsCategory[] = [
    {
      name: "Sections",
      weight: 35,
      score: 0,
      checks: [
        { name: "Contact info present", passed: present("contact") || present("header"), detail: present("contact") || present("header") ? "Found a header/contact block." : "No header or contact section detected — add name, email, phone." },
        { name: "Summary present", passed: present("summary"), detail: present("summary") ? "Summary detected." : "No summary section — add a 2–3 line professional summary." },
        { name: "Skills present", passed: present("skills"), detail: present("skills") ? "Skills detected." : "No skills section detected." },
        { name: "Experience or Projects present", passed: present("experience") || present("projects"), detail: present("experience") || present("projects") ? "Experience/Projects detected." : "Neither experience nor projects detected — recruiters need proof of work." },
        { name: "Education present", passed: present("education"), detail: present("education") ? "Education detected." : "No education section detected." },
      ],
    },
    {
      name: "Quantification",
      weight: 20,
      score: 0,
      checks: [
        { name: "Bullets carry numbers/results", passed: bulletsList.length > 0 && quantified / bulletsList.length >= 0.3, detail: bulletsList.length === 0 ? "No experience/project bullets found to measure." : `${quantified} of ${bulletsList.length} bullets contain a number or result (${Math.round((quantified / bulletsList.length) * 100)}%; aim for 30%+).` },
      ],
    },
    {
      name: "Action verbs",
      weight: 20,
      score: 0,
      checks: [
        { name: "Bullets start with action verbs", passed: bulletsList.length > 0 && verbLed / bulletsList.length >= 0.5, detail: bulletsList.length === 0 ? "No experience/project bullets found to measure." : `${verbLed} of ${bulletsList.length} bullets use an action verb (${Math.round((verbLed / bulletsList.length) * 100)}%; aim for 50%+).` },
      ],
    },
    {
      name: "Contact & links",
      weight: 15,
      score: 0,
      checks: [
        { name: "Email present", passed: EMAIL.test(allText), detail: EMAIL.test(allText) ? "Email found." : "No email address detected — ATS parsers and recruiters need one." },
        { name: "Portfolio / GitHub / LinkedIn link", passed: LINK.test(allText), detail: LINK.test(allText) ? "A profile link was found." : "No GitHub, LinkedIn, or portfolio link detected." },
      ],
    },
    {
      name: "Length & format",
      weight: 10,
      score: 0,
      checks: [
        { name: "Parseable text (not image-only)", passed: words >= 50, detail: words >= 50 ? `${words} words extracted.` : `Only ${words} words extracted — the file may be image-based or nearly empty.` },
        { name: "Reasonable length (150–1500 words)", passed: words >= 150 && words <= 1500, detail: words < 150 ? `Only ${words} words — likely too thin for a full resume.` : words > 1500 ? `${words} words — likely too long; aim for a tight 1–2 page resume.` : `${words} words — in range.` },
        { name: "Dates present", passed: DATE_LIKE.test(allText), detail: DATE_LIKE.test(allText) ? "Dates detected in experience/education." : "No dates detected — add timelines to experience and education." },
      ],
    },
  ];

  for (const cat of categories) {
    const passed = cat.checks.filter((c) => c.passed).length;
    cat.score = cat.checks.length > 0 ? Math.round((passed / cat.checks.length) * 100) : 0;
  }
  const totalWeight = categories.reduce((s, c) => s + c.weight, 0);
  const score = Math.round(
    categories.reduce((s, c) => s + c.score * c.weight, 0) / totalWeight
  );
  return { score, categories };
}
