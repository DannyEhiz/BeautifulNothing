-- Run in Supabase → SQL editor.

-- Page views and button clicks from the landing page (feeds the author dashboard).
create table if not exists public.events (
  id          bigint generated always as identity primary key,
  type        text not null check (type in ('visit', 'selah_click', 'order_click')),
  visitor_id  text,
  path        text,
  referrer    text,
  user_agent  text,
  created_at  timestamptz not null default now()
);

create index if not exists events_type_created_idx on public.events (type, created_at desc);

-- Only the backend (service-role key) touches this table; RLS with no policies blocks public access.
alter table public.events enable row level security;
