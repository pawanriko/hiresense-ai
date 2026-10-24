import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser } from "@/lib/api/helpers";

// POST /api/prep-tasks — add a single checklist task (e.g. from an
// interview report's weakest areas).
export async function POST(request: Request) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const body = await request.json().catch(() => null);
  const title = typeof body?.title === "string" ? body.title.trim() : "";
  if (!title) return errorJson("bad_input", "A task title is required.", 400);
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("prep_tasks")
    .insert({
      user_id: userId,
      analysis_id: typeof body?.analysis_id === "string" ? body.analysis_id : null,
      title: title.slice(0, 200),
      source_gap: typeof body?.source_gap === "string" ? body.source_gap : null,
      status: "todo",
    })
    .select("id, title, source_gap, status")
    .single();
  if (dbError) return errorJson("db_failed", "Could not create the task.", 502);
  return NextResponse.json({ task: data }, { status: 201 });
}

// GET /api/prep-tasks — my checklist (open tasks first).
export async function GET() {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("prep_tasks")
    .select("id, title, source_gap, status, created_at")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });
  if (dbError) return errorJson("db_failed", "Could not load prep tasks.", 502);
  return NextResponse.json({ tasks: data ?? [] });
}
