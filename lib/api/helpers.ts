import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { getServiceClient, isSupabaseConfigured } from "@/lib/supabase/server";

export function errorJson(code: string, message: string, status: number) {
  return NextResponse.json({ error: { code, message } }, { status });
}

type RequireUserResult =
  | { userId: string; error: null }
  | { userId: null; error: NextResponse };

export async function requireUser(): Promise<RequireUserResult> {
  const session = await auth();
  if (!session?.user?.id) return { userId: null, error: errorJson("unauthorized", "Please sign in first.", 401) };
  if (!isSupabaseConfigured()) {
    return { userId: null, error: errorJson("not_configured", "Supabase is not configured.", 503) };
  }
  return { userId: session.user.id, error: null };
}

/** Fetch one row the user owns, or return null.
 *  Typed as `any` on purpose: Supabase's untyped client (dynamic table names)
 *  otherwise resolves `.single()` rows to its error type and every call site
 *  needs a cast. Call sites validate the fields they actually use. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function ownedRow(
  table: string,
  id: string,
  userId: string,
  columns = "*"
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<any | null> {
  const supabase = getServiceClient()!;
  const { data, error } = await supabase
    .from(table)
    .select(columns)
    .eq("id", id)
    .eq("user_id", userId)
    .single();
  if (error || !data) return null;
  return data;
}

export async function audit(userId: string, action: string, entity: string, entityId?: string) {
  const supabase = getServiceClient()!;
  await supabase.from("audit_events").insert({
    user_id: userId,
    action,
    entity,
    entity_id: entityId ?? null,
  });
}

export function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

export type CriterionInput = {
  name: string;
  category: string;
  weight: number;
  required: boolean;
};

export function validCriteria(input: unknown): CriterionInput[] | null {
  if (!Array.isArray(input) || input.length === 0 || input.length > 30) return null;
  const out: CriterionInput[] = [];
  for (const c of input) {
    if (typeof c !== "object" || c === null) return null;
    const rec = c as Record<string, unknown>;
    if (typeof rec.name !== "string" || !rec.name.trim()) return null;
    if (typeof rec.weight !== "number" || rec.weight < 0 || rec.weight > 100) return null;
    out.push({
      name: rec.name.trim().slice(0, 80),
      category: typeof rec.category === "string" ? rec.category : "skill",
      weight: Math.round(rec.weight),
      required: rec.required === true,
    });
  }
  return out;
}
