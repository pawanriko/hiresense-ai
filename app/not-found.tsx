import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16 text-center">
      <h1 className="text-4xl font-bold">404 — Page not found</h1>
      <p className="mt-4 text-slate-600 dark:text-slate-400">
        That page doesn&apos;t exist here. The app lives in four modules — start from any of them.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <Link href="/" className="rounded-lg bg-slate-900 dark:bg-slate-100 px-5 py-3 font-medium text-white dark:text-slate-900">
          Back home
        </Link>
        <Link href="/dashboard" className="rounded-lg border border-slate-300 dark:border-slate-700 px-5 py-3 font-medium">
          Go to dashboard
        </Link>
      </div>
    </main>
  );
}
