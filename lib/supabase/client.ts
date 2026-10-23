import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// Browser Supabase client (anon key). Used only for signed-URL downloads;
// all data access goes through Next.js API routes.
let cached: SupabaseClient | null = null;

export function getBrowserClient(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  if (!cached) cached = createClient(url, key);
  return cached;
}
