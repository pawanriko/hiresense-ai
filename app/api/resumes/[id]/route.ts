import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser, ownedRow, audit } from "@/lib/api/helpers";
import { computeAts } from "@/lib/scoring/ats";

// GET /api/resumes/:id — resume detail incl. the ATS breakdown (owned only).
// The ATS score is computed on demand and stored back on the row.
export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const resume = await ownedRow(
    "resumes",
    id,
    userId,
    "id, version, file_name, file_type, parse_status, parse_error, sections, parsed_text, ats_score, created_at"
  );
  if (!resume) return errorJson("not_found", "Resume not found.", 404);

  let ats = null;
  if (resume.parse_status === "parsed") {
    ats = computeAts(
      (resume.sections ?? {}) as Record<string, string>,
      (resume.parsed_text as string | null) ?? null
    );
    if (resume.ats_score !== ats.score) {
      const supabase = getServiceClient()!;
      await supabase.from("resumes").update({ ats_score: ats.score }).eq("id", id).eq("user_id", userId);
    }
  }
  return NextResponse.json({ resume, ats });
}

// DELETE /api/resumes/:id — delete the file, the row, and (by cascade) its
// analyses; the deletion is recorded in audit_events.
export async function DELETE(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const resume = await ownedRow("resumes", id, userId, "id, file_path");
  if (!resume) return errorJson("not_found", "Resume not found.", 404);
  const supabase = getServiceClient()!;
  if (resume.file_path) {
    await supabase.storage.from("resumes").remove([resume.file_path as string]);
  }
  const { error: dbError } = await supabase
    .from("resumes")
    .delete()
    .eq("id", id)
    .eq("user_id", userId);
  if (dbError) return errorJson("db_failed", "Could not delete the resume.", 502);
  await audit(userId, "resume_deleted", "resumes", id);
  return NextResponse.json({ deleted: true });
}
