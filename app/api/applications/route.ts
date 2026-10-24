import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser } from "@/lib/api/helpers";

const STATUSES = ["Applied", "Interview", "Offer", "Rejected"] as const;

// GET /api/applications — my tracker rows (recently updated first).
export async function GET() {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("applications")
    .select("id, company, role, jd_id, status, notes, updated_at")
    .eq("user_id", userId)
    .order("updated_at", { ascending: false });
  if (dbError) return errorJson("db_failed", "Could not load applications.", 502);
  return NextResponse.json({ applications: data ?? [] });
}

// POST /api/applications — add a tracker row.
export async function POST(request: Request) {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const body = await request.json().catch(() => null);
  const company = typeof body?.company === "string" ? body.company.trim() : "";
  const role = typeof body?.role === "string" ? body.role.trim() : "";
  const status = typeof body?.status === "string" ? body.status : "Applied";
  if (!company || !role) return errorJson("bad_input", "Company and role are required.", 400);
  if (!STATUSES.includes(status as (typeof STATUSES)[number])) {
    return errorJson("bad_input", `status must be one of: ${STATUSES.join(", ")}.`, 400);
  }
  const supabase = getServiceClient()!;
  const { data, error: dbError } = await supabase
    .from("applications")
    .insert({
      user_id: userId,
      company,
      role,
      jd_id: typeof body?.jd_id === "string" ? body.jd_id : null,
      status,
      notes: typeof body?.notes === "string" ? body.notes : null,
    })
    .select("id, company, role, jd_id, status, notes, updated_at")
    .single();
  if (dbError) return errorJson("db_failed", "Could not add the application.", 502);
  return NextResponse.json({ application: data }, { status: 201 });
}
