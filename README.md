# HireSense AI — Candidate Edition

**Paste a job description, get your resume scored criterion-by-criterion with evidence from your own resume, see exactly what's missing, fix it, and practise the interview — before you apply.**

An AI interview-preparation platform built **for candidates**: explainable JD matching (deterministic scoring, evidence quotes, no black-box fit scores), an ATS health check, AI bullet rewrites, mock interviews, and a prep dashboard.

## Status
Documentation locked (23 Oct 2026) · Build 1 — Foundation in progress.
Full documentation lives in [`/docs`](docs/README.md) — start with the index.

## Modules (MVP)
1. **Resume Lab** — upload PDF/DOCX, ATS health score with category breakdown
2. **JD Match** — weighted match score vs a job description, per-criterion evidence, gap list
3. **AI Mock Interview** — questions grounded in your resume + JD, rubric feedback, final report
4. **Prep Dashboard** — checklist from your gaps, score trends, application tracker

## Tech stack
Next.js + TypeScript + Tailwind CSS · Groq API · Auth.js (Google) · Supabase (Postgres + Storage) · Vercel

## Scoring, in one line
`Match Score = Σ (weight × criterion score) / Σ weights` — criterion scores are 100 / 70 / 40 / 0 by a published rubric, always backed by a quote from the resume. The AI never computes the score. Full design: [`docs/03-system-design.md`](docs/03-system-design.md)

## Local setup (once Build 1 code lands)
```bash
npm install
cp .env.example .env.local   # fill in keys
npm run dev
```

## Author
**Pawan Kumar** — BCA student, New Delhi · [@pawanriko](https://github.com/pawanriko)
