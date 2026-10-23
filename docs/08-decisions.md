# 08 · Decision Log — HireSense AI

Architecture Decision Records (ADR). Each entry: what was decided, why, and what it cost us. Newest last. This log doubles as interview preparation — every entry is a defensible talking point.

## ADR-001 · Candidate-side product, not recruiter-side (23 Oct 2026)
**Decision:** HireSense AI serves candidates (interview preparation + resume optimization). The recruiter-side design from the uploaded HireSense deck is superseded.
**Why:** The builder's stated goal is preparing for *his own* interviews and making *his own* resume the best it can be. He's also his own first user and demo subject — a candidate tool demos in 30 seconds with his real resume; a recruiter tool needs invented companies and data.
**Cost:** The deck's multi-tenancy/recruiter material was discarded. Its best idea (explainable scoring) was kept — see ADR-002.

## ADR-002 · Explainable weighted scoring, flipped for candidates (23 Oct 2026)
**Decision:** JD Match score = Σ(weight × criterion score)/Σweights, with per-criterion evidence quotes from the candidate's own resume; missing criteria become actionable gaps.
**Why:** Black-box "fit scores" are the industry norm and the exact thing candidates can't act on. Evidence + a published rubric makes every point explainable and every gap fixable.
**Cost:** More engineering than "ask the LLM for a score" — accepted deliberately; it's the product's differentiator.

## ADR-003 · Deterministic scoring; AI never computes the score (23 Oct 2026)
**Decision:** The scoring path (evidence search + rubric 100/70/40/0) contains zero LLM calls. LLMs are used only for criteria extraction (draft, user-editable), rewrites, interview questions, and answer feedback.
**Why:** Reproducibility (same inputs → same score), testability, zero cost on the main path, and honest interview answers about how the score is produced.
**Cost:** The rubric is coarser than a model's judgement — mitigated by showing evidence so the candidate can judge.

## ADR-004 · Modular monolith in Next.js — no microservices, no Kafka (23 Oct 2026)
**Decision:** One Next.js app (UI + API routes) with isolated domain modules.
**Why:** Solo builder, free-tier deploy, no scale problem to solve. (The old deck contradicted itself — monolith in one table, "microservices & Kafka" in another; this ADR ends that.)
**Cost:** Scaling a single module independently isn't possible without extraction — accepted; module boundaries keep extraction possible later.

## ADR-005 · Groq as the AI provider (23 Oct 2026)
**Decision:** Groq API for all LLM calls; prompts versioned in `/prompts`.
**Why:** Builder already shipped KAI on Groq; speed makes mock interviews feel live; free tier (~30 req/min, 1,000 req/day, checked 23 Oct 2026) fits demo scale.
**Cost:** Free-tier ceilings — mitigated by caching JD criteria extractions and keeping the scoring path AI-free (ADR-003).

## ADR-006 · Supabase (Postgres + Storage) over MongoDB / S3 (23 Oct 2026)
**Decision:** Supabase for both database and private file storage.
**Why:** Data is relational (users → resumes → analyses); one free platform for DB + files + signed URLs; SQL is a skill the builder is actively learning and can discuss in interviews.
**Cost:** Vendor coupling to Supabase — acceptable at this scale; schema is plain Postgres and portable.

## ADR-007 · Documentation before code (23 Oct 2026)
**Decision:** The full documentation set (this folder) is written and locked before Build 1 starts.
**Why:** The design mistakes found in the recruiter deck (contradictory architecture, undefined extraction step, phase-numbering collision) are cheapest to fix on paper. Docs also become the interview-prep material for this project.
**Cost:** A slower start — accepted.
