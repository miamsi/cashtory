import { useState } from 'react'
import { useData } from '../context/DataContext'
import Sheet from '../components/Sheet'
import { fmt } from '../lib/finance'

export default function Bills() {
  const { splits, recurring, accounts, insert, update, remove } = useData()
  const [add, setAdd] = useState(false), [settle, setSettle] = useState(null), [acc, setAcc] = useState(accounts[0]?.id)
  const [f, setF] = useState({ dir: 'receivable', names: '', total: '', note: '' })
  const set = k => e => setF({ ...f, [k]: e.target.value })
  const open = splits.filter(s => !s.settled), sum = d => open.filter(s => s.direction === d).reduce((a, s) => a + +s.amount, 0)

  const save = async () => {
    const names = f.names.split(',').map(s => s.trim()).filter(Boolean), total = +f.total
    if (!names.length || !total) return
    const each = names.length > 1 ? total / (names.length + 1) : total // several names = even split including you
    await insert('splits', names.map(person => ({ person, direction: f.dir, amount: Math.round(each), note: f.note })))
    setAdd(false); setF({ ...f, names: '', total: '', note: '' })
  }
  const confirm = async () => {
    const s = settle, rec = s.direction === 'receivable'
    await insert('transactions', { account_id: acc, kind: rec ? 'income' : 'expense', amount: s.amount, category: 'Other', note: (rec ? 'From ' : 'To ') + s.person + (s.note ? ' · ' + s.note : '') })
    await update('splits', s.id, { settled: true }); setSettle(null)
  }

  return <>
    <div className="row"><h2>Split bills</h2><button className="ghost" onClick={() => setAdd(true)}>Add bill</button></div>
    <div className="row"><div className="card" style={{ flex: 1 }}><div className="mute">Owed to you</div><b className="good">{fmt(sum('receivable'))}</b></div>
      <div className="card" style={{ flex: 1 }}><div className="mute">You owe</div><b className="bad">{fmt(sum('payable'))}</b></div></div>
    {splits.map(s => <div className="card row" key={s.id} style={{ opacity: s.settled ? .5 : 1 }}>
      <div><b>{s.person}</b><div className="mute">{s.direction === 'receivable' ? 'owes you' : 'you owe'} {fmt(s.amount)}{s.note ? ' · ' + s.note : ''}</div></div>
      {s.settled ? <button className="ghost" onClick={() => remove('splits', s.id)}>Clear</button> : <button onClick={() => setSettle(s)}>Settle</button>}
    </div>)}
    {!splits.length && <div className="card"><b>Nothing to settle</b><p className="mute">Add a shared bill. Enter several names to split it evenly with you.</p></div>}
    <h2>Scheduled</h2>
    {recurring.map(r => <div className="card row" key={r.id}><div><b>{r.note || r.category}</b><div className="mute">{r.every} · next {r.next_due}</div></div>
      <div><b>{fmt(r.amount)}</b><button className="ghost" onClick={() => remove('recurring', r.id)}>Stop</button></div></div>)}
    {!recurring.length && <p className="mute">Choose a repeat option when adding a transaction to automate it.</p>}

    <Sheet open={add} onClose={() => setAdd(false)}>
      <h2 style={{ marginTop: 0 }}>New shared bill</h2>
      <div className="seg">{[['receivable', 'They owe me'], ['payable', 'I owe them']].map(([k, l]) => <button key={k} className={f.dir === k ? 'on' : ''} onClick={() => setF({ ...f, dir: k })}>{l}</button>)}</div>
      <input placeholder="Name(s), e.g. Ana, Budi" value={f.names} onChange={set('names')} />
      <input inputMode="decimal" placeholder="Total bill" value={f.total} onChange={set('total')} />
      <input placeholder="Note (dinner, rent…)" value={f.note} onChange={set('note')} />
      <button style={{ width: '100%' }} onClick={save}>Save</button>
    </Sheet>
    <Sheet open={!!settle} onClose={() => setSettle(null)}>
      {settle && <><h2 style={{ marginTop: 0 }}>Settle with {settle.person}</h2>
        <p className="mute" style={{ marginBottom: 10 }}>{fmt(settle.amount)} will be recorded as {settle.direction === 'receivable' ? 'income' : 'an expense'}.</p>
        <select value={acc} onChange={e => setAcc(e.target.value)}>{accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select>
        <button style={{ width: '100%' }} onClick={confirm}>Confirm</button></>}
    </Sheet>
  </>
}
