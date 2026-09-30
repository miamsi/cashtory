-- Run after schema.sql and schema_v2.sql.
-- A user may only attach transactions/schedules to accounts they own.
drop policy "own rows" on transactions;
create policy "own rows" on transactions for all using (user_id = auth.uid()) with check (
  user_id = auth.uid()
  and exists (select 1 from accounts a where a.id = account_id and a.user_id = auth.uid())
  and (to_account_id is null or exists (select 1 from accounts a where a.id = to_account_id and a.user_id = auth.uid())));
drop policy "own rows" on recurring;
create policy "own rows" on recurring for all using (user_id = auth.uid()) with check (
  user_id = auth.uid() and exists (select 1 from accounts a where a.id = account_id and a.user_id = auth.uid()));
alter table transactions add constraint note_len check (char_length(note) <= 200);
alter table transactions add constraint date_sane check (date >= '2000-01-01');
create index on transactions(account_id);
create index on accounts(user_id);
create index on budgets(user_id);
create index on splits(user_id);
create index on rules(user_id);
create index on recurring(user_id, next_due);
