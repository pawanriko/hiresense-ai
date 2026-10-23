# 07 · Roadmap & Testing — HireSense AI

## Build phases
Numbering note: these are **build steps** (Build 1–4). They are not "product phases" — the scope table in `01-product-overview.md` uses MVP vs post-MVP language instead, so the two never collide (a mistake in the earlier recruiter-side deck that this doc set fixes).

### Build 1 — Foundation
**Deliverables:** GitHub repo + branch convention, Next.js + Tailwind + TypeScript scaffold, Auth.js (Google + demo login), Supabase project + schema + RLS, resume upload → private storage → parsing → resume versions list.
**Exit condition:** a signed-in user can upload a PDF and see its parsed sections; healthcheck and env setup documented.

### Build 2 — Scoring engines
**Deliverables:** ATS rule engine + health score UI; JD save + criteria extraction (one AI call, editable criteria screen); deterministic evidence search + rubric scoring; match analysis page (scores, evidence quotes, gaps); gap → prep task push.
**Exit condition:** the sample resume + sample JD produce the documented 62/100-style analysis end-to-end, and the scoring unit tests pass.

### Build 3 — AI assistance
**Deliverables:** bullet rewrites (accept/edit flow), tailored resume version + export, cover letter generation; mock interview engine (question flow, per-answer rubric feedback, final report); revision tasks from interview weak areas.
**Exit condition:** full loop demoable: upload → match → fix → mock interview → report.

### Build 4 — Polish & launch
**Deliverables:** dashboard trends + application tracker completion, demo data seeding + nightly reset, GitHub Actions CI (lint + tests), production deploy on Vercel, README with screenshots + architecture diagram + scoring explanation, 1-minute demo video.
**Exit condition:** live public URL; a stranger can complete the demo loop in under 3 minutes.

## Testing strategy
| Layer | What | Tooling |
|---|---|---|
| Unit | Scoring formula, rubric thresholds, synonym/section evidence search, ATS checks, gap generation | Vitest — these are pure functions and carry the product's credibility, so they get the deepest coverage |
| Integration | API routes: auth required, ownership scoping, upload validation, cascade deletes | Vitest + test Supabase project |
| E2E | One golden path: sign in (demo) → sample resume → sample JD → analysis → mock interview start | Playwright (post-Build 3) |
| Manual | Prompt quality checks for criteria extraction / rewrites / interview feedback against 3 fixed sample resume+JD pairs | Checklist in repo; run before each release |

**Golden rule:** the scoring engine's tests are written before its UI. If a score can't be explained by a test, it doesn't ship.

## Demo data plan
- One sample resume (the builder's own, sanitized) + two sample JDs (Frontend Intern, Python Developer Intern).
- One pre-computed analysis and one completed mock session on the demo account.
- Demo resets nightly to the seeded state.

## Top-5 portfolio checklist
- [ ] Live link + demo login on the README's first screen
- [ ] Before/after match example visible on the landing page
- [ ] Docs set (this folder) linked from the README
- [ ] Scoring rubric explained in the README with the worked example
- [ ] Clean commit history; one branch per build phase
- [ ] 1-minute demo video
