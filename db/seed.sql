-- ============================================================================
-- Seed: your existing September 2026 data
-- Run this in the Supabase SQL editor AFTER: (1) running db/schema.sql, and
-- (2) signing up in the app at least once so your auth.users row exists.
--
-- Edit the email below to match the account you signed up with, then run.
-- ============================================================================

do $$
declare
    v_user_id   uuid;
    v_period_id uuid;
begin
    select id into v_user_id from auth.users where email = 'YOUR_EMAIL_HERE' limit 1;
    if v_user_id is null then
        raise exception 'No user found for that email -- sign up in the app first, then edit the email above and re-run.';
    end if;

    -- clear any previous active period, then create this one
    update periods set is_active = false where user_id = v_user_id and is_active;
    insert into periods (user_id, label, start_date, end_date, is_active)
    values (v_user_id, 'September 2026', '2026-09-01', '2026-09-30', true)
    returning id into v_period_id;

    -- income
    insert into income (user_id, period_id, date, description, amount) values (v_user_id, v_period_id, '2026-09-01', 'Last month leftover gapok', 1889883);
    insert into income (user_id, period_id, date, description, amount) values (v_user_id, v_period_id, '2026-09-01', 'Last month leftover tukin', 1552497);
    insert into income (user_id, period_id, date, description, amount) values (v_user_id, v_period_id, '2026-09-01', 'gapok', 2798600);
    insert into income (user_id, period_id, date, description, amount) values (v_user_id, v_period_id, '2026-09-01', 'tukin', 11450000);

    -- fixed & early spendings
    insert into fixed_spending (user_id, period_id, date, description, amount) values (v_user_id, v_period_id, '2026-09-01', 'Cicilan kartu kredit', 1936863);
    insert into fixed_spending (user_id, period_id, date, description, amount) values (v_user_id, v_period_id, '2026-09-01', 'Iuran kantor', 200000);
    insert into fixed_spending (user_id, period_id, date, description, amount) values (v_user_id, v_period_id, '2026-09-01', 'Bulanan ke rumah', 2002500);
    insert into fixed_spending (user_id, period_id, date, description, amount) values (v_user_id, v_period_id, '2026-09-02', 'Rumah dinas', 25000);

    -- savings
    insert into savings (user_id, period_id, date, description, amount) values (v_user_id, v_period_id, '2026-09-01', 'Tabungan rutin', 3830000);

    -- envelope categories (encumbrance)
    insert into encumbrance (user_id, period_id, name, amount) values (v_user_id, v_period_id, 'Beli tiket bus tua', 1500000);
    insert into encumbrance (user_id, period_id, name, amount) values (v_user_id, v_period_id, 'Jatah konsumsi harian', 4650000);
    insert into encumbrance (user_id, period_id, name, amount) values (v_user_id, v_period_id, 'Listrik', 305000);
    insert into encumbrance (user_id, period_id, name, amount) values (v_user_id, v_period_id, 'Bensin', 200000);
    insert into encumbrance (user_id, period_id, name, amount) values (v_user_id, v_period_id, 'Keperluan rumah', 300000);
    insert into encumbrance (user_id, period_id, name, amount) values (v_user_id, v_period_id, 'Subscription', 150000);
    insert into encumbrance (user_id, period_id, name, amount) values (v_user_id, v_period_id, 'Paket Internet', 600000);
    insert into encumbrance (user_id, period_id, name, amount) values (v_user_id, v_period_id, 'Entertainment', 300000);

    -- wallet catalog (persistent names)
    insert into wallets (user_id, name) values (v_user_id, 'Starbucks Card') on conflict (user_id, name) do nothing;
    insert into wallets (user_id, name) values (v_user_id, 'Ovo') on conflict (user_id, name) do nothing;
    insert into wallets (user_id, name) values (v_user_id, 'Gopay') on conflict (user_id, name) do nothing;
    insert into wallets (user_id, name) values (v_user_id, 'E-Money') on conflict (user_id, name) do nothing;
    insert into wallets (user_id, name) values (v_user_id, 'Dana') on conflict (user_id, name) do nothing;
    insert into wallets (user_id, name) values (v_user_id, 'Cash on hand') on conflict (user_id, name) do nothing;
    insert into wallets (user_id, name) values (v_user_id, 'Shopee Pay') on conflict (user_id, name) do nothing;

    -- this period's opening wallet balances
    insert into period_wallets (user_id, period_id, wallet_name, opening_balance) values (v_user_id, v_period_id, 'Starbucks Card', 8500);
    insert into period_wallets (user_id, period_id, wallet_name, opening_balance) values (v_user_id, v_period_id, 'Ovo', 5680);
    insert into period_wallets (user_id, period_id, wallet_name, opening_balance) values (v_user_id, v_period_id, 'Gopay', 1250);
    insert into period_wallets (user_id, period_id, wallet_name, opening_balance) values (v_user_id, v_period_id, 'E-Money', 14000);
    insert into period_wallets (user_id, period_id, wallet_name, opening_balance) values (v_user_id, v_period_id, 'Dana', 4500);
    insert into period_wallets (user_id, period_id, wallet_name, opening_balance) values (v_user_id, v_period_id, 'Cash on hand', 10000);
    insert into period_wallets (user_id, period_id, wallet_name, opening_balance) values (v_user_id, v_period_id, 'Shopee Pay', 12019);

    -- transaction ledger
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Sarapan ketoprak mas aris', 'Jatah konsumsi harian', -44000, 22000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Sarapan ketoprak mas aris', 'Jatah konsumsi harian', 22000, -22000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Top up starbucks', 'Buffer', -100000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Top up starbucks', 'Starbucks Card', 100000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Beli starbucks', 'Starbucks Card', -49000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Beli starbucks', 'Jatah konsumsi harian', -49000, 24500, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Beli starbucks', 'Jatah konsumsi harian', 24500, -24500, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Beli starbucks', 'Buffer', 49000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Parkir', 'E-Money', -6000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Makan malam', 'Jatah konsumsi harian', -56100, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Tiket bioskop', 'Entertainment', -40000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Tarik uang', 'Buffer', -100000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Tarik uang', 'Cash on hand', 100000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Isi bensin', 'Bensin', -67000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Isi bensin', 'Cash on hand', -67000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-01', 'Isi bensin', 'Buffer', 67000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Iuran tambahan kantor', 'Buffer', -50000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Sarapan kopi kaya', 'Jatah konsumsi harian', -42000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Tiket bus tua', 'Beli tiket bus tua', -1500000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Beli kopi point', 'Jatah konsumsi harian', -21000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Beli kopi orang', 'Buffer', -123000, 123000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Beli kopi orang', 'Buffer', 25000, -25000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Beli kopi orang', 'Buffer', 23000, -23000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Makan siang sop tunjang', 'Jatah konsumsi harian', -25000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Parkir', 'Cash on hand', -1000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-02', 'Parkir', 'Buffer', 1000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-03', 'Sarapan indomie', 'Jatah konsumsi harian', -20000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-03', 'Beli starbucks', 'Jatah konsumsi harian', -25500, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-03', 'Beli starbucks', 'Starbucks Card', -25500, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-03', 'Beli starbucks', 'Buffer', 25500, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-03', 'Beli makan malam', 'Jatah konsumsi harian', -103200, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-04', 'Beli starbucks', 'Jatah konsumsi harian', -70000, 35000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-04', 'Beli starbucks', 'Jatah konsumsi harian', 35000, -35000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-04', 'Beli eight burger', 'Jatah konsumsi harian', -62050, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-04', 'Beli paket data tante', 'Paket Internet', -100000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-04', 'Parkir', 'E-Money', -4000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-04', 'Beli kado perpisahan rose', 'Buffer', -158400, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-04', 'Beli makan malam ayam cabe ijo', 'Jatah konsumsi harian', -25000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-05', 'Beli makan siang ketoprak', 'Jatah konsumsi harian', -25770, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-05', 'Beli kopi', 'Jatah konsumsi harian', -70000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-05', 'Subscription apple music', 'Subscription', -61050, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-06', 'Top up emoney', 'Buffer', -20000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-06', 'Top up emoney', 'E-Money', 20000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-06', 'Parkir', 'E-Money', -6000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-06', 'Top up emoney', 'Buffer', 6000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-06', 'Beli kopi orang', 'Jatah konsumsi harian', 25000, -25000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-06', 'Beli masker', 'Jatah konsumsi harian', -11900, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-06', 'Beli starbucks', 'Jatah konsumsi harian', -70000, 35000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-06', 'Beli makan malam', 'Jatah konsumsi harian', -28981, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-07', 'Beli sarapan', 'Jatah konsumsi harian', -20000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-07', 'Beli starbucks', 'Jatah konsumsi harian', 35000, -35000, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-07', 'Beli kopken', 'Jatah konsumsi harian', -27301, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-07', 'Tarik uang', 'Cash on hand', 15000, 0, 'import');
    insert into transactions (user_id, period_id, date, description, allocation, cash_basis, receivables, source) values (v_user_id, v_period_id, '2026-09-07', 'Tarik uang', 'Buffer', -15000, 0, 'import');

    -- default per-user app settings
    insert into settings (user_id, key, value) values
        (v_user_id, 'daily_budget_category', 'Jatah konsumsi harian'),
        (v_user_id, 'daily_budget_amount', '150000'),
        (v_user_id, 'groq_model', 'llama-3.3-70b-versatile')
    on conflict (user_id, key) do nothing;

    raise notice 'Seeded September 2026 for user %', v_user_id;
end $$;
