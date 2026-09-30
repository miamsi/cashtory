import { iso } from '../lib/finance'
import { fmt } from '../lib/finance'

// Bars = spend per day this month. Red = above an even daily pace. Faded = days still to come.
export function Pace({ tx, daily }) {
  const now = new Date(), dim = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate(), mo = iso(now).slice(0, 7), day = now.getDate()
  const by = Array(dim).fill(0); tx.forEach(t => { if (t.kind === 'expense' && t.date.startsWith(mo)) by[+t.date.slice(8) - 1] += +t.amount })
  const max = Math.max(...by, daily || 1)
  return <div className="pace" role="img" aria-label="Spending per day this month">{by.map((v, i) =>
    <i key={i} className={i + 1 === day ? 'today' : i + 1 > day ? 'future' : daily && v > daily ? 'hot' : ''} style={{ height: Math.max(4, v / max * 100) + '%' }} />)}</div>
}

// Top categories this month as one stacked bar with a legend.
export function Where({ tx }) {
  const mo = iso(new Date()).slice(0, 7), by = {}
  tx.forEach(t => { if (t.kind === 'expense' && t.date.startsWith(mo)) by[t.category] = (by[t.category] || 0) + +t.amount })
  const top = Object.entries(by).sort((a, b) => b[1] - a[1]).slice(0, 5)
  if (!top.length) return null
  return <div className="card"><b>Where it went</b>
    <div className="stack">{top.map(([c, v], i) => <i key={c} style={{ flex: v, background: `var(--c${i})` }} />)}</div>
    <div className="legend mute">{top.map(([c, v], i) => <span key={c} style={{ '--k': `var(--c${i})` }}>{c} {fmt(v)}</span>)}</div></div>
}
