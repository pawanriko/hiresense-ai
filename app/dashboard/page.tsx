import Link from "next/link";
import { auth, signOut } from "@/auth";
import { getServiceClient, isSupabaseConfigured } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

interface ResumeRow {
  id: string;
  version: number;
  file_name: string;
  parse_status: string;
  ats_score: number | null;
  created_at: string;
}

export default async function DashboardPage() {
  const session = await auth();
  const configured = isSupabaseConfigured();
  let resumes: ResumeRow[] = [];
  if (configured && session?.user?.id) {
    const supabase = getServiceClient()!;
    const { data } = await supabase
      .from("resumes")
      .select("id, version, file_name, parse_status, ats_score, created_at")
      .eq("user_id", session.user.id)
      .order("created_at", { ascending: false })
      .limit(5);
    resumes = (data as ResumeRow[]) ?? [];
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="mt-1 text-slate-600">
            Signed in as {session?.user?.name ?? session?.user?.email ?? "candidate"}
          </p>
        </div>
        <form
          action={async () => {
            "use server";
            await signOut({ redirectTo: "/" });
          }}
        >
          <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Sign out</button>
        </form>
      </header>

      {!configured && (
        <div className="mt-8 rounded-lg bg-amber-50 p-4 text-sm text-amber-800">
          Supabase is not configured yet — add the keys to <code>.env.local</code> (see docs/05) to
          enable uploads and stored data. Auth and pages already work.
        </div>
      )}

      <section className="mt-10 grid gap-4 sm:grid-cols-3">
        <Link href="/resume-lab" className="rounded-xl border border-slate-200 p-5 hover:border-slate-400">
          <h2 className="font-semibold">Resume Lab</h2>
          <p className="mt-1 text-sm text-slate-600">Upload a resume and see its parsed sections.</p>
        </Link>
        <div className="rounded-xl border border-dashed border-slate-200 p-5 text-slate-400">
          <h2 className="font-semibold">JD Match</h2>
          <p className="mt-1 text-sm">Coming in Build 2 — the scoring engine.</p>
        </div>
        <div className="rounded-xl border border-dashed border-slate-200 p-5 text-slate-400">
          <h2 className="font-semibold">Mock Interview</h2>
          <p className="mt-1 text-sm">Coming in Build 3.</p>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-semibold">Recent resume versions</h2>
        {resumes.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">
            None yet — head to the <Link className="underline" href="/resume-lab">Resume Lab</Link> and upload your first one.
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100 rounded-xl border border-slate-200">
            {resumes.map((r) => (
              <li key={r.id} className="flex items-center justify-between px-4 py-3 text-sm">
                <span>
                  <span className="font-medium">v{r.version}</span> · {r.file_name}
                </span>
                <span className="text-slate-500">
                  {r.parse_status}
                  {r.ats_score != null ? ` · ATS ${r.ats_score}` : ""} ·{" "}
                  {new Date(r.created_at).toLocaleDateString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
