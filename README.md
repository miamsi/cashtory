# Ledgerly

A React 18 + Vite app (JSX in `src/`), with two small serverless functions in `api/` (Groq AI proxy and a daily job). Supabase for auth and data.

## Deploy (about 10 minutes)
1. **Supabase:** SQL Editor → run `schema.sql`, then `schema_v2.sql`, then `schema_v3_hardening.sql`.
   Authentication → Sign In / Providers → Email: minimum password length 8. Authentication → URL Configuration: set Site URL to your Vercel URL.
2. **Put this folder on Vercel**, either way:
   - **CLI (no GitHub):** unzip, open a terminal in the folder, run `npm i` then `npx vercel`. Accept the defaults.
   - **GitHub:** push the *contents* of this folder to a repo (`package.json` must be at the repo root), then Vercel → Add New → Project → import it. Framework: Vite.
3. **Environment variables** (Vercel → Project → Settings → Environment Variables), then **Redeploy**:
   - `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `GROQ_API_KEY` (required)
   - `VITE_CURRENCY` (optional, default IDR)
   - `SUPABASE_SERVICE_ROLE_KEY` + `CRON_SECRET` (optional pair, for the daily scheduled-payments job)
   Never put `VITE_` in front of the Groq or service-role keys: `VITE_` values are shipped to the browser.
4. Open the URL. You should see the **Ledgerly sign-in screen**. If you see "One step left" instead, step 3 is missing or you did not redeploy.

## Local
`npm i`, copy `.env.example` to `.env`, `npm run dev`. For `/api` locally use `npx vercel dev`. Tests: `npm test`.

Notes: the AI rate limit/cache live per serverless instance (fine at small scale). The cron runs 00:00 UTC.
