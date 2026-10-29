# HireSense AI

**Candidate-side interview prep:** upload a resume → get a deterministic
ATS score with a check-by-check breakdown → match it against a job
description, criterion by criterion, with verbatim evidence quotes →
practise mock interviews → turn every gap into a task and track your
applications.

[![Live demo](https://img.shields.io/badge/Live%20demo-hiresense--ai--s8ih.onrender.com-black)](https://hiresense-ai-s8ih.onrender.com)
![Tests](https://img.shields.io/badge/tests-175%20passing-black)
![License](https://img.shields.io/badge/license-MIT-black)

## 🚀 Live demo

**[hiresense-ai-s8ih.onrender.com](https://hiresense-ai-s8ih.onrender.com)** —
sign in with the public demo account: **`demo` / `demo1234`**.

(On Render's free tier the service sleeps when idle, so the first visit
after a while can take up to a minute to wake. Uploaded resumes live on
the service's local disk and don't survive redeploys — see the roadmap.)

## What it does

- **Resume Lab** — upload a PDF/DOCX resume; text is extracted, split
  into sections, and scored by deterministic ATS rules (5 weighted
  categories). Every check shows its result and explanation.
- **JD Match** — paste a job description and the app drafts match
  criteria (AI when a key is set, else a heuristic extractor). **Edit
  the criteria before scoring**, then run the match: every criterion
  gets a score (100 / 70 / 40 / 0), a verbatim evidence quote from your
  resume, and a concrete fix action for every gap.
- **Mock Interview** — tracks (HR, Technical, DSA, Frontend) ×
  difficulty, 5 questions one at a time, scored on a fixed rubric
  (relevance 30, depth 25, structure 20, confidence 15, conciseness
  10). Ends with a report: overall score, per-topic scores, weakest
  areas.
- **Applications + gap tasks** — track applications (Applied →
  Interview → Offer / Rejected), and push one-click tasks from JD Match
  gaps and interview weak areas into a todo/doing/done checklist
  (duplicates skipped).
- **The core promise: scores are deterministic.** AI (optional, below)
  drafts criteria, generates questions, and writes feedback — it never
  computes a score.

## The interface

A React single-page app (Vite) talking to a Django JSON API with
session auth — plus the original server-rendered Django pages, still
available at their trailing-slash URLs. The UI is a monochrome
"editorial" design: pure black & white, bold Archivo type, hairline
panels, a **dark/light toggle** (your choice is remembered), and a
subtle cursor-tracking glow.

## Tech stack

| Layer | What |
| --- | --- |
| Backend | Django 5.2 (LTS), Python 3.12 |
| Frontend | React 19 + Vite, react-router-dom |
| Database | SQLite by default; Postgres (Supabase) via `DATABASE_URL` |
| Auth | Django sessions; optional Google OAuth (django-allauth) |
| AI (optional) | Groq / Gemini via plain `urllib` — no SDK dependencies |
| Production | gunicorn + WhiteNoise, Render Blueprint (`render.yaml`) |
| Tests | 175 Django tests (scoring, flows, API, OAuth, DB switch, AI fallbacks — all AI calls mocked) |

## How the code is organised

| Path | What it is |
| --- | --- |
| `config/` | Project settings + root URL map (incl. `SPA_ROUTES`, which serve the React app) |
| `api/` | JSON API for the React app (auth, dashboard, resumes, JD match, interviews, applications, tasks) |
| `frontend/` | The React app (Vite) — see `frontend/README.md` |
| `resumes/` | Resume model, upload/extraction, the scoring library (`scoring.py`, `interview.py`), Groq/Gemini clients |
| `jdmatch/` | JD Match models + HTML pages (criteria drafting, evidence, gaps) |
| `interview/` | Mock-interview sessions + HTML pages |
| `applications/` | Application tracker + gap tasks (+ the push-from-gap helpers the API reuses) |
| `accounts/` | Login/logout, `seed_demo` command, Google OAuth guards |
| `dashboard/` | HTML dashboard view (the React dashboard reads `/api/dashboard/`) |
| `templates/` | Shared layout for the HTML pages |

This project began as a Next.js app; that version is preserved on the
`archive/nextjs` branch. The Django rebuild ported its scoring
line-by-line — same inputs give the same scores, including the worked
example (74.0).

## Run it locally

```bash
git clone https://github.com/pawanriko/hiresense-ai.git
cd hiresense-ai

# 1. Virtual environment (Python 3.12 recommended)
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1
# macOS/Linux:  source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Database + demo user
python manage.py migrate
python manage.py seed_demo

# 4. Run, then open http://127.0.0.1:8000/
python manage.py runserver
```

Sign in as `demo` / `demo1234`. The server serves the pre-built React
app from `frontend/dist` when it exists (in a fresh clone, build it
once: `cd frontend && npm install && npm run build`), and the HTML
pages either way.

> **Python 3.13+ note:** `psycopg[binary]` (the Postgres driver) may
> not have a wheel for the newest Python yet. SQLite mode never uses
> it — if `pip install` fails on psycopg, install everything else and
> skip it: `pip install Django==5.2.18 pypdf==6.21.2 python-docx==1.2.0 django-allauth==65.20.1 requests==2.34.2 python-dotenv==1.2.4 gunicorn==23.0.0 whitenoise==6.9.0`

**Frontend development** (hot reload): run Django on :8000 as above,
then `cd frontend && npm install && npm run dev` and open
http://localhost:5173 — Vite proxies `/api` to Django, so session login
works exactly like production.

## Tests

```bash
python manage.py test
```

175 tests: the JD Match rubric and ATS scorer, criteria extraction,
the interview checklist (incl. the relevance regression), upload flows,
owner-only rules everywhere, the full JSON API, the Google OAuth flow
(mocked network calls), the SQLite↔Postgres switch, and every AI
provider path with mocked clients — including the rule that any AI
failure falls back silently and never changes a score.

## Optional integrations

Everything below is opt-in via a `.env` file next to `manage.py`
(copy `.env.example`). With no keys at all, the app is fully functional
on SQLite + the demo login.

### Google OAuth login

The app ships ready for Google sign-in, but you must register your own
OAuth client once (≈5 minutes):

1. [Google Cloud Console](https://console.cloud.google.com/) → create
   a project → **APIs & Services → OAuth consent screen**: app name
   `HireSense AI`, External audience, your email as support/contact.
2. **APIs & Services → Credentials → Create Credentials → OAuth client
   ID** → Web application → under **Authorized redirect URIs** paste
   exactly:
   `http://127.0.0.1:8000/accounts/google/login/callback/`
   (character-for-character; `127.0.0.1`, not `localhost`).
3. Put the client ID/secret in `.env` as `GOOGLE_OAUTH_CLIENT_ID` /
   `GOOGLE_OAUTH_CLIENT_SECRET`, restart the server — a **Sign in with
   Google** button appears on the login page. Keys absent = button
   hidden, demo login untouched. `.env` is gitignored.
4. Production: add your deployed callback URL (e.g.
   `https://hiresense-ai-s8ih.onrender.com/accounts/google/login/callback/`)
   as a second redirect URI on the same client.

Troubleshooting: `redirect_uri_mismatch` = the URI differs by even one
character. Button still hidden = server reads `.env` only at startup;
restart it, and check the file is named exactly `.env`.

### Supabase Postgres

Set `DATABASE_URL` in `.env` and the app switches from SQLite to
Postgres — same models, same migrations, SSL on by default
(`sslmode=require`). Use the **Transaction pooler** connection string
(port 6543) from your Supabase project's **Settings → Database** page.

⚠️ Use a **fresh** Supabase project for this app. SQLite data does not
carry over (re-run `migrate` + `seed_demo`); uploads stay on local disk
either way. Delete the `DATABASE_URL` line and restart to switch back.

### AI providers (Groq / Gemini)

Set `GROQ_API_KEY` and/or `GEMINI_API_KEY` in `.env` (free keys:
console.groq.com, aistudio.google.com). Optional: `GROQ_MODEL`
(default `llama-3.3-70b-versatile`), `GEMINI_MODEL` (default
`gemini-2.0-flash`), `AI_PROVIDER` (`groq`/`gemini` to pin one; unset
= Groq first if its key is set, else Gemini — a pinned provider with a
missing key means no AI, never a silent switch).

With a key: JD Match drafts criteria with AI, interview questions are
generated from the JD + company + track + difficulty, and answers get
AI feedback on the same rubric. **Any failure falls back silently** to
the heuristic/bank/checklist. Scores stay deterministic, always.

## Deploying to Render

The repo ships a Blueprint (`render.yaml`): one web service (Django +
the built React app via WhiteNoise) and one free Postgres database.

1. render.com → connect GitHub → **New → Blueprint** → select this
   repo. Render creates both resources from `render.yaml`.
2. The build installs Python + Node deps, builds the React app,
   collects static files, migrates, and runs `seed_demo` — so the demo
   login exists on the live database (Render's Shell is paid-only;
   the build is how free-tier seeding happens).
3. Later code pushes need a **Manual Deploy → Deploy latest commit**
   from the service page (Blueprint services don't auto-deploy on
   every push); if `render.yaml` itself changed, run a **Blueprint
   Manual sync** first so the new build command is picked up.
4. Optional env vars: `GROQ_API_KEY`, `GEMINI_API_KEY`.

Production notes: `DEBUG=False`, `SECRET_KEY` generated by Render,
secure cookies + `SECURE_PROXY_SSL_HEADER` when not debugging, the SPA
and `/api` share one origin so session + CSRF cookies just work.

## Roadmap

- **Supabase Storage for uploads** — so resumes survive redeploys.
- **Interview grounding in the resume** (the original Next.js version
  linked sessions to a resume; Django sessions don't yet).
- AI extras from the original: resume rewrites, cover letters.

## Author

**Pawan Kumar** — BCA student, New Delhi.
GitHub: [pawanriko](https://github.com/pawanriko) ·
LinkedIn: [in/pawanriko](https://www.linkedin.com/in/pawanriko)

## License

MIT — see [LICENSE](LICENSE).
