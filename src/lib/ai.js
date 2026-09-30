import { sb } from './supabase'
import { CATS, localCategory } from './finance'
export async function ai(task, payload) {
  const { data: { session } } = await sb.auth.getSession()
  if (!session) throw new Error('Please sign in again.')
  const r = await fetch('/api/ai', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + session.access_token }, body: JSON.stringify({ task, payload }) })
  const j = await r.json(); if (!r.ok) throw new Error(j.error || 'AI error'); return j
}
// Local keywords first; AI only when they miss (saves Groq quota and latency).
export async function categorize(note, rules = []) {
  const hit = localCategory(note, rules); if (hit || !note) return hit
  try {
    const r = await Promise.race([ai('categorize', { items: [{ id: '1', note }], categories: CATS }), new Promise((_, j) => setTimeout(j, 5000))])
    const c = r.items?.[0]?.category; return CATS.includes(c) ? c : null
  } catch { return null }
}
// Cache AI outputs per month so revisiting a tab never re-calls Groq.
export async function cached(key, fn) {
  key = 'ai:' + key // cleared on sign-out so accounts never share cached AI output
  try { const c = localStorage.getItem(key); if (c) return JSON.parse(c) } catch {}
  const v = await fn(); try { localStorage.setItem(key, JSON.stringify(v)) } catch {}
  return v
}
