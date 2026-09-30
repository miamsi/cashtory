import { describe, it, expect, vi, afterEach } from 'vitest'
import { parseQuick } from './parse'
import { balance, localCategory, safeToSpend } from './finance'

const accs = [{ id: 'a1', name: 'BCA', opening: 0 }, { id: 'a2', name: 'Gopay', opening: 0 }]
describe('parseQuick', () => {
  it('reads amount, account, note and category', () => {
    const p = parseQuick('lunch 45k bca', accs)
    expect(p).toMatchObject({ amount: 45000, kind: 'expense', note: 'lunch', category: 'Food' }); expect(p.account.id).toBe('a1')
  })
  it('handles jt, rb and dotted thousands', () => {
    expect(parseQuick('gaji 8jt', accs)).toMatchObject({ amount: 8e6, kind: 'income' })
    expect(parseQuick('grab 1.5rb gopay', accs).amount).toBe(1500)
    expect(parseQuick('makan 45.000', accs).amount).toBe(45000)
  })
  it('treats a leading + as income and rejects text without an amount', () => {
    expect(parseQuick('+ freelance 2jt', accs).kind).toBe('income'); expect(parseQuick('hello', accs)).toBeNull()
  })
})
describe('balance', () => {
  it('applies income, expense and transfers in both directions', () => {
    const a = { id: 'a1', opening: 1000 }
    const tx = [{ account_id: 'a1', kind: 'income', amount: 500 }, { account_id: 'a1', kind: 'expense', amount: 200 }, { account_id: 'a1', kind: 'transfer', to_account_id: 'a2', amount: 100 }, { account_id: 'a2', kind: 'transfer', to_account_id: 'a1', amount: 50 }]
    expect(balance(a, tx)).toBe(1250)
  })
})
describe('localCategory', () => {
  it('lets learned rules beat built-in keywords', () => { expect(localCategory('coffee beans', [{ keyword: 'coffee beans', category: 'Groceries' }])).toBe('Groceries'); expect(localCategory('coffee')).toBe('Food') })
})
describe('safeToSpend', () => {
  afterEach(() => vi.useRealTimers())
  it('is null without a monthly budget', () => expect(safeToSpend([], [], [])).toBeNull())
  it('spreads what is left over the remaining days', () => {
    vi.useFakeTimers({ toFake: ['Date'] }); vi.setSystemTime(new Date('2026-09-15T12:00:00'))
    const tx = [{ kind: 'expense', category: 'Food', amount: 1000000, date: '2026-09-10' }, { kind: 'expense', category: 'Food', amount: 50000, date: '2026-09-15' }]
    const s = safeToSpend(tx, [{ category: 'All', period: 'monthly', amount: 3000000 }], [])
    expect(s.days).toBe(16); expect(s.allowance).toBe(125000); expect(s.left).toBe(75000)
  })
})
