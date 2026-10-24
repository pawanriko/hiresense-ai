import { NextResponse } from "next/server";
import { errorJson, requireUser, ownedRow } from "@/lib/api/helpers";

// GET /api/interviews/:id/report — final report for a completed session.
export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const { id } = await context.params;
  const session = await ownedRow(
    "mock_sessions",
    id,
    userId,
    "id, track, difficulty, status, overall_score, transcript, report, created_at"
  );
  if (!session) return errorJson("not_found", "Interview session not found.", 404);
  if (session.status !== "completed") {
    return errorJson("not_ready", "This interview is still in progress.", 409);
  }
  return NextResponse.json({ session });
}
