import { useState } from 'react'
import { useData } from '../context/DataContext'
import Sheet from '../components/Sheet'
import { CATS, fmt, spent } from '../lib/finance'
export default function Budget() {
  const { budgets, transactions: tx, insert, remove } = useData()
  const [open, setOpen] = useState(false), [f, setF] = useState({ category: 'All', period: 'monthly', amount: '' })
  const set = k => e => setF({ ...f, [k]: e.target.value })
  const save = async () => { if (!+f.amount) return; await insert('budgets', { ...f, amount: +f.amount }); setOpen(false) }
  return <>
    <div className="row"><h2>Budgets</h2><button className="ghost" onClick={() => setOpen(true)}>Add budget</button></div>
    {budgets.map(b => { const s = spent(tx, b.category, b.period), p = Math.min(100, s / b.amount * 100); return (
      <div className="card" key={b.id}>
        <div className="row"><b>{b.category} · {b.period}</b><button className="ghost" onClick={() => remove('budgets', b.id)}>Remove</button></div>
        <div className="row mute"><span>{fmt(s)} of {fmt(b.amount)}</span><span className={s > b.amount ? 'bad' : ''}>{s > b.amount ? fmt(s - b.amount) + ' over' : fmt(b.amount - s) + ' left'}</span></div>
        <div className="bar"><i className={p > 85 ? 'hot' : ''} style={{ width: p + '%' }} /></div>
      </div>) })}
    {!budgets.length && <div className="card"><b>Set a limit</b><p className="mute">Cap a category or all spending per day, week or month.</p></div>}
    <Sheet open={open} onClose={() => setOpen(false)}>
      <h2 style={{ marginTop: 0 }}>New budget</h2>
      <select value={f.category} onChange={set('category')}>{['All', ...CATS.filter(c => c !== 'Salary')].map(c => <option key={c}>{c}</option>)}</select>
      <select value={f.period} onChange={set('period')}><option value="monthly">Monthly</option><option value="weekly">Weekly</option><option value="daily">Daily</option></select>
      <input inputMode="numeric" placeholder="Limit" value={f.amount} onChange={set('amount')} />
      <button style={{ width: '100%' }} onClick={save}>Save budget</button>
    </Sheet>
  </>
}
