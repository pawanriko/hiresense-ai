"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "hiresense-theme";

// Dark/light toggle. The choice is stored in localStorage and applied to
// <html> as the `dark` class (see globals.css); a blocking script in the root
// layout applies the stored choice before first paint to avoid a flash.
export default function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    const initial =
      stored === "dark" || stored === "light"
        ? stored
        : window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
    setTheme(initial);
    document.documentElement.classList.toggle("dark", initial === "dark");
    setReady(true);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.classList.toggle("dark", next === "dark");
  }

  return (
    <button
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm dark:border-slate-700"
    >
      {ready && theme === "dark" ? (
        <span aria-hidden="true">☀️ Light</span>
      ) : (
        <span aria-hidden="true">🌙 Dark</span>
      )}
    </button>
  );
}
