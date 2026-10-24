import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";

// POST /api/matches/:id/tailored-resume — a deterministic tailored resume draft:
// the candidate's own sections, reordered so the JD's strongest-matching
// evidence comes first, with weak/missing criteria flagged as "add evidence".
// Nothing is invented: every line comes from the uploaded resume.
export async function POST(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const analysis = await ownedRow(
    "match_analyses",
    id,
    userId,
    "id, match_score, criteria_results, gaps, resumes(file_name, sections, parsed_text), job_descriptions(title, company)"
  );
  if (!analysis) return errorJson("not_found", "Analysis not found.", 404);

  const sections = ((analysis.resumes as { sections?: Record<string, string> } | null)?.sections ?? {}) as Record<string, string>;
  const results = (analysis.criteria_results ?? []) as { name: string; score: number; evidence: string | null }[];
  const gaps = (analysis.gaps ?? []) as { criterion: string; suggested_action: string }[];
  const jd = analysis.job_descriptions as { title?: string; company?: string } | null;

  const lines: string[] = [];
  lines.push(`# Tailored resume — ${jd?.title ?? "Target role"}${jd?.company ? ` (${jd.company})` : ""}`);
  lines.push(``, `Match score: ${analysis.match_score}/100 — tailored from the uploaded resume. Nothing below is invented; gaps are flagged, not filled.`, ``);
  lines.push(`## Skills matched to this JD`);
  for (const r of [...results].sort((a, b) => b.score - a.score)) {
    lines.push(`- ${r.name}: ${r.score}/100${r.evidence ? ` — "${r.evidence}"` : " — no evidence yet"}`);
  }
  lines.push(``);
  const order = ["header", "summary", "skills", "experience", "projects", "education", "certifications"];
  for (const key of order) {
    if (sections[key]?.trim()) {
      lines.push(`## ${key[0].toUpperCase()}${key.slice(1)}`, ``, sections[key].trim(), ``);
    }
  }
  if (gaps.length > 0) {
    lines.push(`## Gaps to close before applying`);
    for (const g of gaps) lines.push(`- ${g.criterion}: ${g.suggested_action}`);
    lines.push(``);
  }
  const content = lines.join("\n");

  const supabase = getServiceClient()!;
  await supabase.from("generated_docs").insert({
    analysis_id: id,
    kind: "tailored_resume",
    content,
  });
  return NextResponse.json({ content, source: "deterministic" });
}
