import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";

const STATUSES = ["Applied", "Interview", "Offer", "Rejected"] as const;

// PATCH /api/applications/:id — move a tracker row (status / notes).
export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const row = await ownedRow("applications", id, userId, "id");
  if (!row) return errorJson("not_found", "Application not found.", 404);
  const body = await request.json().catch(() => null);
  const patch: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (typeof body?.status === "string") {
    if (!STATUSES.includes(body.status as (typeof STATUSES)[number])) {
      return errorJson("bad_input", `status must be one of: ${STATUSES.join(", ")}.`, 400);
    }
    patch.status = body.status;
  }
  if (typeof body?.notes === "string") patch.notes = body.notes;
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("applications")
    .update(patch)
    .eq("id", id)
    .eq("user_id", userId)
    .select("id, company, role, jd_id, status, notes, updated_at")
    .single();
  if (dbError) return errorJson("db_failed", "Could not update the application.", 502);
  return NextResponse.json({ application: data });
}

// DELETE /api/applications/:id — remove a tracker row.
export async function DELETE(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const row = await ownedRow("applications", id, userId, "id");
  if (!row) return errorJson("not_found", "Application not found.", 404);
  const supabase = getServiceClient()!;
  const { error: dbError } = await supabase
    .from("applications")
    .delete()
    .eq("id", id)
    .eq("user_id", userId);
  if (dbError) return errorJson("db_failed", "Could not delete the application.", 502);
  return NextResponse.json({ deleted: true });
}
