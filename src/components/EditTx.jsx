import { useState } from 'react'
import { useData } from '../context/DataContext'
import { CATS } from '../lib/finance'

// Edit a transaction. Changing its category also teaches a rule, so the same merchant is never sent to AI again.
export default function EditTx({ tx, onDone }) {
  const { update, remove, insert, rules } = useData()
  const [f, setF] = useState({ amount: tx.amount, note: tx.note || '', category: tx.category || 'Other', date: tx.date })
  const set = k => e => setF({ ...f, [k]: e.target.value })
  const transfer = tx.kind === 'transfer'
  const save = async () => {
    const patch = { amount: +f.amount, date: f.date, ...(transfer ? {} : { note: f.note.trim(), category: f.category }) }
    if (!patch.amount) return
    onDone()
    try {
      await update('transactions', tx.id, patch)
      if (!transfer && f.category !== tx.category && patch.note) {
        const keyword = patch.note.toLowerCase().split(/\s+/).slice(0, 3).join(' '), old = rules.find(r => r.keyword === keyword)
        old ? await update('rules', old.id, { category: f.category }) : await insert('rules', { keyword, category: f.category })
      }
    } catch (e) { alert(e.message) }
  }
  return <>
    <h2 style={{ marginTop: 0 }}>Edit {tx.kind}</h2>
    <input inputMode="decimal" value={f.amount} onChange={set('amount')} aria-label="Amount" />
    {!transfer && <><input value={f.note} onChange={set('note')} placeholder="Note" aria-label="Note" />
      <select value={f.category} onChange={set('category')} aria-label="Category">{CATS.map(c => <option key={c}>{c}</option>)}</select></>}
    <input type="date" value={f.date} onChange={set('date')} aria-label="Date" />
    <div className="row"><button className="sec" onClick={() => { onDone(); remove('transactions', tx.id).catch(e => alert(e.message)) }}>Delete</button><button style={{ flex: 1 }} onClick={save}>Save changes</button></div>
  </>
}
