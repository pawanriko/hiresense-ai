# HireSense AI — Candidate Edition

**Live:** https://hiresense-ai-nine.vercel.app
**Demo login:** sign in with `demo@hiresense.ai` via “Try the demo account” on the login page.

Paste a job description and get your resume scored criterion by criterion — every point backed by a
quote from your own resume, every miss turned into a fixable gap. Then fix the gaps and practise the
interview on the same material.

## What it does

- **Resume Lab** — Upload a PDF/DOCX resume (max 10 MB). Stored privately in Supabase Storage, parsed
  (unpdf / mammoth), split into sections by heading heuristics, and scored by a rule-based **ATS health
  engine** (sections, quantification, action verbs, contact & links, length & format). Every deduction
  names the failed check.
- **JD Match** — Paste a JD. Criteria are drafted (AI via Groq when a key is configured, otherwise a
  keyword scan) and are **always editable by the candidate before scoring**. The deterministic scoring
  engine then scores each criterion with verbatim evidence:
  - **100** — evidence in an Experience/Projects bullet with an action verb and/or quantified result
  - **70** — evidence in Experience/Projects, or described with context in Summary
  - **40** — mentioned only in the Skills list (claimed, not demonstrated)
  - **0** — not found → a gap with a suggested fix action
  - Match score = Σ(weight × criterion score) / Σweights. The AI never computes a score.
- **Fix the gaps** — Bullet rewrites (accept/edit), a cover letter, and a tailored resume draft
  (downloadable), all built only from the resume's own evidence. Gaps push to the Prep Dashboard as
  checklist tasks with one click.
- **AI Mock Interview** — HR, Technical, DSA, and Frontend tracks; 5 questions one at a time; answers
  scored on a fixed rubric (relevance 30%, depth 25%, structure 20%, confidence 15%, conciseness 10%)
  with a final report (per-topic scores, weakest areas, weakest answer) and revision tasks.
- **Prep Dashboard** — Latest match score, score trend, gap checklist, and an application tracker
  (Applied → Interview → Offer → Rejected).

## Worked example (from the design docs)

Frontend Intern JD: React 70×35% + JavaScript 70×25% + TypeScript 0×20% + Git 100×20% = **62.0/100**.
Top gap: TypeScript — build a small project with it, then add an evidence bullet.

## Stack (all free tiers)

Next.js (App Router) + TypeScript + Tailwind · Auth.js v5 (Google + demo credentials) · Supabase
(Postgres + private Storage) · Groq API for AI features · Vercel hosting.

## AI honesty

AI features (criteria drafting, rewrites, cover letters, interview questions/feedback) run on Groq
**only when `GROQ_API_KEY` is set** (add it in Vercel → Settings → Environment Variables, then
redeploy). Without a key, the app runs honest deterministic fallbacks — heuristic criteria, template
drafts, checklist interview scoring — and labels them as such in the UI. Scoring itself never uses AI.

## Docs

Full documentation lives in [`docs/`](docs/README.md): product overview, architecture, system design
(incl. the scoring engine and ATS rules), workflows, tech stack, security & privacy, roadmap, and
decision records. LLM prompts are versioned in [`prompts/`](prompts/).

## Develop

```bash
npm install
cp .env.example .env.local   # fill in Supabase + Auth.js values
npm run dev                  # http://localhost:3000
npm test                     # scoring engine unit tests (Vitest)
npm run build
```

Database: run `db/schema.sql` in the Supabase SQL editor, then
`db/migrations/001_ai_assistance.sql`. Create a **private** Storage bucket named `resumes`.

## Author

**Pawan Kumar** — BCA student, New Delhi · [@pawanriko](https://github.com/pawanriko)
