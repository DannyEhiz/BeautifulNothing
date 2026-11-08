-- Beautiful Nothing — run once in Supabase → SQL editor. Safe to re-run.
-- Every object is prefixed bn_ so it can live alongside other apps in the same project.
-- Only the backend (service-role key) touches these tables: RLS is on with no policies,
-- which blocks the public anon key completely.

-- ───────────── Analytics: page views and button clicks ─────────────
create table if not exists public.bn_events (
  id          bigint generated always as identity primary key,
  type        text not null check (type in ('visit', 'ebook_click', 'showlove_click', 'order_click')),
  visitor_id  text,
  path        text,
  referrer    text,
  user_agent  text,
  created_at  timestamptz not null default now()
);
create index if not exists bn_events_type_created_idx on public.bn_events (type, created_at desc);

-- ───────────── Bank accounts shown to paperback buyers ─────────────
create table if not exists public.bn_bank_accounts (
  id              bigint generated always as identity primary key,
  bank_name       text not null,
  account_number  text not null,
  account_name    text not null,
  account_type    text,
  is_active       boolean not null default true,
  sort_order      int not null default 0,
  created_at      timestamptz not null default now(),
  unique (bank_name, account_number)
);

insert into public.bn_bank_accounts (bank_name, account_number, account_name, account_type, sort_order) values
  ('GTBank', '0124239769', 'Egbaidomeh Daniel', 'Savings', 1),
  ('Opay',   '8109491987', 'Egbaidomeh Daniel', 'Savings', 2)
on conflict (bank_name, account_number) do nothing;

-- ───────────── "Show love" supporters (captured before redirecting to Selar) ─────────────
-- Payment happens on Selar, so a row here is a *promise*. The admin checks Selar's ShowLove
-- dashboard, then confirms (sends thanks) or dismisses.
create table if not exists public.bn_supporters (
  id            bigint generated always as identity primary key,
  name          text not null,
  email         text not null,
  status        text not null default 'new' check (status in ('new', 'thanked', 'dismissed')),
  visitor_id    text,
  created_at    timestamptz not null default now(),
  thanked_at    timestamptz
);
create index if not exists bn_supporters_created_idx on public.bn_supporters (created_at desc);

-- ───────────── Paperback orders ─────────────
create sequence if not exists public.bn_order_code_seq start 1;

create table if not exists public.bn_orders (
  id                uuid primary key default gen_random_uuid(),
  code              text not null unique default ('BN-' || lpad(nextval('public.bn_order_code_seq')::text, 4, '0')),
  access_token      text not null,             -- lets the buyer reopen their order page
  name              text not null,
  email             text not null,
  phone             text not null,
  fulfilment        text not null check (fulfilment in ('delivery', 'pickup')),
  address           text,
  area              text,
  quantity          int not null check (quantity between 1 and 50),
  unit_price        int not null,
  total             int not null,
  note              text,
  status            text not null default 'pending_payment' check (status in (
                      'pending_payment',    -- order placed, waiting for transfer
                      'payment_submitted',  -- buyer says they've paid (from which account)
                      'acknowledged',       -- admin confirmed payment; queued for supply
                      'rejected',           -- admin couldn't find the payment; buyer may confirm again
                      'dispatched',         -- delivery: out for delivery
                      'ready_for_pickup',   -- pickup: waiting at the store
                      'delivered',
                      'picked_up',
                      'cancelled')),
  payer_name        text,                   -- name on the account the buyer paid from
  payer_bank        text,
  payer_reference   text,                   -- optional transfer reference / session ID
  admin_note        text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  payment_reported_at timestamptz,
  acknowledged_at   timestamptz,
  dispatched_at     timestamptz,
  completed_at      timestamptz,
  cancelled_at      timestamptz
);
-- If an earlier version of this script already created bn_orders, bring it up to date.
alter table public.bn_orders add column if not exists payer_name text;
alter table public.bn_orders add column if not exists payer_bank text;
alter table public.bn_orders add column if not exists payer_reference text;
alter table public.bn_orders add column if not exists payment_reported_at timestamptz;

create index if not exists bn_orders_status_idx on public.bn_orders (status, created_at desc);

-- Audit trail: every status change, who made it and how.
create table if not exists public.bn_order_history (
  id           bigint generated always as identity primary key,
  order_id     uuid not null references public.bn_orders (id) on delete cascade,
  from_status  text,
  to_status    text not null,
  actor        text not null,   -- 'buyer' | 'admin' | 'admin-email'
  note         text,
  created_at   timestamptz not null default now()
);
create index if not exists bn_order_history_order_idx on public.bn_order_history (order_id, created_at);

-- People outside Lagos who wanted delivery: demand we can follow up later.
create table if not exists public.bn_waitlist (
  id          bigint generated always as identity primary key,
  name        text not null,
  email       text not null,
  phone       text,
  location    text not null,
  quantity    int not null default 1,
  created_at  timestamptz not null default now()
);

-- ───────────── Settings the admin changes in /admin → Settings (prices, phase, links…) ─────────────
-- A missing key falls back to the value in the server's environment variables.
create table if not exists public.bn_settings (
  key         text primary key,
  value       text not null,
  updated_at  timestamptz not null default now()
);

-- ───────────── Where pickup buyers collect their copy (managed in /admin → Settings) ─────────────
create table if not exists public.bn_pickup_locations (
  id          bigint generated always as identity primary key,
  name        text not null,          -- short, shown on the landing page, e.g. "Opebi, Ikeja"
  address     text not null,          -- full address, sent to buyers
  is_active   boolean not null default true,
  sort_order  int not null default 0,
  created_at  timestamptz not null default now()
);

insert into public.bn_pickup_locations (name, address, sort_order)
select 'Opebi, Ikeja', 'No 19, Fagbemi Street, Off Opebi Road, Ikeja, Lagos, Nigeria', 1
where not exists (select 1 from public.bn_pickup_locations);

alter table public.bn_settings         enable row level security;
alter table public.bn_pickup_locations enable row level security;
alter table public.bn_events         enable row level security;
alter table public.bn_bank_accounts  enable row level security;
alter table public.bn_supporters     enable row level security;
alter table public.bn_orders         enable row level security;
alter table public.bn_order_history  enable row level security;
alter table public.bn_waitlist       enable row level security;

-- ───────────── Dashboard numbers in one call (used by /api/admin/summary) ─────────────
create or replace function public.bn_dashboard_summary()
returns json
language sql
stable
set search_path = public
as $$
  select json_build_object(
    'visits',          (select count(*) from bn_events where type = 'visit'),
    'unique_visitors', (select count(distinct visitor_id) from bn_events where type = 'visit'),
    'clicks',          (select coalesce(json_object_agg(type, n), '{}'::json)
                          from (select type, count(*) n from bn_events where type <> 'visit' group by type) t),
    'daily_visits',    (select coalesce(json_agg(json_build_object('day', d, 'visits', n) order by d), '[]'::json)
                          from (select (created_at at time zone 'Africa/Lagos')::date d, count(*) n
                                  from bn_events
                                 where type = 'visit' and created_at > now() - interval '30 days'
                                 group by 1) t),
    'orders',          (select coalesce(json_object_agg(status, n), '{}'::json)
                          from (select status, count(*) n from bn_orders group by status) t),
    'copies_confirmed',  (select coalesce(sum(quantity), 0) from bn_orders
                           where status in ('acknowledged', 'dispatched', 'ready_for_pickup', 'delivered', 'picked_up')),
    'revenue_confirmed', (select coalesce(sum(total), 0) from bn_orders
                           where status in ('acknowledged', 'dispatched', 'ready_for_pickup', 'delivered', 'picked_up')),
    'supporters',      (select coalesce(json_object_agg(status, n), '{}'::json)
                          from (select status, count(*) n from bn_supporters group by status) t),
    'waitlist',        (select count(*) from bn_waitlist)
  );
$$;

-- Functions in public are callable through the API by default; keep this one server-only.
revoke execute on function public.bn_dashboard_summary() from public, anon, authenticated;

-- Tell the Supabase API to pick up the new tables/function immediately.
notify pgrst, 'reload schema';
