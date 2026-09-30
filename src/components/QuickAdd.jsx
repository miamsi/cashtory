import { useState } from 'react'
import { useData } from '../context/DataContext'
import { parseQuick } from '../lib/parse'
import { categorize } from '../lib/ai'
import { fmt, iso } from '../lib/finance'

// One line, Enter to save: "lunch 45k bca". Suffixes: k, rb, jt. Start with + for income.
// Saves instantly with a best-guess category; if the keywords missed, AI refines it in the background.
export default function QuickAdd() {
  const { accounts, insert, update, rules } = useData()
  const [text, setText] = useState(''), [msg, setMsg] = useState('')
  if (!accounts.length) return null
  const submit = e => {
    e.preventDefault()
    const p = parseQuick(text, accounts, rules); if (!p) return setMsg('Include an amount, like "lunch 45k".')
    const id = crypto.randomUUID(), fast = p.category || (p.kind === 'income' ? 'Salary' : 'Other')
    setMsg(`Saved ${p.note || fast} · ${fast} · ${fmt(p.amount)} from ${p.account.name}`); setText('')
    insert('transactions', { id, kind: p.kind, amount: p.amount, account_id: p.account.id, note: p.note, category: fast, date: iso(new Date()) })
      .then(() => !p.category && p.note && categorize(p.note, rules).then(c => c && c !== fast && update('transactions', id, { category: c })))
      .catch(err => setMsg(err.message))
  }
  return <form onSubmit={submit} style={{ margin: '14px 0 6px' }}>
    <div className="row" style={{ gap: 8 }}>
      <input style={{ margin: 0 }} aria-label="Quick add" placeholder='Type it: "lunch 45k bca"' value={text} onChange={e => setText(e.target.value)} enterKeyHint="done" />
      <button disabled={!text.trim()} type="submit">Add</button>
    </div>
    {msg && <p className="mute" style={{ marginTop: 6 }} role="status">{msg}</p>}
  </form>
}
