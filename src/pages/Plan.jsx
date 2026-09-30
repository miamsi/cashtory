import { useState } from 'react'
import { useData } from '../context/DataContext'
import { ai } from '../lib/ai'
import { avgMonthlyNet, fmt, summary } from '../lib/finance'

export default function Plan() {
  const d = useData(), tx = d.transactions
  const [goal, setGoal] = useState(''), [months, setMonths] = useState('')
  const cats = [...new Set(tx.filter(t => t.kind === 'expense').map(t => t.category))]
  const [cat, setCat] = useState(cats[0] || ''), [cut, setCut] = useState(20)
  const [q, setQ] = useState(''), [res, setRes] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState('')

  // Reverse calculation: what a goal demands vs what you actually save
  const avg = avgMonthlyNet(tx), need = +goal && +months ? goal / months : 0, gap = Math.max(0, need - avg)
  // Simulation: average monthly spend in a category, reduced by cut%
  const span = new Set(tx.map(t => t.date.slice(0, 7))).size || 1
  const monthly = tx.filter(t => t.kind === 'expense' && t.category === cat).reduce((s, t) => s + +t.amount, 0) / span
  // Forecast: month-end projection from this month's pace
  const s = summary(d), now = new Date(), dim = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate(), proj = s.expense / now.getDate() * dim

  const ask = async () => {
    if (!q.trim()) return; setBusy(true); setErr('')
    try { setRes(await ai('scenario', { summary: s, scenario: q.trim() })) } catch (e) { setErr(e.message) }
    setBusy(false)
  }

  return <>
    <h2>Reach a goal</h2>
    <div className="card">
      <input inputMode="numeric" placeholder="Goal amount" value={goal} onChange={e => setGoal(e.target.value)} />
      <input inputMode="numeric" placeholder="In how many months" value={months} onChange={e => setMonths(e.target.value)} />
      {need ? <p>Save <b>{fmt(need)}</b> a month ({fmt(need / 30.4)} a day). Your average monthly surplus is <b>{fmt(avg)}</b>. {gap ? <span className="bad">Short by {fmt(gap)} a month, about {fmt(gap / 30.4)} less spent per day.</span> : <span className="good">You are on track.</span>}</p>
        : <p className="mute">Enter a goal to see what it takes.</p>}
    </div>
    <h2>What if I cut back</h2>
    <div className="card">
      {cats.length ? <>
        <select value={cat} onChange={e => setCat(e.target.value)}>{cats.map(c => <option key={c}>{c}</option>)}</select>
        <div className="row mute"><span>Cut by</span><b>{cut}%</b></div>
        <input type="range" min="5" max="100" step="5" value={cut} onChange={e => setCut(+e.target.value)} />
        <p>You spend about {fmt(monthly)} a month on {cat}. Cutting {cut}% saves <b className="good">{fmt(monthly * cut / 100)}</b> a month, <b className="good">{fmt(monthly * cut / 100 * 12)}</b> a year.</p>
      </> : <p className="mute">Add some expenses to simulate savings.</p>}
    </div>
    <h2>Forecast</h2>
    <div className="card">Spent so far: <b>{fmt(s.expense)}</b><br />At this pace you will spend <b>{fmt(proj)}</b> by month end.<br /><span className="mute">Projected balance change: {fmt(s.income - proj)}</span></div>
    <h2>Ask a what-if</h2>
    <div className="card">
      <textarea rows="2" placeholder="e.g. What if I cook at home 4 days a week?" value={q} onChange={e => setQ(e.target.value)} />
      <button disabled={busy} onClick={ask}>{busy ? 'Thinking…' : 'Simulate with AI'}</button>
      {err && <p className="bad" style={{ marginTop: 8 }}>{err}</p>}
      {res && <div style={{ marginTop: 10 }}><p>{res.answer}</p><p className="mute">Per month: {fmt(res.monthly_impact)} · Per year: {fmt(res.yearly_impact)}</p></div>}
    </div>
  </>
}
