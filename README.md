# HireSense AI

I'm the one sitting in interviews, so I built the tool I wanted on the candidate's side: upload your resume → get an ATS score with a check-by-check breakdown → match the resume against a job description, point by point, with actual quotes from your resume as proof → practise mock interviews → turn every gap into a task and keep track of your applications.

[![Live demo](https://img.shields.io/badge/Live%20demo-hiresense--ai--s8ih.onrender.com-black)](https://hiresense-ai-s8ih.onrender.com)
![Tests](https://img.shields.io/badge/tests-178%20passing-black)
![License](https://img.shields.io/badge/license-MIT-black)

## Try it live

**[hiresense-ai-s8ih.onrender.com](https://hiresense-ai-s8ih.onrender.com)** — there's a public demo account: **`demo` / `demo1234`**.

Two honest warnings: it's on Render's free tier, which sleeps when nobody visits, so the first load after a while can take up to a minute. And uploaded resumes are stored on the service's own disk, which Render wipes on redeploys — fixing that is on the roadmap below.

## What it does

- **Resume Lab** — upload a PDF or DOCX resume. The text gets extracted, split into sections, and scored by fixed ATS rules (5 weighted categories). Every single check shows what happened and why — no mysterious final number.
- **JD Match** — paste a job description and the app drafts the criteria it should check (with AI if a key is set, otherwise a built-in extractor). **You can edit the criteria before scoring.** Then it scores each one (100 / 70 / 40 / 0), quotes the exact line from your resume as evidence, and gives you a concrete fix for every gap.
- **Mock Interview** — pick a track (HR, Technical, DSA, Frontend) and a difficulty. Five questions, one at a time, scored on a fixed rubric (relevance 30, depth 25, structure 20, confidence 15, conciseness 10). At the end you get a report: overall score, per-topic scores, and your weakest areas.
- **Applications + gap tasks** — track applications (Applied → Interview → Offer / Rejected), and turn gaps from JD Match and weak areas from interviews into a todo/doing/done checklist with one click (it skips duplicates).
- **One rule I didn't compromise on: the scores are never computed by AI.** AI can draft criteria, generate questions and write feedback — it never touches a number. Every score comes from fixed rules, so the same resume always gets the same score.

## The interface

The frontend is a React single-page app (Vite) talking to a Django JSON API with InsForge auth (email + password, or Google via InsForge). The original server-rendered Django pages are still there too, at their normal URLs, on Django session login. The design is monochrome — black and white, bold type, thin borders — with a dark/light toggle that remembers your choice.

## Tech stack

| Layer | What |
| --- | --- |
| Backend | Django 5.2 (LTS), Python 3.12 |
| Frontend | React 19 + Vite, react-router-dom |
| Database | SQLite by default; Postgres (Supabase) via `DATABASE_URL` |
| Auth | InsForge JWT (RS256, verified via JWKS) for the API; Django sessions for the HTML pages + `/admin/` |
| AI (optional) | Groq / Gemini via plain `urllib` — no SDK dependencies |
| Production | gunicorn + WhiteNoise, Render Blueprint (`render.yaml`) |
| Tests | Django tests (scoring, flows, API, InsForge auth, DB switch, AI fallbacks — all AI calls mocked) |

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
| `accounts/` | Login/logout (HTML pages), `seed_demo` command |
| `dashboard/` | HTML dashboard view (the React dashboard reads `/api/dashboard/`) |
| `templates/` | Shared layout for the HTML pages |

A bit of history: this started as a Next.js app. That version is kept untouched on the `archive/nextjs` branch. When I rebuilt it in Django, I ported the scoring code line by line, so both versions give the same scores for the same input — including the worked example (74.0).

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

The HTML pages sign in as `demo` / `demo1234` (see `/accounts/login/`). The React app signs in through InsForge instead — it needs the InsForge variables first (see "InsForge auth" below), plus a built frontend: `cd frontend && npm install && npm run build`. The demo account in InsForge is `demo@hiresense.ai` / `demo1234`; the build links it to the Django demo user, so it sees the demo data.

> **Python 3.13+ note:** `psycopg[binary]` (the Postgres driver) may not have a wheel for the newest Python yet. SQLite mode never uses it — if `pip install` fails on psycopg, install everything else and skip it: `pip install Django==5.2.19 pypdf==6.21.2 python-docx==1.2.0 requests==2.34.2 python-dotenv==1.2.4 "PyJWT[crypto]==2.15.1" cryptography==50.0.2 gunicorn==23.0.0 whitenoise==6.9.0`

**Working on the frontend** (with hot reload): run Django on :8000 as above, then `cd frontend && npm install && npm run dev` and open http://localhost:5173. Vite proxies `/api` to Django, so logging in works exactly like production.

## Tests

```bash
python manage.py test
```

The suite covers the JD Match rubric and the ATS scorer, criteria extraction, the interview checklist (including the relevance regression), upload flows, owner-only rules everywhere, the full JSON API, the InsForge JWT auth (minted RS256 tokens, mocked JWKS fetch — expiry, wrong signatures, unknown keys, email collisions, the cutover flags, the CSRF exemption), the SQLite↔Postgres switch, and every AI provider path with mocked clients — including the rule that any AI failure falls back silently and never changes a score.

## Optional extras

Everything below is opt-in through a `.env` file next to `manage.py` (copy `.env.example`). With no keys at all, the HTML pages still work fully on SQLite with the demo login — but the React app needs the InsForge variables (see below), or its login page will say auth is not configured.

### InsForge auth

Sign-in for the React app lives in [InsForge](https://insforge.dev) (a backend-as-a-service): the browser signs users in against InsForge with email + password or Google, and Django verifies the resulting RS256 access tokens against InsForge's public JWKS — no shared secret, no password ever touches Django. User data still hangs off Django users, linked to InsForge identities by the token's `sub` claim (see `api/insforge_auth.py` and `api/models.py`).

To run it yourself:

1. Create a free InsForge account + project. Note the project's base URL (`https://<appkey>.us-east.insforge.app`) and its public **anon key** (dashboard → API keys — the anon key is browser-safe by design; never use the service/admin key in the frontend).
2. Backend (`.env` next to `manage.py`): `INSFORGE_AUTH_ENABLED=true` and `INSFORGE_BASE_URL=<project URL>`. That turns on dual-auth: Bearer tokens work alongside Django sessions for `/api/`.
3. Frontend (`frontend/.env`, gitignored): `VITE_INSFORGE_URL=<same project URL>` and `VITE_INSFORGE_ANON_KEY=<anon key>`. These are read at BUILD time — rebuild after changing them (`npm run build`, or restart `npm run dev`).
4. Create the demo account in InsForge (`demo@hiresense.ai` / `demo1234`), then link it to the Django demo user: `INSFORGE_LINK_MAP='{"demo@hiresense.ai": "<its InsForge user id>"}' python manage.py link_insforge_users --apply`. Run `--report` first to see link state. The command is all-or-nothing and idempotent; on Render it runs in the build, right after `seed_demo`.
5. Cutover: set `INSFORGE_AUTH_REQUIRED=true` as well. Now `/api/` is Bearer-only — session cookies no longer authenticate it. The HTML pages and `/admin/` keep Django sessions in every state (deliberate). Roll back by unsetting `INSFORGE_AUTH_REQUIRED`.

Known limits: InsForge access tokens are stateless — signing out drops the token locally, but the token stays valid until its 15-minute expiry. Email verification is off unless you configure SMTP in InsForge; with it off, the link command never auto-links on email alone (an email match proves nothing), so existing accounts can only be linked through the explicit mapping above.

### Supabase Postgres

Set `DATABASE_URL` in `.env` and the app switches from SQLite to Postgres — same models, same migrations, SSL on by default (`sslmode=require`). Use the **Transaction pooler** connection string (port 6543) from your Supabase project's **Settings → Database** page.

⚠️ Use a **fresh** Supabase project for this app, not one that already has another app's data in it. SQLite data doesn't carry over (run `migrate` + `seed_demo` again), and uploads stay on local disk either way. Delete the `DATABASE_URL` line and restart to switch back.

### AI providers (Groq / Gemini)

Set `GROQ_API_KEY` and/or `GEMINI_API_KEY` in `.env` (free keys from console.groq.com and aistudio.google.com). Optional extras: `GROQ_MODEL` (default `llama-3.3-70b-versatile`), `GEMINI_MODEL` (default `gemini-2.0-flash`), and `AI_PROVIDER` — set it to `groq` or `gemini` to pin one provider. Leave it unset and it uses Groq first if that key exists, else Gemini. If you pin a provider and its key is missing, you get no AI at all — it never silently switches to the other one.

With a key set: JD Match drafts its criteria with AI, interview questions are generated from the JD + company + track + difficulty, and answers get AI feedback on the same rubric. And if the AI call fails for any reason, the app falls back to the built-in questions/checklists without telling you anything broke. The scores stay rule-based either way.

## Deploying to Render

The repo has a Blueprint (`render.yaml`): one web service (Django + the built React app, served by WhiteNoise) and one free Postgres database.

1. render.com → connect GitHub → **New → Blueprint** → pick this repo. Render creates both resources from `render.yaml`.
2. The build installs the Python and Node dependencies, builds the React app, collects static files, migrates, runs `seed_demo`, and runs `link_insforge_users --apply` — that's how the demo login (and its InsForge link) exists on the live database, because Render's Shell is paid-only and the build has to do the seeding.
3. After pushing code later, deploy it with **Manual Deploy → Deploy latest commit** on the service page — Blueprint services don't auto-deploy on every push. If `render.yaml` itself changed, run a **Blueprint Manual sync** first so the new build command is picked up.
4. Env vars on the live service: the InsForge set (`INSFORGE_AUTH_ENABLED`, `INSFORGE_AUTH_REQUIRED`, `INSFORGE_BASE_URL`, `VITE_INSFORGE_URL`, `VITE_INSFORGE_ANON_KEY`, `INSFORGE_LINK_MAP`) — the Vite ones must be set BEFORE the deploy that builds the frontend. Optional AI vars: `GROQ_API_KEY`, `GEMINI_API_KEY`.

Production notes: `DEBUG=False`, `SECRET_KEY` generated by Render, secure cookies + `SECURE_PROXY_SSL_HEADER` when not debugging, and the SPA and `/api` share one origin so no CORS setup is needed.

## Roadmap

- **Supabase Storage for uploads**, so resumes survive redeploys.
- **Linking interview sessions to a resume** (the old Next.js version did this; the Django version doesn't yet).
- Two things the original had that I haven't ported: resume rewrites and cover letters.

## Author

**Pawan Kumar** — BCA student, New Delhi.
GitHub: [pawanriko](https://github.com/pawanriko) · LinkedIn: [in/pawanriko](https://www.linkedin.com/in/pawanriko)

## License

MIT — see [LICENSE](LICENSE).
