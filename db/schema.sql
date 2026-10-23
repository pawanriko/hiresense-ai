-- HireSense AI — Supabase schema (Build 1 subset of docs/03-system-design.md)
-- Run in the Supabase SQL editor. Every table is scoped by user_id (text: Auth.js user id).

create table if not exists public.resumes (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  version int not null default 1,
  file_name text not null,
  file_path text not null,
  file_type text not null check (file_type in ('pdf','docx')),
  parsed_text text,
  sections jsonb not null default '{}'::jsonb,
  parse_status text not null default 'pending' check (parse_status in ('pending','parsed','failed')),
  parse_error text,
  ats_score numeric,
  created_at timestamptz not null default now()
);
create index if not exists resumes_user_idx on public.resumes (user_id, created_at desc);

create table if not exists public.job_descriptions (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  title text not null,
  company text,
  raw_text text not null,
  criteria jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.match_analyses (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  resume_id uuid not null references public.resumes(id) on delete cascade,
  jd_id uuid not null references public.job_descriptions(id) on delete cascade,
  match_score numeric,
  criteria_results jsonb not null default '[]'::jsonb,
  gaps jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.mock_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  resume_id uuid references public.resumes(id) on delete set null,
  jd_id uuid references public.job_descriptions(id) on delete set null,
  track text not null,
  difficulty text not null default 'medium',
  status text not null default 'in_progress',
  overall_score numeric,
  transcript jsonb not null default '[]'::jsonb,
  report jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.prep_tasks (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  analysis_id uuid references public.match_analyses(id) on delete cascade,
  title text not null,
  source_gap text,
  status text not null default 'todo' check (status in ('todo','doing','done')),
  created_at timestamptz not null default now()
);

create table if not exists public.applications (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  company text not null,
  role text not null,
  jd_id uuid references public.job_descriptions(id) on delete set null,
  status text not null default 'Applied' check (status in ('Applied','Interview','Offer','Rejected')),
  notes text,
  updated_at timestamptz not null default now()
);

create table if not exists public.audit_events (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  action text not null,
  entity text not null,
  entity_id text,
  created_at timestamptz not null default now()
);

-- Row Level Security is enabled as a second line of defence.
-- The app accesses data through the service role (server-side only) and
-- always filters by user_id in the data-access layer, so no permissive
-- public policies are defined here on purpose.
alter table public.resumes enable row level security;
alter table public.job_descriptions enable row level security;
alter table public.match_analyses enable row level security;
alter table public.mock_sessions enable row level security;
alter table public.prep_tasks enable row level security;
alter table public.applications enable row level security;
alter table public.audit_events enable row level security;

-- Storage: create a PRIVATE bucket named "resumes" in the Supabase dashboard
-- (Storage → New bucket → name: resumes, Public: off). Files are served only
-- via server-generated signed URLs.
