// Pure functions: no React, easy to test.
export const CUR = import.meta.env.VITE_CURRENCY || 'IDR'
export const CATS = ['Food','Groceries','Transport','Bills','Shopping','Health','Entertainment','Education','Salary','Other']
const KW = { Food:/food|lunch|dinner|coffee|cafe|makan|restaurant|breakfast/i, Transport:/grab|gojek|uber|taxi|fuel|bensin|parking|bus|train/i, Bills:/electric|water|internet|rent|phone|pulsa|insurance|listrik/i, Groceries:/grocer|supermarket|indomaret|alfamart|market/i, Shopping:/shop|amazon|tokopedia|shopee|clothes/i, Health:/doctor|pharmacy|medic|gym|hospital/i, Entertainment:/netflix|spotify|movie|game|cinema/i, Salary:/salary|gaji|paycheck|bonus/i, Education:/course|book|school|tuition/i }
export const localCategory = (n, rules = []) => { const s = (n || '').toLowerCase(); return rules.find(r => s.includes(r.keyword))?.category || Object.keys(KW).find(k => KW[k].test(s)) }
export const fmt = n => new Intl.NumberFormat(undefined, { style: 'currency', currency: CUR, maximumFractionDigits: 0 }).format(n || 0)
export const iso = d => new Date(d - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10)
export const periodStart = p => { const d = new Date(); d.setHours(0,0,0,0); if (p === 'weekly') d.setDate(d.getDate() - ((d.getDay() + 6) % 7)); if (p === 'monthly') d.setDate(1); return iso(d) }
export const nextDate = (d, every) => { const x = new Date(d + 'T00:00'); every === 'weekly' ? x.setDate(x.getDate() + 7) : x.setMonth(x.getMonth() + 1); return iso(x) }

export const balance = (a, tx) => +a.opening + tx.reduce((s, t) =>
  s + (t.account_id === a.id ? (t.kind === 'income' ? 1 : -1) * t.amount : 0) + (t.to_account_id === a.id ? +t.amount : 0), 0)
export const netWorth = (acc, tx) => acc.reduce((s, a) => s + balance(a, tx), 0)
export const spent = (tx, cat, period) => tx.filter(t => t.kind === 'expense' && (cat === 'All' || t.category === cat) && t.date >= periodStart(period)).reduce((s, t) => s + +t.amount, 0)
export const avgMonthlyNet = tx => { const m = {}; tx.filter(t => t.kind !== 'transfer').forEach(t => { const k = t.date.slice(0, 7); m[k] = (m[k] || 0) + (t.kind === 'income' ? 1 : -1) * t.amount }); const v = Object.values(m); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : 0 }
export function summary({ accounts, transactions: tx, budgets }) {
  const mo = iso(new Date()).slice(0, 7), m = tx.filter(t => t.date.startsWith(mo) && t.kind !== 'transfer'), byCategory = {}
  const sum = k => m.filter(t => t.kind === k).reduce((s, t) => s + +t.amount, 0)
  m.filter(t => t.kind === 'expense').forEach(t => byCategory[t.category] = (byCategory[t.category] || 0) + +t.amount)
  return { month: mo, currency: CUR, income: sum('income'), expense: sum('expense'), byCategory, netWorth: netWorth(accounts, tx),
    budgets: budgets.map(b => ({ category: b.category, period: b.period, limit: b.amount, spent: spent(tx, b.category, b.period) })) }
}

// What is safe to spend today: (monthly limit − spent before today − bills still due) ÷ days left, minus today's spending.
export function safeToSpend(tx, budgets, recurring) {
  const b = budgets.find(x => x.category === 'All' && x.period === 'monthly'); if (!b) return null
  const now = new Date(), dim = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate(), days = dim - now.getDate() + 1
  const end = iso(new Date(now.getFullYear(), now.getMonth(), dim)); let upcoming = 0
  recurring.filter(r => r.kind === 'expense').forEach(r => { let d = r.next_due, n = 0; while (d <= end && n < 40) { upcoming += +r.amount; d = nextDate(d, r.every); n++ } })
  const used = spent(tx, 'All', 'daily'), before = spent(tx, 'All', 'monthly') - used
  const allowance = (b.amount - before - upcoming) / days
  return { allowance, used, left: allowance - used, days, upcoming, daily: b.amount / dim }
}
