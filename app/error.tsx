"use client";

import Link from "next/link";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16 text-center">
      <h1 className="text-3xl font-bold">Something went wrong</h1>
      <p className="mt-4 text-slate-600 dark:text-slate-400">
        The page hit an unexpected error. Your data is safe — try again, or head back to the
        dashboard.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <button
          onClick={() => reset()}
          className="rounded-lg bg-slate-900 dark:bg-slate-100 px-5 py-3 font-medium text-white dark:text-slate-900"
        >
          Try again
        </button>
        <Link href="/dashboard" className="rounded-lg border border-slate-300 dark:border-slate-700 px-5 py-3 font-medium">
          Go to dashboard
        </Link>
      </div>
    </main>
  );
}
