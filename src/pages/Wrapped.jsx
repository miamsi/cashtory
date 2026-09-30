import { useState } from 'react'
import { useData } from '../context/DataContext'
import { ai, cached } from '../lib/ai'
import { summary } from '../lib/finance'
export default function Wrapped() {
  const d = useData(), [out, setOut] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState('')
  const run = async () => {
    setBusy(true); setErr('')
    try {
      const s = summary(d), k = s.month + d.transactions.length
      const [w, a] = await Promise.all([cached('w' + k, () => ai('wrapped', { summary: s })), cached('a' + k, () => ai('advice', { summary: s }))])
      setOut({ w, a })
    } catch (e) { setErr(e.message) }
    setBusy(false)
  }
  return <>
    <h2>Your month, wrapped</h2><p className="mute" style={{ marginBottom: 12 }}>A quick recap with advice for next month.</p>
    {!out && <button style={{ width: '100%' }} disabled={busy} onClick={run}>{busy ? 'Crunching your month…' : 'Generate recap'}</button>}
    {err && <p className="bad">{err}</p>}
    {out && <>
      <div className="slides">{out.w.slides.map((x, i) => <div className="slide" key={i}><div className="e">{x.emoji}</div><b>{x.title}</b><div className="s">{x.stat}</div><div>{x.text}</div></div>)}</div>
      <h2>{out.a.headline}</h2>{out.a.tips.map((t, i) => <div className="card" key={i}>{t}</div>)}
    </>}
  </>
}
