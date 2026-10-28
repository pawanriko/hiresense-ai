# HireSense AI — Django rebuild (slices 1–4 + Google OAuth + Supabase Postgres + Groq + Gemini AI)

A Python/Django rebuild of HireSense AI, the candidate-side interview-prep
tool: upload a resume, get a deterministic ATS score with a check-by-check
breakdown, match it against a job description, practise mock interviews,
then track applications and work through gap tasks. Slice 1 built the
foundation; slice 2 added the JD Match page; slice 3 added the Mock
Interview page; slice 4 added Applications and gap tasks. After slice 4,
Google OAuth login was added via django-allauth (see below), then the
Supabase Postgres swap, then optional Groq and Gemini AI (see below).

> Branding note: the product name is **HireSense AI** everywhere you see it
> (titles, header, footer). The folder name `hiresense-django` only exists
> to tell this copy apart from the original Next.js folder — it is not a
> new product name.

## What works end-to-end in slices 1–4 + Google OAuth + Supabase Postgres + Groq + Gemini AI

- **Demo login** with Django's built-in auth: sign in as
  `demo` / `demo1234` after running `seed_demo`.
- **Google OAuth login** (django-allauth, optional): when
  `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` are set (see
  "Google OAuth login" below), a "Sign in with Google" button appears on
  the login page and the full flow works — first Google login creates a
  Django user automatically and lands on the dashboard. When the keys
  are absent (the default), the button is hidden, a note says Google
  sign-in isn't configured, and the demo login works exactly as before
  — never a crash, never a broken redirect.
- **Dashboard home page**: your uploaded resumes and your latest ATS score.
- **Resume upload (PDF/DOCX)**: text is extracted, split into sections,
  and scored by the ported deterministic ATS rules. The result page shows
  every category and check with its explanation.
- **JD Match page** (`/jd-match/`, new in slice 2): paste a job
  description and the app drafts match criteria — AI (Groq or Gemini)
  when a key is set (see "AI providers" below), else the heuristic
  extractor. Edit names, categories, weights, and required flags — add
  and delete rows — and save them BEFORE scoring, exactly like the
  original. Then pick one of your parsed resumes and run the match:
  the result page shows the overall score, every criterion's score with
  its verbatim evidence quote and section, and every gap with a concrete
  fix action. Past matches are listed newest first and re-openable;
  JD and result pages are owner-only (other users get 404).
- **Mock Interview page** (`/interview/`, new in slice 3): pick a track
  (HR, Technical, DSA, Frontend) and difficulty, optionally add the
  company and JD text, then answer 5 questions one at a time. With a
  AI key set (see "AI providers" below), the 5 questions are generated
  from the JD + company + track + difficulty, and each answer gets AI
  feedback; without a key, the question bank and the deterministic
  checklist run instead. Either way the rubric is the same (relevance
  30%, depth 25%, structure 20%, confidence 15%, conciseness 10%) and
  each feedback is labelled with its source ("ai" or "checklist"). The
  finished session shows an overall report: overall score, scores by
  topic, weakest areas, and weakest question. Sessions are saved per
  user, listed newest first, re-openable, and owner-only; an abandoned
  in-progress session resumes at its next unanswered question.
- **Applications + gap tasks** (`/applications/`, new in slice 4):
  track job applications (company, role, status, notes, optional JD
  link) through the original's four stages — Applied, Interview, Offer,
  Rejected — listed recently updated first, with per-stage counts. The
  gap-task checklist (`/applications/tasks/`) holds manual tasks plus
  tasks pushed from a JD Match result's gaps ("Close gap: …") and from
  an interview report's weakest areas ("Practise interview topic: …"),
  with duplicate pushes skipped, done/undone toggles, todo/doing/done
  states, and open/done/all filters. The dashboard shows open and done
  task counts plus per-stage application counts, like the original.
- **Ported scoring library** (tested; the interview half now has its page):
  - `resumes/scoring.py` — section segmentation, the JD Match rubric
    (100 / 70 / 40 / 0 per criterion, weighted average), the ATS scorer,
    and the heuristic JD-criteria drafter. Ported line-by-line from the
    original app's `lib/scoring/` and `lib/parsing/` — same inputs give
    the same scores, including the worked example (74.0).
  - `resumes/interview.py` — the interview question bank, the
    deterministic answer checklist scorer, and the session report builder
    (overall = rounded mean of answer scores, topic scores, 2 weakest
    areas, weakest question), ported from `lib/interview/questions.ts`
    and the original answer route, including the relevance fix (question
    content words count, not just the topic label). Its page is the
    slice 3 `interview/` app.
- **No external services at runtime unless you opt in**: SQLite database,
  local file uploads, no API keys, no network calls — until you set the
  Google OAuth keys (only the Google sign-in flow talks to Google), a
  Supabase `DATABASE_URL` (only the database moves to Postgres), or a
  AI key (only criteria drafting, question generation, and answer
  feedback call Groq or Gemini — scores stay deterministic).

## How the code is organised (what lives where, and why)

| Path | What it is | Why it exists |
| --- | --- | --- |
| `config/` | Project settings + root URL map | Django's control room: installed apps, database, login redirects, top-level routes |
| `accounts/` | Login/logout + `seed_demo` command | Auth is Django built-in; we only add our templates and the demo seed |
| `resumes/` | Resume model, upload form/view, extraction, scoring | The heart of slice 1: file in, score out |
| `resumes/scoring.py` | Pure scoring functions | No database, no network — testable in isolation, portable |
| `resumes/interview.py` | Question bank + checklist scorer | Ready library for the slice-2 Interview page |
| `dashboard/` | Home page view + template | One place for "what do I see after login" |
| `jdmatch/` | JD Match models, forms, views, templates | Paste JD → edit criteria → run match → saved result |
| `jdmatch/models.py` | JobDescription + MatchAnalysis | Criteria/results stored as JSON, shown verbatim |
| `jdmatch/forms.py` | JD form, criterion formset row, run-match form | Validation mirrors the original API's rules |
| `interview/` | Interview session model, forms, views, templates | Start session → answer one at a time → report |
| `applications/` | Application + GapTask models, forms, views, templates | Track applications → push gaps/weakest areas → checklist |
| `interview/models.py` | InterviewSession | Transcript + report stored as JSON, shown verbatim |
| `accounts/context_processors.py` | `google_oauth` flag | Tells every template whether Google keys are set, so the login page can hide the button safely |
| `accounts/views.py` (guards) | Google login/callback guards | Delegate to allauth when configured; redirect to login with a message when not |
| `templates/base.html` | Shared header/footer layout | Every page extends it, so the shell is written once |

Django concepts used here, in one line each: **model** = a database table
as a Python class; **view** = a function turning a request into a response;
**URLconf** = the map from URLs to views; **template** = HTML with
placeholders; **migration** = a file describing a database change, applied
with `migrate`; **form** = input validation that shows friendly errors.

## Setup and run (exact commands)

```bash
cd ~/workspace/projects/hiresense-django

# 1. Create and activate the virtual environment (Python 3.12)
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database tables
python manage.py migrate

# 4. Create the demo login (demo / demo1234)
python manage.py seed_demo

# 5. (Optional) Create an admin account for /admin/
python manage.py createsuperuser

# 6. Run the dev server, then open http://127.0.0.1:8000/
python manage.py runserver
```

Sign in with username `demo`, password `demo1234`, then upload a PDF or
DOCX resume to see your ATS score and breakdown. (Or set up Google OAuth
below and sign in with Google instead.) Then open **JD Match**
in the header: paste a JD, edit the drafted criteria, save them, pick a
resume, and run the match. Then open **Mock Interview**: pick a track
and difficulty, answer the 5 questions one at a time, and read your
report at the end — past sessions stay listed for re-opening. Then open
**Applications**: track a job application through Applied → Interview →
Offer / Rejected, and open **Gap tasks** to push a JD Match result's gaps
or an interview report's weakest areas into checklist tasks.

## Tests

```bash
python manage.py test
```

Covers: the JD Match rubric (including the 74.0 worked example, synonym
resolution, and gap actions), ATS scoring (high/low resumes), criteria
extraction (weights sum to 100, capped at 12), the interview checklist
(including the relevance regression), the demo seed command, the upload
flow (login required, DOCX + PDF extraction, .txt rejection, owner-only
result pages, dashboard listing), the slice 2 JD Match flow
(JD drafting + 30-character minimum, edit-before-score including delete
and blank-row handling, run-match scoring with evidence quotes and gaps,
edited-criteria scoring, no-criteria and foreign-resume rejection,
re-drafting, owner-only JD/result pages, newest-first listing), and the
slice 3 Interview flow (session start with track/difficulty validation,
one-at-a-time answering with saved scores, short-answer rejection,
overall report math including topic scores and weakest areas,
answering a completed session changing nothing, abandoned-session
resume, owner-only pages, newest-first listing, anonymous redirect),
and the slice 4 Applications + gap tasks flow (tracker CRUD with the
four pipeline stages, status counts, recently-updated-first ordering,
manual tasks with toggle and todo/doing/done states, open/done/all
filters, gap pushes from JD Match analyses and interview reports with
duplicate skipping, owner-only pages, dashboard counts), and the
Google OAuth flow (demo login unchanged, login page with/without the
Google button depending on configuration, unconfigured Google URLs
redirecting instead of crashing, configured Google login posting to
Google, and a mocked callback creating a user and logging them in —
the only mocked parts are the two Google network calls), and the
database switch (connection-URL parsing for Supabase's pooler and
direct forms, SSL-on-by-default, rejection of non-Postgres URLs, and
the DATABASE_URL-set → Postgres / unset → SQLite wiring, booted in a
real subprocess — no live Postgres server needed), and the AI provider
paths (both clients failing → None, JSON parsing including fenced
replies, criteria validation and weight normalisation, the 5-question
invariant, answer-score clamping and rubric-weighted overall, the
Gemini endpoint/header/reply shape, the dispatch rule across every
key/pin combination, and the view-level AI-first/bank-and-checklist-
fallback behaviour for questions, answers, and criteria drafting —
all mocked, no real Groq or Gemini calls).

## Google OAuth login (optional — demo login works without it)

The app ships ready for Google sign-in, but Google can't know about an
app that only runs on your PC until you register it. That takes about
5 minutes, once, in Google Cloud Console. Until you do it, everything
works with the demo login and the Google button simply stays hidden.

### Step 1 — Create a project
1. Open [Google Cloud Console](https://console.cloud.google.com/) and
   sign in with the Google account you want to own this app.
2. Top-left project picker → **New Project** → name it e.g.
   `HireSense AI` → **Create**, then make sure it is the selected
   project.

### Step 2 — Configure the OAuth consent screen
1. Left menu → **APIs & Services → OAuth consent screen**.
2. **Get started** → App name `HireSense AI`, User support email = your
   email, Audience **External**.
3. Contact email = your email → **Save**. (No scopes to add, no test
   users needed for your own account; leave the rest as-is.)

### Step 3 — Create the OAuth client ID
1. Left menu → **APIs & Services → Credentials** → **Create Credentials
   → OAuth client ID**.
2. Application type: **Web application**, name e.g. `HireSense local`.
3. Under **Authorized redirect URIs**, click **Add URI** and paste
   exactly (this is the one allauth listens on for local use):

   ```
   http://127.0.0.1:8000/accounts/google/login/callback/
   ```

   ⚠️ Copy it character for character — Google rejects the login if
   even one character differs, and note it is `127.0.0.1`, not
   `localhost` (Google treats those as different addresses).
4. **Create** → a popup shows your **Client ID** and **Client secret**.
   Copy both now (you can re-open them later under Credentials, but the
   secret is only shown in full once).

### Step 4 — Give the keys to the app (never in code, never in git)
1. In the project folder (next to `manage.py`), copy `.env.example` to
   a new file named `.env` and paste your values:

   ```
   GOOGLE_OAUTH_CLIENT_ID=your-client-id-here
   GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
   ```

2. Restart the server (`runserver` again). The login page now shows
   **Sign in with Google**. Click it → "Continue" → pick your Google
   account → you land on the dashboard, signed in as a new Django user.
   Your existing demo account and all its data are untouched.
3. `.env` is gitignored, so the keys never land in the repo. If you ever
   share the project folder, delete `.env` first (or just don't copy it).

### If it doesn't work
- **"redirect_uri_mismatch" from Google**: the URI in Step 3 doesn't
  match exactly — re-check `127.0.0.1` vs `localhost`, `http` vs
  `https`, and the trailing slash.
- **Button still hidden after restart**: the server only reads `.env`
  at startup, and both variables must be non-empty — restart
  `runserver` and check the file is named exactly `.env` (not
  `.env.txt`) in the same folder as `manage.py`.
- **Production later**: a deployed site needs its OWN redirect URI
  added to the same OAuth client (e.g.
  `https://your-domain.com/accounts/google/login/callback/`) — the
  local `127.0.0.1` URI keeps working alongside it.

## Supabase Postgres (optional — SQLite works without it)

By default the app uses SQLite: one file, zero setup, and that is what
the tests use. When you want a real database that survives outside your
machine (and that a deployed site can share), point the app at
Postgres with one environment variable. No code changes, no new
migrations to write — the same models and migrations run on both.

### ⚠️ Create a FRESH Supabase project — never reuse the live app's

The original Next.js HireSense AI already has its own Supabase project
("hiresense-ai") with its own tables and live data. **Do not point this
Django app at that project.** If both apps shared one database, their
tables would collide and one app could wipe the other's data. Create a
separate, empty project for the Django app (Supabase's free tier is
enough) and use only its connection string.

### Step 1 — Create the project

1. Go to [supabase.com](https://supabase.com) → **Start your project**
   (sign in with GitHub or Google) → **New project**.
2. Pick a name (e.g. `hiresense-django`), a database password (save it
   somewhere safe — you need it in the next step), and the closest
   region. Wait for the project to finish provisioning.

### Step 2 — Copy the connection string

1. In the Supabase dashboard, open **Project Settings** (gear icon) →
   **Database**.
2. Under **Connection string**, pick **URI**. You will see two tabs:
   - **Transaction pooler (recommended)** — host ends in
     `.pooler.supabase.com`, port **6543**. Paste this one: it reuses
     connections, which is what a web app wants, and it is the form
     that survives serverless/hosted deployments.
   - **Direct connection** — host looks like `db.<ref>.supabase.co`,
     port **5432**. Also works, but one connection per app process;
     fine for local development.
3. The string looks like this (yours will differ — never share the
   real one):

   ```
   postgresql://postgres.<ref>:<your-password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```

   If your password contains characters like `@`, `%`, or `#`, the
   dashboard's string already URL-escapes them (e.g. `p@ss` becomes
   `p%40ss`) — copy it exactly as shown, don't "fix" it by hand.

### Step 3 — Give it to the app and migrate

1. In the project folder (next to `manage.py`), copy `.env.example`
   to `.env` if you haven't already, and add the line:

   ```
   DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   ```

2. Restart the server, then run the same two commands as the SQLite
   setup — they now target Postgres:

   ```bash
   python manage.py migrate
   python manage.py seed_demo
   python manage.py runserver
   ```

3. Sign in with `demo` / `demo1234` and use the app normally.

### What changes, and what doesn't

- **SSL is always on for remote Postgres.** Supabase refuses plaintext
  connections, so the app sends `sslmode=require` unless your URL
  already carries its own `sslmode` — a URL without one still gets
  `require`, never a silent plaintext fallback.
- **SQLite data does NOT carry over.** Postgres starts empty: you
  re-seed the demo user and re-upload resumes. The old `db.sqlite3`
  file stays on disk, untouched, so nothing is lost.
- **Switching back is one edit:** delete the `DATABASE_URL` line from
  `.env` and restart — the app is back on SQLite with its old data.
- **Uploads still live on local disk** (`media/`). The database swap
  does not move file storage — Supabase Storage for uploads is a
  separate follow-up, listed below.

### If it doesn't work

- **Connection refused / timeout on port 6543**: you pasted the direct
  string but your network blocks it, or vice versa — try the other
  tab's string (pooler first).
- **Password authentication failed**: the password in the URL doesn't
  match the one set at project creation — reset it under Database
  settings → **Reset database password**, then paste the new string.
- **SSL / sslmode errors**: add `?sslmode=require` to the end of the
  URL (with `&` instead of `?` if the URL already has a `?` part).
- **App still shows SQLite data after setting the variable**: the
  server only reads `.env` at startup — restart `runserver`, and check
  the file is named exactly `.env` in the same folder as `manage.py`.

## AI providers (optional — everything works without them)

The original app's AI features, ported to Django with two providers —
Groq (`resumes/groq.py`) and Gemini (`resumes/gemini.py`), both stdlib
only, no new dependencies. The views call `resumes/ai_provider.py`,
which picks the provider; both answer the same three features, so the
pages cannot tell them apart. Set a key (or both) in `.env`, next to
`manage.py`, then restart the server:

```bash
GROQ_API_KEY=gsk_your_key_here
# GROQ_MODEL is optional; it defaults to llama-3.3-70b-versatile
GEMINI_API_KEY=AIza_your_key_here
# GEMINI_MODEL is optional; it defaults to gemini-2.0-flash
# AI_PROVIDER is optional: "groq" or "gemini" to pin one provider.
# Unset (the default) means Groq first if its key is set, else Gemini.
```

Get a Groq key at console.groq.com (free tier works) and a Gemini key
at aistudio.google.com. A pinned provider with a missing key means no
AI at all — no silent switch to the other provider. What changes, and
what does not:

- **JD Match**: criteria are drafted by AI from the role title,
  company, and JD text instead of the keyword heuristic. You still edit
  them before scoring — a draft is a draft.
- **Mock Interview**: start a session with a company + JD text and the
  5 questions are generated for that JD, company, track, and
  difficulty. Answers get AI feedback on the same rubric. Sessions
  record `question_source` ("ai" or "bank") and each answer records its
  feedback source, so the report says which author wrote what.
- **Any AI failure falls back silently**: bad key, no network, rate
  limit, malformed reply — the page just uses the heuristic, the bank,
  or the checklist instead. AI never crashes a page.
- **Scores never change meaning**: match scores and ATS scores stay
  deterministic. AI drafts criteria, generates questions, and writes
  feedback — it never computes a score. That is the app's core promise,
  and the key does not move it.

No keys (the default): the app behaves exactly as it did before this
section existed. Keys live only in `.env`, which is gitignored —
never commit them, never paste them into a chat or a screenshot.

## What's next (later slices)

1. **Storage + polish** — Supabase Storage for uploads (so resumes
   survive outside local disk), then real CSS/static files, dark/light
   theme, per-page loading states, matching the original app's look
   and feel. (Google OAuth, the Supabase Postgres swap, and AI
   providers are done.)
2. **Polish** — real CSS/static files, dark/light theme, per-page loading
   states, matching the original app's look and feel.

## Honest differences from the original (slices 1–4 + Google OAuth + Supabase Postgres + Groq + Gemini AI)

- AI parity, except rewrites/cover letters: AI (Groq or Gemini) drafts
  criteria, generates interview questions, and scores answers with
  feedback when a key is set — same as the original. No AI rewrites, cover letters,
  or tailored resumes yet — those are AI extras, not the deterministic
  core. (The Django interview questions use JD + company + track +
  difficulty; the original also grounds them in the resume, which
  Django sessions do not link yet.)
- Google OAuth works, but YOU still have to create the Google OAuth
  client (steps above) — the original Next.js app never had one either,
  so there were no keys to copy.
- SQLite by default, Supabase Postgres when `DATABASE_URL` is set (your
  own fresh project — never the live Next.js app's); uploads still
  stored locally under `media/` (Supabase Storage is the remaining
  follow-up).
- Styling is a small inline stylesheet, not Tailwind — the focus so far
  is Django concepts and correct scoring, not pixels.

## Deploying to Render (live link)

The repo ships a Render Blueprint (`render.yaml`): one web service
(Django + the built React app, served by WhiteNoise) and one free
Postgres database.

1. Create a free account at render.com and connect your GitHub.
2. Dashboard → New → Blueprint → select `pawanriko/hiresense-ai`.
   Render reads `render.yaml` and creates both resources.
3. Wait for the first build + deploy, then open the service's
   `.onrender.com` URL.
4. The build runs `python manage.py seed_demo` automatically (after
   migrate), so the demo/demo1234 login exists on the live database.
   (Render's Shell tab needs a paid plan, so on the free tier the build
   is the way to seed. Or sign in with Google, once you've created an
   OAuth client with the live callback URL.)
5. Optional env vars in the dashboard: `GROQ_API_KEY`, `GEMINI_API_KEY`
   (AI features; everything works without them).

How production works, briefly: `DEBUG` is False and `SECRET_KEY` is
generated by Render (see `config/settings.py`); the build compiles the
React app and `collectstatic` gathers it under `/static/`; gunicorn
serves Django; the same origin serves both the app and `/api`, so
session + CSRF cookies work with no CORS setup. The React routes
(`/resumes`, `/jd-match`, ...) are served by Django (see `SPA_ROUTES`
in `config/urls.py`); the older HTML pages still live at their
trailing-slash URLs (`/resumes/`).

Free-tier honesty: the service sleeps when idle, so the first visit
after a while takes a moment to wake; uploaded resumes live on the
service's local disk, so they do not survive redeploys — Supabase
Storage (see "What's next") is the real fix for that.
