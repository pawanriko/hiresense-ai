# 03 · System Design — HireSense AI

## 1. Data model

All tables carry `user_id`; every query is scoped to the authenticated user. No cross-user reads exist anywhere in the system.

| Table | Key fields | Purpose |
|---|---|---|
| `users` | id, email, name, image, created_at | Account (created by Auth.js Google OAuth) |
| `resumes` | id, user_id, version, file_url, file_type (pdf/docx), parsed_text, sections (JSON), ats_score, created_at | Each upload is a new version; nothing is overwritten |
| `job_descriptions` | id, user_id, title, company, raw_text, criteria (JSON), created_at | Pasted JD + its extracted, user-edited criteria |
| `match_analyses` | id, user_id, resume_id, jd_id, match_score, criteria_results (JSON: per-criterion weight, score, evidence quote, status), gaps (JSON), created_at | One scoring run; re-running creates a new record |
| `resume_rewrites` | id, analysis_id, original_bullet, rewritten_bullet, accepted (bool) | AI rewrite suggestions and what the candidate kept |
| `mock_sessions` | id, user_id, resume_id, jd_id, track (HR/Technical/DSA/Frontend), difficulty, status, overall_score, transcript (JSON), report (JSON), created_at | One mock interview |
| `prep_tasks` | id, user_id, analysis_id, title, source_gap, status (todo/doing/done), created_at | Checklist items generated from gaps |
| `applications` | id, user_id, company, role, jd_id, status (Applied/Interview/Offer/Rejected), notes, updated_at | Application tracker |
| `audit_events` | id, user_id, action, entity, entity_id, created_at | Scoring runs, exports, deletions — user-visible history |

**Criteria JSON (stored on `job_descriptions`):**
```json
[
  {"name": "React", "category": "skill", "weight": 35, "required": true},
  {"name": "TypeScript", "category": "skill", "weight": 20, "required": false}
]
```

## 2. API design (Next.js route handlers, JSON REST)

| Method & route | Auth | Purpose |
|---|---|---|
| `POST /api/resumes` | User | Upload PDF/DOCX (multipart), store privately, parse, run ATS checks |
| `GET /api/resumes` | User | List my resume versions |
| `GET /api/resumes/:id` | User (owner) | Resume detail incl. ATS breakdown |
| `POST /api/jds` | User | Save a JD (title, company, text) |
| `POST /api/jds/:id/extract-criteria` | User (owner) | One LLM call → structured criteria + suggested weights (draft, editable) |
| `PUT /api/jds/:id/criteria` | User (owner) | Save the candidate's edited criteria/weights |
| `POST /api/matches` | User | Run the scoring engine (resume_id + jd_id) → match analysis |
| `GET /api/matches/:id` | User (owner) | Full analysis: scores, evidence, gaps |
| `POST /api/matches/:id/rewrites` | User | AI bullet rewrites for weak/missing criteria |
| `POST /api/matches/:id/cover-letter` | User | Generate a cover letter from resume + JD |
| `POST /api/interviews` | User | Start a mock session (track, difficulty, resume + JD context) |
| `POST /api/interviews/:id/answer` | User (owner) | Submit an answer → rubric feedback + next question |
| `GET /api/interviews/:id/report` | User (owner) | Final report |
| `GET /api/dashboard` | User | Checklist, recent scores, application summary |
| `POST /api/applications` / `PATCH /api/applications/:id` | User | Tracker create/update |

Conventions: errors are `{ error: { code, message } }`; lists are paginated; all IDs are UUIDs; no endpoint ever returns another user's data (ownership check on every `:id` route).

## 3. The scoring engine (core design)

### 3.1 Formula
```
Match Score = Σ (Criterion Weightᵢ × Criterion Scoreᵢ) / Σ Weightᵢ
```
Deterministic: identical inputs always give identical outputs. Unit-tested.

### 3.2 Criteria extraction (AI, once per JD)
The LLM receives the JD text and returns structured JSON criteria (name, category, required?, suggested weight). Weighting guidance given to the model: required skills > preferred skills > education/soft requirements. **The candidate reviews and edits criteria and weights before scoring** — the extraction is a draft, not a verdict. Extraction results are cached on the JD record.

### 3.3 Evidence search (deterministic)
For each criterion, the engine searches the parsed resume:
- **Normalization:** lowercase, punctuation-stripped text; a synonym map (e.g. `js → javascript`, `reactjs → react`, `postgres → postgresql`).
- **Section awareness:** every hit is tagged with the section it was found in (Skills, Experience, Projects, Education, Summary).
- **Context capture:** the sentence/bullet containing the hit is stored as the evidence quote.
- **Context strength signals:** presence of action verbs and quantified results (numbers, %, ₹/$) in the evidence bullet.

### 3.4 Rubric (per criterion, 0–100)
| Score | Rule |
|---|---|
| **100** | Evidence in Experience/Projects bullet **with** action verb and/or quantified result |
| **70** | Evidence in Experience/Projects, or described with context in Summary |
| **40** | Mentioned only in the Skills list — claimed, not demonstrated |
| **0** | Not found anywhere → status `missing`, generates a gap |

Status per criterion: `strong` (100) · `present` (70) · `weak` (40) · `missing` (0), always shown with its evidence quote or "No evidence found".

### 3.5 Gap generation
Each `missing` or `weak` criterion creates a gap entry: `{ criterion, current_status, suggested_action }`. Suggested actions are templated by category (e.g. skill missing → "build or convert a small project using X, then add an evidence bullet"; skill weak → "add a project bullet showing X in use"). Gap entries can be pushed to the Prep Dashboard as `prep_tasks` with one click.

### 3.6 Sample run (illustrative)
Frontend Developer Intern JD vs a sample resume: React 35% → 70 (24.5), JavaScript 25% → 70 (17.5), TypeScript 20% → 0 (0), Git/GitHub 20% → 100 (20.0) → **Match Score 62.0/100**. Top gap: TypeScript.

## 4. ATS health score (Resume Lab)
Rule-based, independent of any JD. Categories (each with visible pass/fail checks):
- **Sections:** contact info, summary, skills, experience/projects, education present
- **Quantification:** % of bullets containing numbers/results
- **Action verbs:** bullet openings checked against an action-verb list
- **Length & format:** 1–2 pages equivalent, parseable text (no image-only content), consistent dates
- **Contact & links:** email present, portfolio/GitHub/LinkedIn links present
Overall = weighted average of category scores; every deduction names the failed check.

## 5. Mock interview engine
- **Question generation (AI):** prompt built from the resume sections + JD criteria + track + difficulty; questions asked **one at a time**; no repeat of covered criteria until others are covered.
- **Answer scoring (AI with fixed rubric):** relevance 30%, depth 25%, structure (STAR where applicable) 20%, confidence cues 15%, conciseness 10%. The rubric is a versioned prompt in `/prompts`, shown in the report.
- **Report:** per-topic scores, two weakest areas, model-answer outline for the weakest question, and revision tasks pushed to the dashboard.
- Session state (questions asked, transcript) is stored server-side in `mock_sessions.transcript`.

## 6. Parsing pipeline
Upload → validation (size ≤ 10 MB, MIME check, extension check) → private storage → text extraction (PDF: `unpdf`/`pdfjs`; DOCX: `mammoth`) → section segmentation (heading-based heuristics) → normalized text + sections JSON stored on the resume row. Corrupt/unreadable files fail visibly with a specific error; nothing is silently accepted. Parse failures never create a scored resume.

## 7. Prompt management
All LLM prompts live in `/prompts` as versioned files (`criteria-extraction.v1.md`, `bullet-rewrite.v1.md`, `interview-questions.v1.md`, `answer-scoring.v1.md`). Prompt changes are commits — the README can point to them as evidence of deliberate AI engineering.

## 8. Non-functional requirements
- **Reproducibility:** scoring path contains no LLM calls.
- **Latency:** scoring run < 2s for a typical resume; AI calls are the only slow paths and show progress states.
- **Cost:** $0 infra on free tiers; Groq usage is metered per user action, criteria extractions are cached.
- **Deletion:** deleting a resume deletes its file, analyses, and rewrites (cascade), recorded in `audit_events`.
