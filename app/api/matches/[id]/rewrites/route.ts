import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";
import { rewriteBulletsAi, isGroqConfigured } from "@/lib/ai/groq";

// POST /api/matches/:id/rewrites — bullet rewrites for weak/missing criteria.
// AI when configured; otherwise honest template drafts that never invent facts
// (they are labelled "template" and the candidate edits before using them).
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
    "id, criteria_results, gaps, resumes(parsed_text, sections), job_descriptions(title)"
  );
  if (!analysis) return errorJson("not_found", "Analysis not found.", 404);

  const criteriaResults = (analysis.criteria_results ?? []) as {
    name: string;
    score: number;
    evidence: string | null;
  }[];
  const weak = criteriaResults.filter((r) => r.score < 100).slice(0, 6);
  if (weak.length === 0) {
    return NextResponse.json({ rewrites: [], source: "none", note: "Every criterion already scores 100 — nothing to rewrite." });
  }

  const supabase = getServiceClient()!;
  let source = "template";
  let drafts: { original: string; rewritten: string }[] = [];

  if (isGroqConfigured()) {
    const bullets = weak.map(
      (r) => r.evidence ?? `Experience using ${r.name}.`
    );
    const ai = await rewriteBulletsAi(
      bullets,
      weak.map((r) => r.name),
      (analysis.job_descriptions as { title?: string } | null)?.title ?? ""
    );
    if (ai) {
      source = "ai";
      drafts = weak.map((r, i) => ({
        original: r.evidence ?? `Experience using ${r.name}.`,
        rewritten: ai[i] ?? r.evidence ?? "",
      }));
    }
  }
  if (source === "template") {
    drafts = weak.map((r) => ({
      original: r.evidence ?? `Experience using ${r.name}.`,
      rewritten:
        r.score === 0
          ? `[Add a bullet] Built a small project with ${r.name}: describe what you made, the tools used, and one measurable outcome (users, time saved, or performance gain).`
          : `[Strengthen] ${r.evidence ?? ""} — add the result: what changed because of this work (a number, a before/after, or who benefited).`,
    }));
  }

  const rows = drafts.map((d) => ({
    analysis_id: id,
    original_bullet: d.original,
    rewritten_bullet: d.rewritten,
    accepted: false,
  }));
  const { data, error: dbError } = await supabase
    .from("resume_rewrites")
    .insert(rows)
    .select("id, original_bullet, rewritten_bullet, accepted");
  if (dbError) {
    // The migration table may not exist yet on older deployments — still
    // return the drafts so the feature works, and let the UI note it.
    return NextResponse.json({ rewrites: rows, source, stored: false });
  }
  return NextResponse.json({ rewrites: data, source, stored: true });
}
