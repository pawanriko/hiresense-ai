import { NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { auth } from "@/auth";
import { getServiceClient, isSupabaseConfigured } from "@/lib/supabase/server";
import {
  detectFileType,
  parseResumeBuffer,
  MAX_FILE_BYTES,
} from "@/lib/parsing/parse-resume";
import { computeAts } from "@/lib/scoring/ats";

const BUCKET = "resumes";

function errorJson(code: string, message: string, status: number) {
  return NextResponse.json({ error: { code, message } }, { status });
}

// POST /api/resumes — upload a resume (PDF/DOCX), store it privately, parse it,
// and return the created version with its detected sections.
export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.id) return errorJson("unauthorized", "Please sign in first.", 401);
  if (!isSupabaseConfigured()) {
    return errorJson("not_configured", "Storage is not configured yet (Supabase keys missing).", 503);
  }
  const supabase = getServiceClient()!;

  const form = await request.formData();
  const file = form.get("file");
  if (!(file instanceof File)) return errorJson("no_file", "No file was uploaded.", 400);
  if (file.size === 0) return errorJson("empty_file", "The uploaded file is empty.", 400);
  if (file.size > MAX_FILE_BYTES) return errorJson("too_large", "File is larger than 10 MB.", 413);

  const fileType = detectFileType(file.name, file.type);
  if (!fileType) return errorJson("bad_type", "Only PDF and DOCX resumes are supported.", 415);

  const userId = session.user.id;
  const buffer = Buffer.from(await file.arrayBuffer());
  const filePath = `${userId}/${randomUUID()}.${fileType}`;

  const upload = await supabase.storage.from(BUCKET).upload(filePath, buffer, {
    contentType: file.type || (fileType === "pdf" ? "application/pdf" : undefined),
    upsert: false,
  });
  if (upload.error) return errorJson("storage_failed", "Could not store the file. Please try again.", 502);

  // Version = count of this user's previous resumes + 1.
  const { count } = await supabase
    .from("resumes")
    .select("id", { count: "exact", head: true })
    .eq("user_id", userId);
  const version = (count ?? 0) + 1;

  let parseStatus: "parsed" | "failed" = "parsed";
  let parseError: string | null = null;
  let parsedText: string | null = null;
  let sections: Record<string, string> = {};
  try {
    const parsed = await parseResumeBuffer(buffer, fileType);
    parsedText = parsed.text;
    sections = parsed.sections;
  } catch (err) {
    parseStatus = "failed";
    parseError = err instanceof Error ? err.message : "Could not parse this file.";
  }

  // ATS health score is computed at upload time so Resume Lab can show it
  // immediately (the detail endpoint recomputes it the same way).
  const atsScore =
    parseStatus === "parsed" ? computeAts(sections, parsedText).score : null;

  const { data, error } = await supabase
    .from("resumes")
    .insert({
      user_id: userId,
      version,
      file_name: file.name,
      file_path: filePath,
      file_type: fileType,
      parsed_text: parsedText,
      sections,
      parse_status: parseStatus,
      parse_error: parseError,
      ats_score: atsScore,
    })
    .select("id, version, file_name, file_type, parse_status, parse_error, sections, ats_score, created_at")
    .single();
  if (error) return errorJson("db_failed", "Could not save the resume record.", 502);

  await supabase.from("audit_events").insert({
    user_id: userId,
    action: "resume_uploaded",
    entity: "resumes",
    entity_id: data.id,
  });

  return NextResponse.json({ resume: data }, { status: 201 });
}

// GET /api/resumes — list the signed-in user's resume versions (newest first).
export async function GET() {
  const session = await auth();
  if (!session?.user?.id) return errorJson("unauthorized", "Please sign in first.", 401);
  if (!isSupabaseConfigured()) {
    return NextResponse.json({ resumes: [], configured: false });
  }
  const supabase = getServiceClient()!;
  const { data, error } = await supabase
    .from("resumes")
    .select("id, version, file_name, file_type, parse_status, ats_score, created_at")
    .eq("user_id", session.user.id)
    .order("created_at", { ascending: false });
  if (error) return errorJson("db_failed", "Could not load resumes.", 502);
  return NextResponse.json({ resumes: data ?? [], configured: true });
}
