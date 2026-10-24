import Spinner from "./components/Spinner";

// Shown on route transitions while the next page loads, so opening any link
// never shows a blank page.
export default function Loading() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <Spinner label="Loading HireSense AI…" />
      <div className="mx-auto mt-6 max-w-md space-y-3" aria-hidden="true">
        <div className="h-4 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
        <div className="h-4 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
      </div>
    </main>
  );
}
