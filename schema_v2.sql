-- Run after schema.sql. Learned merchant rules: correct a category once, never pay for AI on it again.
create table rules(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  keyword text not null, category text not null,
  created_at timestamptz default now(),
  unique (user_id, keyword));
alter table rules enable row level security;
create policy "own rows" on rules for all using (user_id = auth.uid()) with check (user_id = auth.uid());
