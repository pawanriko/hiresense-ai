import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";

// POST /api/matches/:id/prep-tasks — push an analysis's gaps onto the
// Prep Dashboard as checklist tasks (skips titles already present).
export async function POST(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const analysis = await ownedRow("match_analyses", id, userId, "id, gaps");
  if (!analysis) return errorJson("not_found", "Analysis not found.", 404);

  const gaps = (analysis.gaps ?? []) as { criterion: string; suggested_action: string }[];
  if (gaps.length === 0) return NextResponse.json({ tasks: [], note: "No gaps to push." });

  const supabase = getServiceClient()!;
  const { data: existing } = await supabase
    .from("prep_tasks")
    .select("title")
    .eq("user_id", userId)
    .eq("analysis_id", id);
  const existingTitles = new Set((existing ?? []).map((t) => t.title));
  const rows = gaps
    .filter((g) => !existingTitles.has(`Close gap: ${g.criterion}`))
    .map((g) => ({
      user_id: userId,
      analysis_id: id,
      title: `Close gap: ${g.criterion}`,
      source_gap: g.suggested_action,
      status: "todo",
    }));
  if (rows.length === 0) return NextResponse.json({ tasks: [], note: "All gaps are already on your checklist." });
  const { data, error: dbError } = await supabase
    .from("prep_tasks")
    .insert(rows)
    .select("id, title, source_gap, status");
  if (dbError) return errorJson("db_failed", "Could not create prep tasks.", 502);
  return NextResponse.json({ tasks: data }, { status: 201 });
}
