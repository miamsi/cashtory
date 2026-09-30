import { Component, useEffect, useState } from 'react'
import useSession from './hooks/useSession'
import { configured } from './lib/supabase'
import { DataProvider, useData } from './context/DataContext'
import Auth, { NewPassword } from './pages/Auth'
import Home from './pages/Home'
import Budget from './pages/Budget'
import Bills from './pages/Bills'
import Plan from './pages/Plan'
import Wrapped from './pages/Wrapped'
import Sheet from './components/Sheet'
import Nav from './components/Nav'
import TxForm from './components/TxForm'
import AccountForm from './components/AccountForm'

const PAGES = { home: Home, budget: Budget, bills: Bills, plan: Plan, wrap: Wrapped }

class Boundary extends Component {
  state = { e: null }
  static getDerivedStateFromError(e) { return { e } }
  render() {
    return this.state.e
      ? <div className="auth"><h2>Something went wrong</h2><p className="mute" style={{ margin: '6px 0 14px' }}>Your data is safe. Reload to continue.</p><button onClick={() => location.reload()}>Reload</button></div>
      : this.props.children
  }
}

// Any failed save that isn't handled locally surfaces as a toast instead of failing silently.
function useToast() {
  const [m, setM] = useState('')
  useEffect(() => {
    let h; const on = e => { e.preventDefault(); setM(e.reason?.message || 'Something went wrong. Try again.'); clearTimeout(h); h = setTimeout(() => setM(''), 4000) }
    addEventListener('unhandledrejection', on); return () => removeEventListener('unhandledrejection', on)
  }, [])
  return m
}

function Shell() {
  const [tab, setTab] = useState('home'), [modal, setModal] = useState(null)
  const { ready, accounts, error } = useData()
  const Page = PAGES[tab]
  if (!ready) return <main id="v"><p className="mute">Loading…</p></main>
  return <>
    <main id="v">{error && <p className="bad" role="alert">Could not load your data: {error}</p>}<Page openAccount={() => setModal('acc')} goto={setTab} /></main>
    <button id="fab" aria-label="Add transaction" onClick={() => setModal(accounts.length ? 'tx' : 'acc')}>+</button>
    <Nav tab={tab} setTab={setTab} />
    <Sheet open={!!modal} onClose={() => setModal(null)}>
      {modal === 'tx' && <TxForm onDone={() => setModal(null)} />}
      {modal === 'acc' && <AccountForm onDone={() => setModal(null)} />}
    </Sheet>
  </>
}

function Root() {
  const { session, recovering, setRecovering } = useSession(), toast = useToast()
  return <Boundary>
    {toast && <div id="toast" role="alert" style={{ display: 'block' }}>{toast}</div>}
    {session === undefined ? null : recovering ? <NewPassword onDone={() => setRecovering(false)} /> : !session ? <Auth /> : <DataProvider><Shell /></DataProvider>}
  </Boundary>
}

function Setup() {
  return <div className="auth"><h2>One step left</h2>
    <p className="mute" style={{ margin: '8px 0 12px' }}>The app is running, but it cannot find its Supabase settings. In Vercel open Settings → Environment Variables and add <b>VITE_SUPABASE_URL</b> and <b>VITE_SUPABASE_ANON_KEY</b>, then <b>redeploy</b>. These values are baked in at build time, so adding them without redeploying changes nothing.</p></div>
}

export default function App() { return configured ? <Root /> : <Setup /> }
