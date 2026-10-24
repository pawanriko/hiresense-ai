-- HireSense AI — migration 001 (Build 3 tables).
-- Run in the Supabase SQL editor. Safe to run twice (IF NOT EXISTS).
-- Adds: resume_rewrites (AI/template bullet rewrites + accept state) and
-- generated_docs (cover letters, tailored resumes) linked to match_analyses.

create table if not exists public.resume_rewrites (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references public.match_analyses(id) on delete cascade,
  original_bullet text not null,
  rewritten_bullet text not null,
  accepted boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.generated_docs (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references public.match_analyses(id) on delete cascade,
  kind text not null check (kind in ('cover_letter', 'tailored_resume')),
  content text not null,
  created_at timestamptz not null default now()
);

alter table public.resume_rewrites enable row level security;
alter table public.generated_docs enable row level security;
