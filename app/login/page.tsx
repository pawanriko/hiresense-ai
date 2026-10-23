import { signIn } from "@/auth";

export default function LoginPage() {
  const googleReady = Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
  const demoReady = Boolean(process.env.DEMO_USER_EMAIL && process.env.DEMO_USER_PASSWORD);

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="text-3xl font-bold">Welcome to HireSense AI</h1>
      <p className="mt-2 text-slate-600">
        Sign in to score your resume against any job description.
      </p>

      <div className="mt-8 space-y-6">
        <form
          action={async () => {
            "use server";
            await signIn("google", { redirectTo: "/dashboard" });
          }}
        >
          <button
            type="submit"
            disabled={!googleReady}
            className="w-full rounded-lg bg-slate-900 px-4 py-3 font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            Continue with Google
          </button>
          {!googleReady && (
            <p className="mt-2 text-center text-xs text-slate-500">
              Google login activates once OAuth keys are added to .env.local
            </p>
          )}
        </form>

        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="h-px flex-1 bg-slate-200" /> OR <span className="h-px flex-1 bg-slate-200" />
        </div>

        <form
          action={async (formData: FormData) => {
            "use server";
            formData.set("redirectTo", "/dashboard");
            await signIn("demo", formData);
          }}
          className="space-y-3"
        >
          <input
            name="email"
            type="email"
            required
            placeholder="Demo email"
            className="w-full rounded-lg border border-slate-300 px-4 py-3"
          />
          <input
            name="password"
            type="password"
            required
            placeholder="Demo password"
            className="w-full rounded-lg border border-slate-300 px-4 py-3"
          />
          <button
            type="submit"
            disabled={!demoReady}
            className="w-full rounded-lg border border-slate-900 px-4 py-3 font-medium disabled:cursor-not-allowed disabled:opacity-40"
          >
            Try the demo account
          </button>
          {!demoReady && (
            <p className="text-center text-xs text-slate-500">
              Demo login activates once DEMO_USER_EMAIL / DEMO_USER_PASSWORD are set
            </p>
          )}
        </form>
      </div>
    </main>
  );
}
