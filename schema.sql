-- Run in Supabase SQL editor. Every table is private per user via RLS.
create table accounts(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  name text not null,
  type text not null default 'cash' check (type in ('cash','bank','ewallet','credit','asset')),
  opening numeric not null default 0,
  credit_limit numeric,
  created_at timestamptz default now());

create table transactions(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  account_id uuid not null references accounts on delete cascade,
  to_account_id uuid references accounts on delete cascade,
  kind text not null check (kind in ('income','expense','transfer')),
  amount numeric not null check (amount > 0),
  category text, note text,
  date date not null default current_date,
  created_at timestamptz default now());
create index on transactions(user_id, date desc);

create table budgets(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  category text not null,               -- 'All' = overall limit
  period text not null check (period in ('daily','weekly','monthly')),
  amount numeric not null check (amount > 0),
  created_at timestamptz default now());

create table splits(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  person text not null,
  direction text not null check (direction in ('payable','receivable')),
  amount numeric not null check (amount > 0),
  note text, settled boolean not null default false,
  created_at timestamptz default now());

create table recurring(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  account_id uuid not null references accounts on delete cascade,
  kind text not null check (kind in ('income','expense')),
  amount numeric not null check (amount > 0),
  category text, note text,
  every text not null check (every in ('weekly','monthly')),
  next_due date not null,
  created_at timestamptz default now());

do $$ declare t text; begin
  foreach t in array array['accounts','transactions','budgets','splits','recurring'] loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy "own rows" on %I for all using (user_id = auth.uid()) with check (user_id = auth.uid())', t);
  end loop;
end $$;
