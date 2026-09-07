-- ============================================================================
-- Personal Finance Tracker — Supabase schema (v2: auth + monthly periods)
-- Run once in the Supabase SQL editor (or `supabase db push`).
--
-- Design:
--   * Every table has user_id uuid default auth.uid(), and RLS restricts all
--     access to auth.uid() = user_id. Supabase Auth (email/password) is used
--     for login/signup — no extra user table needed.
--   * "periods" = one row per month. income / fixed_spending / savings /
--     encumbrance / transactions all belong to a period, so each month is
--     its own clean ledger.
--   * "wallets" is a persistent catalog of wallet NAMES (Gopay, Cash on hand,
--     ...) that doesn't change month to month. "period_wallets" holds each
--     wallet's OPENING balance for a specific period — this is what lets a
--     wallet's leftover balance roll forward into next month while still
--     keeping each month's historical numbers correct and immutable.
-- ============================================================================

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- Periods: one row per month you track
-- ---------------------------------------------------------------------------
create table if not exists periods (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
    label       text not null,                 -- e.g. "September 2026"
    start_date  date not null,
    end_date    date not null,
    is_active   boolean not null default true, -- the "current" month
    created_at  timestamptz not null default now(),
    unique (user_id, label)
);

-- Only one active period per user at a time.
create unique index if not exists one_active_period_per_user
    on periods (user_id) where is_active;

-- ---------------------------------------------------------------------------
-- Income / fixed spending / savings — period-scoped (sheets: income, fix and
-- early spendings, savings)
-- ---------------------------------------------------------------------------
create table if not exists income (
    id          bigint generated always as identity primary key,
    user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
    period_id   uuid not null references periods(id) on delete cascade,
    date        date not null default current_date,
    description text not null,
    amount      numeric(14,2) not null,
    created_at  timestamptz not null default now()
);

create table if not exists fixed_spending (
    id          bigint generated always as identity primary key,
    user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
    period_id   uuid not null references periods(id) on delete cascade,
    date        date not null default current_date,
    description text not null,
    amount      numeric(14,2) not null,
    created_at  timestamptz not null default now()
);

create table if not exists savings (
    id          bigint generated always as identity primary key,
    user_id     uuid not null default auth.uid() references auth.users(id) on delete cascade,
    period_id   uuid not null references periods(id) on delete cascade,
    date        date not null default current_date,
    description text not null,
    amount      numeric(14,2) not null,
    created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Envelope categories — period-scoped (sheet: encumbrance). Re-declared each
-- month (usually copied forward from last month by the app's roll-forward
-- action), so historical months keep their own budget even if you change
-- next month's amounts.
-- ---------------------------------------------------------------------------
create table if not exists encumbrance (
    id        bigint generated always as identity primary key,
    user_id   uuid not null default auth.uid() references auth.users(id) on delete cascade,
    period_id uuid not null references periods(id) on delete cascade,
    name      text not null,
    amount    numeric(14,2) not null default 0,
    active    boolean not null default true,
    unique (period_id, name)
);

-- ---------------------------------------------------------------------------
-- Wallets — persistent catalog of wallet/e-wallet NAMES only (sheet: wallets)
-- ---------------------------------------------------------------------------
create table if not exists wallets (
    id      bigint generated always as identity primary key,
    user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
    name    text not null,
    active  boolean not null default true,
    unique (user_id, name)
);

-- Each wallet's opening balance FOR A GIVEN PERIOD (the "Threshold"/"Fund").
create table if not exists period_wallets (
    id              bigint generated always as identity primary key,
    user_id         uuid not null default auth.uid() references auth.users(id) on delete cascade,
    period_id       uuid not null references periods(id) on delete cascade,
    wallet_name     text not null,
    opening_balance numeric(14,2) not null default 0,
    unique (period_id, wallet_name)
);

-- ---------------------------------------------------------------------------
-- The ledger (sheet: Records) — period-scoped. Each row is one leg of a
-- transaction; simple spends are a single leg, wallet top-ups/withdrawals/
-- split (cash vs receivable) payments are multiple balanced legs sharing
-- group_id. allocation references an encumbrance.name, a wallets.name, or
-- the literal 'Buffer', all within the SAME period.
-- ---------------------------------------------------------------------------
create table if not exists transactions (
    id            bigint generated always as identity primary key,
    user_id       uuid not null default auth.uid() references auth.users(id) on delete cascade,
    period_id     uuid not null references periods(id) on delete cascade,
    group_id      uuid not null default gen_random_uuid(),
    date          date not null default current_date,
    description   text not null,
    allocation    text not null,
    cash_basis    numeric(14,2) not null default 0,
    receivables   numeric(14,2) not null default 0,
    accrual_basis numeric(14,2) generated always as (cash_basis + receivables) stored,
    source        text not null default 'manual',   -- 'manual' | 'ai' | 'import'
    created_at    timestamptz not null default now()
);

create index if not exists idx_transactions_period on transactions (period_id);
create index if not exists idx_transactions_allocation on transactions (period_id, allocation);
create index if not exists idx_transactions_group on transactions (group_id);

-- ---------------------------------------------------------------------------
-- Per-user app settings (mirrors hardcoded numbers in the sheet, e.g. the
-- 150,000/day food budget used in "Consumption Performance")
-- ---------------------------------------------------------------------------
create table if not exists settings (
    user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
    key     text not null,
    value   text not null,
    primary key (user_id, key)
);

-- ---------------------------------------------------------------------------
-- Row Level Security — every table is scoped to auth.uid() = user_id.
-- With Supabase Auth + the anon key + a logged-in session, Postgres sees the
-- caller's JWT, so `auth.uid()` resolves automatically; user_id never needs
-- to be set explicitly by the app (the column default handles it).
-- ---------------------------------------------------------------------------
alter table periods enable row level security;
alter table income enable row level security;
alter table fixed_spending enable row level security;
alter table savings enable row level security;
alter table encumbrance enable row level security;
alter table wallets enable row level security;
alter table period_wallets enable row level security;
alter table transactions enable row level security;
alter table settings enable row level security;

do $$
declare
    t text;
begin
    for t in select unnest(array[
        'periods','income','fixed_spending','savings','encumbrance',
        'wallets','period_wallets','transactions','settings'
    ])
    loop
        execute format('drop policy if exists "owner access" on %I;', t);
        execute format(
            'create policy "owner access" on %I for all using (auth.uid() = user_id) with check (auth.uid() = user_id);',
            t
        );
    end loop;
end $$;

-- ---------------------------------------------------------------------------
-- Helper (reference only): default settings the app inserts for a brand-new
-- user automatically on first login — see lib/db.py :: ensure_default_settings
-- ---------------------------------------------------------------------------
-- insert into settings (key, value) values
--     ('daily_budget_category', 'Jatah konsumsi harian'),
--     ('daily_budget_amount', '150000'),
--     ('groq_model', 'llama-3.3-70b-versatile');
