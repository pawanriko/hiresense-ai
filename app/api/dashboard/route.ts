import { NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase/server";
import { errorJson, requireUser } from "@/lib/api/helpers";

// GET /api/dashboard — one call for the dashboard: latest match score,
// score trend, open prep tasks, and application counts by status.
export async function GET() {
  const { userId, error } = await requireUser();
  if (userId === null) return error;
  const supabase = getServiceClient()!;

  const [{ data: analyses }, { data: tasks }, { data: applications }, { data: resumes }] =
    await Promise.all([
      supabase
        .from("match_analyses")
        .select("id, match_score, created_at, job_descriptions(title, company)")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(10),
      supabase
        .from("prep_tasks")
        .select("id, title, source_gap, status")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(20),
      supabase
        .from("applications")
        .select("status")
        .eq("user_id", userId),
      supabase
        .from("resumes")
        .select("id, version, file_name, ats_score, created_at")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(5),
    ]);

  const appCounts: Record<string, number> = { Applied: 0, Interview: 0, Offer: 0, Rejected: 0 };
  for (const a of applications ?? []) {
    if (a.status in appCounts) appCounts[a.status as string] += 1;
  }
  const trend = [...(analyses ?? [])]
    .reverse()
    .map((a) => ({ score: a.match_score, date: a.created_at }));

  return NextResponse.json({
    latest_score: analyses?.[0]?.match_score ?? null,
    latest_analysis_id: analyses?.[0]?.id ?? null,
    trend,
    analyses: analyses ?? [],
    tasks: tasks ?? [],
    open_tasks: (tasks ?? []).filter((t) => t.status !== "done").length,
    application_counts: appCounts,
    resumes: resumes ?? [],
  });
}
