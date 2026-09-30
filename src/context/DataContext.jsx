import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { sb } from '../lib/supabase'
import { iso, nextDate } from '../lib/finance'

const TABLES = ['accounts', 'transactions', 'budgets', 'splits', 'recurring', 'rules']
const Ctx = createContext(null)
export const useData = () => useContext(Ctx)
const sortTx = (t, a) => t === 'transactions' ? [...a].sort((x, y) => y.date.localeCompare(x.date) || y.created_at.localeCompare(x.created_at)) : a

// PostgREST caps one request at 1000 rows and balances need the full history, so page through everything.
async function fetchAll(t) {
  let out = [], from = 0
  for (;;) {
    const { data, error } = await sb.from(t).select('*').order('created_at', { ascending: false }).order('id').range(from, from + 999)
    if (error) return { error }
    out = out.concat(data); if (data.length < 1000) return { data: out }; from += 1000
  }
}

export function DataProvider({ children }) {
  const [data, setData] = useState(Object.fromEntries(TABLES.map(t => [t, []])))
  const [ready, setReady] = useState(false), [error, setError] = useState('')
  const ref = useRef(data); ref.current = data
  const put = (t, fn) => setData(d => ({ ...d, [t]: sortTx(t, fn(d[t])) }))

  const load = useCallback(async () => {
    const res = await Promise.all(TABLES.map(fetchAll))
    const bad = res.find(r => r.error); if (bad) return setError(bad.error.message)
    const next = Object.fromEntries(TABLES.map((t, i) => [t, sortTx(t, res[i].data)]))
    setData(next); return next
  }, [])

  useEffect(() => { // fallback automation when the app opens; the daily cron does the same job server-side
    (async () => {
      try {
      const d = await load(); if (!d) return
      const today = iso(new Date()); let ran = 0
      for (const r of d.recurring) {
        let due = r.next_due, n = 0
        while (due <= today && n < 12) {
          const nx = nextDate(due, r.every)
          const { data: won } = await sb.from('recurring').update({ next_due: nx }).eq('id', r.id).eq('next_due', due).select('id')
          if (!won?.length) break
          await sb.from('transactions').insert({ account_id: r.account_id, kind: r.kind, amount: r.amount, category: r.category, note: r.note, date: due })
          due = nx; n++; ran++
        }
      }
      if (ran) await load()
      } catch (e) { setError(e.message) } finally { setReady(true) }
    })()
  }, [load])

  // Optimistic writes: the UI updates instantly with a client-made id; a failed write rolls itself back.
  const insert = async (t, row) => {
    const rows = (Array.isArray(row) ? row : [row]).map(r => ({ id: crypto.randomUUID(), created_at: new Date().toISOString(), ...r }))
    put(t, a => [...rows, ...a])
    const { error } = await sb.from(t).insert(rows.map(({ created_at, ...r }) => r))
    if (error) { put(t, a => a.filter(x => !rows.some(r => r.id === x.id))); throw error }
  }
  const update = async (t, id, patch) => {
    const prev = ref.current[t].find(x => x.id === id)
    put(t, a => a.map(x => x.id === id ? { ...x, ...patch } : x))
    const { error } = await sb.from(t).update(patch).eq('id', id)
    if (error) { put(t, a => a.map(x => x.id === id ? prev : x)); throw error }
  }
  const remove = async (t, id) => {
    const prev = ref.current[t].find(x => x.id === id)
    put(t, a => a.filter(x => x.id !== id))
    const { error } = await sb.from(t).delete().eq('id', id)
    if (error) { put(t, a => [prev, ...a]); throw error }
  }
  return <Ctx.Provider value={{ ...data, ready, error, load, insert, update, remove }}>{children}</Ctx.Provider>
}
