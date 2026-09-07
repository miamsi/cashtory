# Budget Tracker — Streamlit + Supabase + Groq

An AI-powered rebuild of your envelope-budgeting spreadsheet — with login, and
built to be used month after month, not just once.

**Why Streamlit, not Vercel/Next.js:** this is a data-entry-and-dashboard tool.
Streamlit gets you working forms, tables, and charts against Supabase (plus
Supabase Auth for login) in a fraction of the code a separate frontend/backend
would need — the more efficient choice here.

## What's new in this version

- **Login & signup** via Supabase Auth (email/password). Every table is
  scoped to the logged-in user with Postgres Row Level Security — one
  Supabase project can serve many people, each seeing only their own data.
- **Monthly periods.** Income, fixed costs, savings, envelope categories, and
  the transaction ledger all belong to a specific month. A **Months** page
  lets you close out the current month and roll into the next one:
  - Wallet balances (real cash sitting in an e-wallet) carry forward as next
    month's opening balance automatically.
  - Envelope categories are copied forward so you're not retyping them.
  - Buffer + unspent envelope leftovers are proposed as a single "carry-over"
    income line for next month (editable/skippable) — mirroring how your
    original sheet folded last month's leftover salary into this month's
    income.
  - Every past month's numbers stay exactly as they were; nothing is mutated
    retroactively.

## What it does

| Original sheet | In this app |
|---|---|
| `income`, `fix and early spendings`, `savings` | **Setup** page (per month) |
| `encumbrance` | **Envelopes & Wallets** page (per month) |
| `wallets` | Wallet catalog (persistent) + opening balance per month |
| `Buffer` | `lib/logic.py :: buffer_summary()` |
| `Model` | `lib/logic.py :: allocation_model()` |
| `Buffer Flow` (buffer in / threshold / buffer out / reversal) | `lib/logic.py :: buffer_flow()` |
| `Records` | **Transactions** page (ledger, manual + AI entry) |
| `Quick View` | Dashboard metric row |
| `Consumption Performance` | Dashboard chart |

**AI, via Groq** (`lib/ai.py`):
- **Quick add** — type an expense in plain language ("top up gopay 50000",
  "beli kopi 25000 pakai gopay") and Groq proposes the correct ledger leg(s),
  following the double-entry pattern in your history (e.g. a wallet top-up
  debits Buffer and credits the wallet). You always review/edit before it's
  saved — the model never writes to the database directly.
- **Chat assistant** — ask questions about the currently selected month;
  answers are grounded in your live Supabase data, not invented.

## Setup

### 1. Supabase
1. Create a project at [supabase.com](https://supabase.com).
2. **Enable email/password auth**: Authentication → Providers → Email
   (enabled by default). Decide whether you want email confirmation on
   signup (Authentication → Settings) — turn it off for the fastest personal
   setup, or leave it on and confirm via the email Supabase sends.
3. Open the SQL editor and run everything in `db/schema.sql`.
4. Grab your **Project URL** and the **anon/public key** (Settings → API).
   That's the only key the app itself needs — Row Level Security keeps users'
   data separated even with this public key.

### 2. Groq
Get an API key from [console.groq.com/keys](https://console.groq.com/keys).
Default model is `llama-3.3-70b-versatile`, changeable anytime on the
**Setup → App settings** page.

### 3. Local run
```bash
cd finance-tracker
python -m venv venv && source venv/bin/activate     # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# edit .env with SUPABASE_URL, SUPABASE_ANON_KEY, GROQ_API_KEY

streamlit run app.py
```
Sign up with an email/password on first launch, then head to the **Months**
page to create your first month (or import your existing data — see below).

### 4. Load your existing September 2026 data (optional, one-time)
`db/seed.sql` contains your real data from the uploaded spreadsheet, ready to
run in the Supabase SQL editor:

1. Sign up in the app once (so your `auth.users` row exists).
2. Open `db/seed.sql`, replace `'YOUR_EMAIL_HERE'` with the email you signed
   up with.
3. Run it in the Supabase SQL editor.

It creates a "September 2026" period and loads your income, fixed spending,
savings, envelope categories, wallets, and full 54-row transaction ledger —
verified to reproduce the same Buffer (Rp 1,691,617), Model, and Buffer Flow
numbers as your spreadsheet.

**For future months**, either use the in-app **Months → Start next month**
roll-forward wizard (recommended — it also carries wallet balances and
envelopes forward automatically), or run:
```bash
python scripts/seed_from_excel.py path/to/october.xlsx you@example.com "October 2026" 2026-10-01 2026-10-31
```
This script needs `SUPABASE_SERVICE_KEY` (Settings → API → service_role) in
your `.env` — keep that key local, never in Streamlit secrets or the deployed
app, since it bypasses Row Level Security.

### 5. Deploy
**Streamlit Community Cloud** (free, simplest): push this folder to a GitHub
repo, deploy at [share.streamlit.io](https://share.streamlit.io), and add
`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `GROQ_API_KEY` under the app's
**Secrets**. (Do not add `SUPABASE_SERVICE_KEY` there — it's only for the
local import script.)

Any other host that runs a long-lived Python process works too (Render,
Railway, Fly.io, a VM).

## Project layout
```
finance-tracker/
├── app.py                    # Auth gate + page router (st.navigation)
├── pages/
│   ├── login.py               # Sign in / sign up
│   ├── dashboard.py           # This month's overview
│   ├── transactions.py        # Ledger: AI quick-add, manual entry, history
│   ├── allocations.py         # Envelope categories, wallet catalog + balances, Model view
│   ├── periods.py             # Create months, roll-forward wizard
│   ├── ai_assistant.py        # Chat over the selected month's data
│   └── setup.py                # Income / fixed spending / savings / app settings
├── lib/
│   ├── auth.py                # Supabase Auth (session kept per-browser-session)
│   ├── db.py                  # Supabase data access (period-scoped)
│   ├── logic.py               # Spreadsheet formulas, ported to Python
│   ├── ai.py                  # Groq: transaction parsing + chat
│   └── ui.py                  # Sidebar: account info, month switcher
├── db/
│   ├── schema.sql             # Run once in Supabase
│   └── seed.sql               # Your real September 2026 data, ready to run
├── scripts/seed_from_excel.py # Admin import for future months (service key)
├── requirements.txt
└── .env.example
```

## A security note on the auth implementation
The Supabase client used for data queries is stored in `st.session_state`,
**not** `st.cache_resource`. `st.cache_resource` is a process-wide cache
shared by every visitor to a deployed Streamlit app — caching a logged-in
client there would leak one user's session to another. `st.session_state` is
per-browser-session, which is what a login system needs. If you extend
`lib/auth.py` or `lib/db.py`, keep that distinction in mind.

One practical limitation: the session lives in Streamlit's session state, so
a full server restart (or, on some deployments, an extended idle period) logs
everyone out — there's no persistent "remember me" cookie. Fine for a
personal tool; if you want longer-lived sessions, look at a cookie-storage
package like `streamlit-cookies-controller` to persist the refresh token.

## Extending it
- The AI parser only ever proposes legs against allocation names that already
  exist for the selected month, and never auto-saves. Relax the guardrail in
  `lib/ai.py :: parse_transaction` if you want it to create new envelope
  categories on the fly.
- `lib/logic.py :: propose_rollover()` currently proposes ALL non-wallet
  leftover (Buffer + unspent envelopes) as one lump carry-over income line.
  If you'd rather some envelopes NOT roll their leftover into next month's
  income (e.g. discard it, or make some categories roll their fund forward
  as-is instead), that's the function to adjust.
