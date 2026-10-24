import Link from "next/link";
import { auth, signOut } from "@/auth";
import ThemeToggle from "./ThemeToggle";

// Shared top header, rendered on every page via the root layout.
// Signed-in users get module navigation + sign out; visitors get Sign in.
export default async function Header() {
  const session = await auth();
  const signedIn = Boolean(session?.user);

  return (
    <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-3">
        <Link href="/" className="text-lg font-bold tracking-tight">
          HireSense <span className="text-slate-500 dark:text-slate-400">AI</span>
        </Link>
        <nav aria-label="Main" className="flex flex-wrap items-center gap-4 text-sm">
          <ThemeToggle />
          {signedIn && (
            <>
              <Link href="/dashboard" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">Dashboard</Link>
              <Link href="/resume-lab" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">Resume Lab</Link>
              <Link href="/jd-match" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">JD Match</Link>
              <Link href="/interview" className="text-slate-600 dark:text-slate-400 hover:text-slate-900">Mock Interview</Link>
            </>
          )}
          {signedIn ? (
            <form
              action={async () => {
                "use server";
                await signOut({ redirectTo: "/" });
              }}
              className="flex items-center gap-3"
            >
              <span className="hidden text-slate-500 dark:text-slate-400 sm:inline">
                {session?.user?.name ?? session?.user?.email}
              </span>
              <button className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm">
                Sign out
              </button>
            </form>
          ) : (
            <Link href="/login" className="rounded-lg bg-slate-900 dark:bg-slate-100 px-4 py-2 text-sm font-medium text-white dark:text-slate-900">
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
