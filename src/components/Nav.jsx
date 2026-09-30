const TABS = [['home', '🏠', 'Home'], ['budget', '🎯', 'Budget'], ['bills', '🤝', 'Bills'], ['plan', '🧮', 'Plan'], ['wrap', '✨', 'Wrapped']]
export default function Nav({ tab, setTab }) {
  return <nav>{TABS.map(([k, i, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}><b>{i}</b>{l}</button>)}</nav>
}
