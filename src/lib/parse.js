import { localCategory } from './finance'
// Turns "lunch 45k bca" / "gaji 8jt" / "grab 1.5rb gopay" into a transaction. Runs locally, instantly, no AI.
const AMT = /(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(k|rb|ribu|jt|juta|m)?(?![a-z\d])/i
const MULT = { k: 1e3, rb: 1e3, ribu: 1e3, jt: 1e6, juta: 1e6, m: 1e6 }
const toNum = (s, u) => (/^\d{1,3}([.,]\d{3})+$/.test(s) ? +s.replace(/[.,]/g, '') : +s.replace(',', '.')) * (MULT[(u || '').toLowerCase()] || 1)

export function parseQuick(text, accounts, rules = []) {
  const m = text.match(AMT); if (!m) return null
  const amount = toNum(m[1], m[2]); if (!amount) return null
  let rest = text.replace(m[0], ' ')
  const acc = accounts.find(a => new RegExp('\\b' + a.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'i').test(rest)) || accounts[0]
  rest = rest.replace(new RegExp('\\b' + acc.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'i'), ' ')
  const kind = /^\s*\+|\b(salary|gaji|income|received|terima|refund)\b/i.test(text) ? 'income' : 'expense'
  const note = rest.replace(/^\s*\+/, '').replace(/\s+/g, ' ').trim()
  return { kind, amount, note, account: acc, category: localCategory(note, rules) }
}
