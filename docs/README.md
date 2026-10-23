# HireSense AI — Documentation

**Candidate-side AI interview-preparation platform.** Score your resume against any job description with evidence-backed, explainable matching; fix the gaps; practise the interview; walk in prepared.

> Status: documentation locked 23 Oct 2026 · build not yet started (see `07-roadmap-and-testing.md`)

## Read in this order
| # | Document | What it covers |
|---|---|---|
| 01 | [Product Overview](01-product-overview.md) | Vision, philosophy, users, modules, scope, success criteria |
| 02 | [Architecture](02-architecture.md) | Modular monolith, system/component diagrams, deployment, security boundary |
| 03 | [System Design](03-system-design.md) | Data model, API surface, the scoring engine (formula, rubric, evidence search), ATS checks, interview engine, parsing |
| 04 | [Workflows](04-workflows.md) | Onboarding, Resume Lab, JD Match loop, mock interview, dashboard, demo & error flows |
| 05 | [Tech Stack](05-tech-stack.md) | Chosen stack with justifications, rejected alternatives, env vars, cost posture |
| 06 | [Security & Privacy](06-security-and-privacy.md) | Auth, data isolation, file handling, secrets, privacy commitments, honest limitations |
| 07 | [Roadmap & Testing](07-roadmap-and-testing.md) | Build 1–4 with exit conditions, testing strategy, demo data plan, Top-5 checklist |
| 08 | [Decision Log](08-decisions.md) | ADRs: candidate-side scope, explainable flipped scoring, deterministic engine, monolith, Groq, Supabase, docs-first |

## The one-paragraph version
HireSense AI is a Next.js + Groq + Supabase web app for candidates. Its core is a **deterministic** matching engine: an LLM extracts editable criteria from a pasted job description, a rule-based engine searches the candidate's parsed resume for evidence of each criterion, and a published rubric (100/70/40/0) produces a weighted match score — every point traceable to a quote from the resume, every miss converted into a prep task. Around that core sit a Resume Lab (ATS health), an AI mock interviewer, and a prep dashboard.

## Provenance
This doc set supersedes the recruiter-side "HireSense AI" presentation deck reviewed on 23 Oct 2026. The deck's explainable-scoring idea was kept and flipped for candidates; its contradictions (monolith vs microservices/Kafka, 6-vs-7 phases, undefined extraction step) are corrected here and recorded in `08-decisions.md`.
