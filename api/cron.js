// Daily pipeline: post due scheduled payments for every user. Vercel Cron sends `Authorization: Bearer $CRON_SECRET`.
import { createClient } from '@supabase/supabase-js'
const iso = d => new Date(d - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10)
const next = (d, e) => { const x = new Date(d + 'T00:00'); e === 'weekly' ? x.setDate(x.getDate() + 7) : x.setMonth(x.getMonth() + 1); return iso(x) }

export default async function handler(req, res) {
  if (!process.env.CRON_SECRET || req.headers.authorization !== 'Bearer ' + process.env.CRON_SECRET) return res.status(401).end()
  const sb = createClient(process.env.VITE_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY)
  const today = iso(new Date()); let posted = 0
  const { data: due, error } = await sb.from('recurring').select('*').lte('next_due', today)
  if (error) return res.status(500).json({ error: error.message })
  for (const r of due) {
    let d = r.next_due, n = 0
    while (d <= today && n < 12) {
      const nx = next(d, r.every)
      // Compare-and-swap: only the caller that advances next_due may post, so the app and cron never double-post.
      const { data: won } = await sb.from('recurring').update({ next_due: nx }).eq('id', r.id).eq('next_due', d).select('id')
      if (!won?.length) break
      await sb.from('transactions').insert({ user_id: r.user_id, account_id: r.account_id, kind: r.kind, amount: r.amount, category: r.category, note: r.note, date: d })
      d = nx; n++; posted++
    }
  }
  res.json({ posted })
}
