import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";

// PATCH /api/prep-tasks/:id — move a task between todo / doing / done.
export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const row = await ownedRow("prep_tasks", id, userId, "id");
  if (!row) return errorJson("not_found", "Prep task not found.", 404);
  const body = await request.json().catch(() => null);
  if (!["todo", "doing", "done"].includes(body?.status)) {
    return errorJson("bad_input", "status must be todo, doing, or done.", 400);
  }
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("prep_tasks")
    .update({ status: body.status })
    .eq("id", id)
    .eq("user_id", userId)
    .select("id, title, source_gap, status")
    .single();
  if (dbError) return errorJson("db_failed", "Could not update the task.", 502);
  return NextResponse.json({ task: data });
}
