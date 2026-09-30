import { useState } from 'react'
import { useData } from '../context/DataContext'
import QuickAdd from '../components/QuickAdd'
import Settings from '../components/Settings'
import EditTx from '../components/EditTx'
import Sheet from '../components/Sheet'
import { Pace, Where } from '../components/Insights'
import { balance, fmt, netWorth, safeToSpend } from '../lib/finance'

export default function Home({ openAccount, goto }) {
  const { accounts, transactions: tx, budgets, recurring } = useData()
  const [edit, setEdit] = useState(null)
  const nw = netWorth(accounts, tx), s = safeToSpend(tx, budgets, recurring)
  const pct = s ? Math.min(100, s.used / Math.max(1, s.allowance) * 100) : 0
  return <>
    {s ? <>
      <p className="mute">Safe to spend today</p>
      <div className={'hero ' + (s.left < 0 ? 'bad' : '')}>{fmt(s.left)}</div>
      <div className="bar"><i className={pct > 85 ? 'hot' : ''} style={{ width: pct + '%' }} /></div>
      <p className="mute" style={{ marginTop: 6 }}>{fmt(s.used)} of {fmt(s.allowance)} today · {s.days} days left{s.upcoming ? ` · ${fmt(s.upcoming)} in bills still due` : ''}</p>
      <Pace tx={tx} daily={s.daily} />
    </> : <div className="card"><b>What is safe to spend today?</b>
      <p className="mute" style={{ margin: '4px 0 10px' }}>Set an overall monthly budget and this becomes your daily number.</p>
      <button onClick={() => goto('budget')}>Set monthly budget</button></div>}

    <QuickAdd />
    <Where tx={tx} />
    <div className="row"><h2>Accounts</h2><button className="ghost" onClick={openAccount}>Add account</button></div>
    <p className="mute" style={{ marginBottom: 8 }}>Net worth {fmt(nw)}</p>
    {accounts.length ? accounts.map(a => { const b = balance(a, tx); return (
      <div className="card row" key={a.id}><div><b>{a.name}</b><div className="mute">{a.type === 'credit' ? 'Credit card' : a.type}</div></div><b className={b < 0 ? 'bad' : ''}>{fmt(b)}</b></div>) })
      : <div className="card"><b>Start with your accounts</b><p className="mute">Add each wallet, bank account or card with its current balance.</p></div>}
    <h2>Recent</h2>
    <div className="card">{tx.slice(0, 15).map(t => (
      <div className="tx row" key={t.id} onClick={() => setEdit(t)}>
        <div><b>{t.note || t.category || t.kind}</b><div className="mute">{t.date} · {accounts.find(a => a.id === t.account_id)?.name} · {t.kind === 'transfer' ? 'Transfer' : t.category}</div></div>
        <b className={t.kind === 'income' ? 'good' : ''}>{t.kind === 'income' ? '+' : t.kind === 'expense' ? '−' : ''}{fmt(t.amount)}</b>
      </div>))}{!tx.length && <p className="mute">Nothing yet. Type your first expense above.</p>}</div>
    <Settings />
    <Sheet open={!!edit} onClose={() => setEdit(null)}>{edit && <EditTx tx={edit} onDone={() => setEdit(null)} />}</Sheet>
  </>
}
