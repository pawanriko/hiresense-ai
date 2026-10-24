import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";
import { coverLetterAi, isGroqConfigured } from "@/lib/ai/groq";

// POST /api/matches/:id/cover-letter — cover letter from resume + JD.
// AI when configured; otherwise a structured template letter built only from
// the resume's own evidence (never invented). Stored as a generated doc.
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
    "id, match_score, criteria_results, resumes(parsed_text), job_descriptions(title, company, raw_text)"
  );
  if (!analysis) return errorJson("not_found", "Analysis not found.", 404);

  const jd = analysis.job_descriptions as { title?: string; company?: string; raw_text?: string } | null;
  const resumeText = (analysis.resumes as { parsed_text?: string | null } | null)?.parsed_text ?? "";
  const strengths = ((analysis.criteria_results ?? []) as { name: string; score: number }[])
    .filter((r) => r.score >= 70)
    .slice(0, 3)
    .map((r) => r.name);

  let letter: string | null = null;
  let source = "template";
  if (isGroqConfigured()) {
    letter = await coverLetterAi(resumeText, jd?.raw_text ?? "", analysis.match_score ?? 0, strengths);
    if (letter) source = "ai";
  }
  if (!letter) {
    const role = jd?.title ?? "this role";
    const company = jd?.company ? ` at ${jd.company}` : "";
    const strengthLine =
      strengths.length > 0
        ? `My strongest matches for this role are ${strengths.join(", ")}.`
        : "My background aligns with several of the role's requirements.";
    letter = [
      `Dear Hiring Manager,`,
      ``,
      `I am applying for ${role}${company}. ${strengthLine}`,
      ``,
      `My recent work is summarised in my resume, including the projects and experience that evidence the skills above. I am particularly interested in this role because it lets me apply that experience to real problems and keep growing as an engineer.`,
      ``,
      `I would welcome the chance to discuss how I can contribute to your team. Thank you for your consideration.`,
      ``,
      `Sincerely,`,
      `Candidate`,
    ].join("\n");
  }

  const supabase = getServiceClient()!;
  await supabase.from("generated_docs").insert({
    analysis_id: id,
    kind: "cover_letter",
    content: letter,
  });
  return NextResponse.json({ letter, source });
}
