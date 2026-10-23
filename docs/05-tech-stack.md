# 05 · Tech Stack — HireSense AI

## Chosen stack

| Layer | Choice | Why this one |
|---|---|---|
| Framework | **Next.js (App Router) + React + TypeScript** | UI + API in one repo and one deploy; TypeScript keeps the scoring engine's data contracts honest |
| Styling | **Tailwind CSS** | Fast, consistent UI; the builder already uses it |
| AI | **Groq API** (chat models; prompts versioned in `/prompts`) | Already used in the KAI project; very fast responses make mock interviews feel live; free tier (checked 23 Oct 2026: ~30 req/min, 1,000 req/day, no card) is enough for demo scale. Fallback: any OpenAI-compatible endpoint |
| Auth | **Auth.js (NextAuth v5)** with Google OAuth + demo credentials login | Real login in an afternoon; demo login powers the portfolio demo |
| Database | **Supabase Postgres** | Free tier, relational integrity for resumes/JDs/analyses, SQL the builder is learning anyway |
| File storage | **Supabase Storage** (private bucket, signed URLs) | Same platform as the DB; no separate AWS account/billing |
| Parsing | **`unpdf`/`pdfjs-dist`** (PDF), **`mammoth`** (DOCX) | Local, free, deterministic — no external parsing API |
| Hosting | **Vercel** (free) | Native Next.js hosting, preview deploys per branch |
| Testing | **Vitest** (unit: scoring engine, ATS rules), **Playwright** (one E2E happy path, later) | The scoring engine is pure functions — cheap to test thoroughly |
| CI | **GitHub Actions** | Lint + unit tests on every push (added in Build 4) |

## Alternatives considered — and why not (from the HireSense recruiter-side deck review, 23 Oct 2026)

| Alternative | Verdict | Reason |
|---|---|---|
| FastAPI backend + separate React frontend | Rejected for MVP | Two repos, two deploys, CORS/auth glue — slower for a solo builder; Next.js API routes cover the same ground |
| Microservices + Kafka | Rejected | No scale problem exists that these solve; the deck itself argued for a modular monolith elsewhere — contradiction removed |
| AWS S3 for resume files | Rejected | Supabase Storage does the same job on the same free platform |
| Local embedding models / vector search | Deferred | Scoring must be explainable and reproducible; embeddings are neither. Possible post-MVP experiment, never inside the score |
| MongoDB | Rejected | Data is relational (users → resumes → analyses); Postgres + SQL is also better interview material for this builder |
| OpenAI API as primary | Rejected | Paid; Groq free tier + prior KAI experience wins |

## Environment variables (server-side only)
```
NEXTAUTH_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NEXT_PUBLIC_SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=     # server only, never shipped to browser
GROQ_API_KEY=                  # server only
DEMO_USER_EMAIL= / DEMO_USER_PASSWORD=
```

## Cost & limits posture
Total running cost target: **₹0** on free tiers. Known ceilings: Groq free-tier daily requests (mitigated by caching criteria extraction per JD), Supabase free storage/DB size (fine for demo), Vercel function timeouts (parsing kept synchronous but small — files capped at 10 MB).

## Versioning note
AI model names on Groq change quarterly. The README must pin the model roster **with the date checked**, and all prompts carry version numbers, so results stay explainable over time.
