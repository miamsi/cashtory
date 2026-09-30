import { useState } from 'react'
import { sb } from '../lib/supabase'
export default function Auth() {
  const [email, setEmail] = useState(''), [password, setPw] = useState(''), [msg, setMsg] = useState(''), [busy, setBusy] = useState(false)
  const go = async kind => {
    if (!email.trim()) return setMsg('Enter your email first.')
    if (kind === 'up' && password.length < 8) return setMsg('Use at least 8 characters.')
    setBusy(true)
    const c = { email: email.trim(), password }
    const { error } = kind === 'in' ? await sb.auth.signInWithPassword(c) : kind === 'up' ? await sb.auth.signUp(c) : await sb.auth.resetPasswordForEmail(c.email, { redirectTo: location.origin })
    setMsg(error ? error.message : kind === 'up' ? 'Check your email to confirm, then sign in.' : kind === 'reset' ? 'If that email has an account, a reset link is on its way.' : '')
    setBusy(false)
  }
  return <div className="auth">
    <div className="hero">Ledgerly</div><p className="mute" style={{ margin: '6px 0 22px' }}>Know where it went. Plan where it goes.</p>
    <input type="email" placeholder="Email" aria-label="Email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} />
    <input type="password" placeholder="Password (8+ characters)" aria-label="Password" autoComplete="current-password" value={password} onChange={e => setPw(e.target.value)} onKeyDown={e => e.key === 'Enter' && go('in')} />
    {msg && <p className="bad" role="alert" style={{ marginBottom: 8 }}>{msg}</p>}
    <button style={{ width: '100%' }} disabled={busy} onClick={() => go('in')}>Sign in</button>
    <button className="ghost" style={{ width: '100%', marginTop: 8 }} disabled={busy} onClick={() => go('up')}>Create account</button>
    <button className="ghost" style={{ width: '100%' }} disabled={busy} onClick={() => go('reset')}>Forgot password</button>
  </div>
}
export function NewPassword({ onDone }) {
  const [pw, setPw] = useState(''), [msg, setMsg] = useState('')
  const save = async () => { if (pw.length < 8) return setMsg('Use at least 8 characters.'); const { error } = await sb.auth.updateUser({ password: pw }); error ? setMsg(error.message) : onDone() }
  return <div className="auth"><h2>Choose a new password</h2>
    <input type="password" aria-label="New password" autoComplete="new-password" placeholder="New password (8+ characters)" value={pw} onChange={e => setPw(e.target.value)} />
    {msg && <p className="bad" role="alert" style={{ marginBottom: 8 }}>{msg}</p>}<button style={{ width: '100%' }} onClick={save}>Save password</button></div>
}
