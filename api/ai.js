// Vercel serverless function. Env: GROQ_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY
const URL_ = 'https://api.groq.com/openai/v1/chat/completions';
// Fast tier for categorisation, smart tier for advice/forecasts; each falls back down the chain.
const MODELS = {
  fast: ['openai/gpt-oss-20b', 'qwen/qwen3-32b'],
  smart: ['openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'qwen/qwen3-32b'],
};
const TASKS = {
  categorize: p => ['fast', `Categorise each transaction by its note. Reply JSON only: {"items":[{"id":"","category":""}]}. category must be exactly one of: ${p.categories.join(', ')}.`, { items: p.items }],
  advice: p => ['smart', `You are a concise personal budgeting coach. Using the monthly summary, reply JSON only: {"headline":"","tips":["",""]} with 3-4 specific, actionable tips citing real numbers and categories. Currency: ${p.summary.currency}.`, p.summary],
  wrapped: p => ['smart', `Write a fun, warm "Spotify Wrapped"-style recap of the user's month. Reply JSON only: {"slides":[{"emoji":"","title":"","stat":"","text":""}]} with 5 slides: top category, biggest saving or overspend, budget performance, savings rate, one recommendation for next month. Keep text under 25 words. Currency: ${p.summary.currency}.`, p.summary],
  scenario: p => ['smart', `You are a financial simulator. Given the user's summary and a what-if scenario, estimate the impact per month and over 12 months. Reply JSON only: {"answer":"","monthly_impact":0,"yearly_impact":0}. State assumptions briefly. Currency: ${p.summary.currency}.`, { summary: p.summary, scenario: p.scenario }],
};

const cache = new Map(), authCache = new Map(), hits = new Map();
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function user(token) {
  const c = authCache.get(token);
  if (c && c.exp > Date.now()) return c.id;
  const r = await fetch(process.env.VITE_SUPABASE_URL + '/auth/v1/user', {
    headers: { apikey: process.env.VITE_SUPABASE_ANON_KEY, Authorization: 'Bearer ' + token },
  });
  if (!r.ok) return null;
  const id = (await r.json()).id;
  if (authCache.size > 500) authCache.delete(authCache.keys().next().value);
  authCache.set(token, { id, exp: Date.now() + 5 * 60e3 });
  return id;
}

async function groq(tier, system, data) {
  let last = 'unknown';
  for (const model of MODELS[tier]) {
    for (let attempt = 0; attempt < 2; attempt++) {
      const r = await fetch(URL_, {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + process.env.GROQ_API_KEY, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model, temperature: 0.3, max_completion_tokens: 1500,
          response_format: { type: 'json_object' },
          ...(model.includes('gpt-oss') ? { reasoning_effort: 'low' } : { reasoning_format: 'hidden' }),
          messages: [{ role: 'system', content: system }, { role: 'user', content: JSON.stringify(data) }],
        }),
      });
      if (r.ok) {
        try { return JSON.parse((await r.json()).choices[0].message.content); }
        catch { last = 'bad JSON'; break; } // try next model
      }
      last = 'HTTP ' + r.status;
      // Only wait/retry on a real 429 with a short retry-after; otherwise fall to the next model.
      const wait = +r.headers.get('retry-after') || 1;
      if (r.status === 429 && attempt === 0 && wait <= 3) { await sleep(wait * 1000); continue; }
      break;
    }
  }
  throw new Error('AI unavailable (' + last + ')');
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });
  try {
    const uid = await user((req.headers.authorization || '').replace('Bearer ', ''));
    if (!uid) return res.status(401).json({ error: 'Please sign in again.' });

    const { task, payload } = req.body || {};
    if (!TASKS[task]) return res.status(400).json({ error: 'Unknown task' });
    // Keep requests small and well-formed so a client can't burn quota or crash the handler.
    if (JSON.stringify(payload ?? {}).length > 20000) return res.status(413).json({ error: 'Request too large' });
    if (task === 'categorize' && !(Array.isArray(payload?.items) && payload.items.length <= 50 && Array.isArray(payload?.categories))) return res.status(400).json({ error: 'Bad request' });
    if (task !== 'categorize' && !payload?.summary) return res.status(400).json({ error: 'Bad request' });
    if (task === 'scenario' && String(payload.scenario || '').length > 500) return res.status(400).json({ error: 'Scenario too long' });

    const key = uid + task + JSON.stringify(payload);
    const hit = cache.get(key);
    if (hit && hit.exp > Date.now()) return res.json(hit.data);

    // Per-user guard (30 calls/min) so one client can't burn the shared Groq quota.
    const now = Date.now(), recent = (hits.get(uid) || []).filter(t => now - t < 60e3);
    if (recent.length >= 30) return res.status(429).json({ error: 'Slow down: too many AI requests this minute.' });
    hits.set(uid, [...recent, now]);

    const [tier, system, data] = TASKS[task](payload);
    const out = await groq(tier, system, data);
    if (cache.size > 500) cache.delete(cache.keys().next().value);
    cache.set(key, { data: out, exp: now + (task === 'categorize' ? 3600e3 : 600e3) });
    res.json(out);
  } catch (e) {
    res.status(503).json({ error: e.message });
  }
};
