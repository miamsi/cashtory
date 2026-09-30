import { useState } from 'react'
import { useData } from '../context/DataContext'
import { CATS, iso, nextDate } from '../lib/finance'
import { categorize } from '../lib/ai'

export default function TxForm({ onDone }) {
  const { accounts, insert, rules } = useData()
  const [kind, setKind] = useState('expense')
  const [f, setF] = useState({ amount: '', account_id: accounts[0].id, to: accounts[1]?.id || accounts[0].id, note: '', category: '', date: iso(new Date()), repeat: '' })
  const [busy, setBusy] = useState(false), [err, setErr] = useState('')
  const set = k => e => setF({ ...f, [k]: e.target.value })

  const save = async () => {
    const amount = +f.amount; if (!amount) return setErr('Enter an amount')
    if (kind === 'transfer' && f.to === f.account_id) return setErr('Pick two different accounts')
    setBusy(true)
    try {
      const row = { kind, amount, account_id: f.account_id, date: f.date }
      if (kind === 'transfer') row.to_account_id = f.to
      else {
        row.note = f.note.trim()
        row.category = f.category || (await categorize(row.note, rules)) || (kind === 'income' ? 'Salary' : 'Other')
        if (f.repeat) await insert('recurring', { account_id: row.account_id, kind, amount, category: row.category, note: row.note, every: f.repeat, next_due: nextDate(f.date, f.repeat) })
      }
      await insert('transactions', row); onDone()
    } catch (e) { setErr(e.message); setBusy(false) }
  }

  return <>
    <div className="seg">{['expense', 'income', 'transfer'].map(k => <button key={k} className={k === kind ? 'on' : ''} onClick={() => setKind(k)}>{k[0].toUpperCase() + k.slice(1)}</button>)}</div>
    <input inputMode="decimal" placeholder="Amount" autoFocus value={f.amount} onChange={set('amount')} />
    <select value={f.account_id} onChange={set('account_id')}>{accounts.map(a => <option key={a.id} value={a.id}>{kind === 'transfer' ? 'From ' : ''}{a.name}</option>)}</select>
    {kind === 'transfer'
      ? <select value={f.to} onChange={set('to')}>{accounts.map(a => <option key={a.id} value={a.id}>To {a.name}</option>)}</select>
      : <>
          <input placeholder="What was it? (AI picks the category)" value={f.note} onChange={set('note')} />
          <select value={f.category} onChange={set('category')}><option value="">Auto category</option>{CATS.map(c => <option key={c}>{c}</option>)}</select>
        </>}
    <input type="date" value={f.date} onChange={set('date')} />
    {kind !== 'transfer' && <select value={f.repeat} onChange={set('repeat')}><option value="">Does not repeat</option><option value="weekly">Repeats weekly</option><option value="monthly">Repeats monthly</option></select>}
    {err && <p className="bad" style={{ marginBottom: 8 }}>{err}</p>}
    <button style={{ width: '100%' }} disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save'}</button>
  </>
}
