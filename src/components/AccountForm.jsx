import { useState } from 'react'
import { useData } from '../context/DataContext'
export default function AccountForm({ onDone }) {
  const { insert } = useData()
  const [f, setF] = useState({ name: '', type: 'bank', opening: '', limit: '' })
  const set = k => e => setF({ ...f, [k]: e.target.value })
  const save = async () => {
    if (!f.name.trim()) return
    const o = +f.opening || 0, credit = f.type === 'credit'
    await insert('accounts', { name: f.name.trim(), type: f.type, opening: credit ? -o : o, credit_limit: credit ? +f.limit || null : null })
    onDone()
  }
  return <>
    <h2 style={{ marginTop: 0 }}>New account</h2>
    <input placeholder="Name (e.g. BCA, Wallet)" value={f.name} onChange={set('name')} />
    <select value={f.type} onChange={set('type')}>{['cash', 'bank', 'ewallet', 'credit', 'asset'].map(t => <option key={t}>{t}</option>)}</select>
    <input inputMode="decimal" placeholder="Current balance (card: amount owed)" value={f.opening} onChange={set('opening')} />
    {f.type === 'credit' && <input inputMode="numeric" placeholder="Credit limit" value={f.limit} onChange={set('limit')} />}
    <button style={{ width: '100%' }} onClick={save}>Save account</button>
  </>
}
