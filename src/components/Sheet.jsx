export default function Sheet({ open, onClose, children }) {
  if (!open) return null
  return <div id="sheet" className="open" onClick={e => e.target === e.currentTarget && onClose()}><div>{children}</div></div>
}
