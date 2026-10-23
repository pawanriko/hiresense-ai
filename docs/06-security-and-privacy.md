# 06 · Security & Privacy — HireSense AI

Resumes are personal documents. This product treats them that way by design, not as an afterthought.

## Authentication & sessions
- Google OAuth via Auth.js; sessions are signed JWTs with a short lifetime and secure, httpOnly cookies.
- A separate **demo account** exists for portfolio visitors; it owns only its seeded demo data.
- Every API route handler checks the session first; unauthenticated requests get `401`, non-owner requests get `404` (never confirming another user's data exists).

## Authorization & data isolation
- Single-tenant-per-user model: every table carries `user_id`, and **every** query filters by the session's `user_id` — enforced in the data-access layer, not per-page.
- Supabase Row Level Security is enabled as a second line of defence behind the API checks.
- There are no admin endpoints in the MVP and no cross-user features (no sharing, no public profiles).

## File handling
- Uploads: max **10 MB**, extension **and** MIME verified (PDF/DOCX only), file names never trusted (stored under generated UUID names).
- Files live in a **private** Supabase Storage bucket. Downloads/previews use **signed URLs with short expiry**, generated server-side after an ownership check.
- Parsing runs on extracted text only; uploaded files are never executed or rendered as HTML. Parsed text is sanitized before display (no raw HTML injection from resume content).

## Secrets & API keys
- `GROQ_API_KEY` and `SUPABASE_SERVICE_ROLE_KEY` exist only as server environment variables; nothing secret is ever sent to the browser or committed (`.env*` is git-ignored; a pre-commit check is part of Build 1).
- LLM prompts contain resume/JD text by necessity — only the minimum context is sent per call (e.g. criteria extraction sends the JD only, not the resume).

## Privacy commitments
- A user's resumes, analyses, and interview transcripts are visible **only to that user**.
- **Deletion is real:** deleting a resume cascades to its stored file, parsed text, analyses, and rewrites. Account deletion removes everything.
- No resume data is used to train anything; no data is sold or shared; analytics, if added later, are aggregate usage counts only (no content).
- The AI provider (Groq) receives text only during the candidate's own AI actions (criteria extraction, rewrites, interview), which the UI labels as AI steps.

## Abuse & rate limiting
- Per-user rate limits on upload and AI endpoints (protects the shared Groq free tier).
- AI endpoints validate input sizes (JD text and answers are length-capped) to prevent cost abuse.
- All scoring is local/deterministic — the most-used path costs nothing and cannot be used to burn AI quota.

## Known limitations (stated honestly)
- Free-tier infrastructure: no WAF, no dedicated audit logging beyond `audit_events`.
- OAuth-only login means account recovery is Google's responsibility.
- These are acceptable for a portfolio deployment and are documented here so an interviewer hears them from us first.
