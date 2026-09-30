// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest'
import { createRoot } from 'react-dom/client'
import { act } from 'react'

const h = vi.hoisted(() => ({ configured: true }))
vi.mock('./lib/supabase', () => ({
  get configured() { return h.configured },
  sb: { auth: { getSession: async () => ({ data: { session: null } }), onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }) } },
}))

async function render() {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true
  const { default: App } = await import('./App')
  const el = document.createElement('div'); document.body.append(el)
  await act(async () => { createRoot(el).render(<App />) })
  return el.textContent
}
describe('App renders something real', () => {
  it('shows the sign-in screen when configured', async () => { h.configured = true; const t = await render(); expect(t).toContain('Ledgerly'); expect(t).toContain('Sign in') })
  it('shows a setup screen, not a blank page, when env vars are missing', async () => { h.configured = false; expect(await render()).toContain('VITE_SUPABASE_URL') })
})
