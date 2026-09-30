import { sb } from '../lib/supabase'
import { useData } from '../context/DataContext'
const cell = v => { const s = String(v ?? ''); return '"' + (/^[=+\-@]/.test(s) ? "'" + s : s).replace(/"/g, '""') + '"' } // guards against spreadsheet formula injection
export default function Settings() {
  const { transactions, accounts } = useData()
  const exportCsv = () => {
    const name = id => accounts.find(a => a.id === id)?.name
    const rows = [['date', 'kind', 'amount', 'category', 'note', 'account', 'to_account'], ...transactions.map(t => [t.date, t.kind, t.amount, t.category, t.note, name(t.account_id), name(t.to_account_id)])]
    const url = URL.createObjectURL(new Blob([rows.map(r => r.map(cell).join(',')).join('\n')], { type: 'text/csv' }))
    Object.assign(document.createElement('a'), { href: url, download: 'ledgerly-transactions.csv' }).click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const signOut = async () => { Object.keys(localStorage).filter(k => k.startsWith('ai:')).forEach(k => localStorage.removeItem(k)); await sb.auth.signOut() }
  return <div className="row" style={{ margin: '24px 0 8px' }}><button className="sec" onClick={exportCsv}>Export CSV</button><button className="sec" onClick={signOut}>Sign out</button></div>
}
