import { useEffect, useState } from 'react'
import { sb } from '../lib/supabase'
// session: undefined = loading, null = signed out. recovering = opened from a password-reset email.
export default function useSession() {
  const [session, setS] = useState(undefined), [recovering, setRecovering] = useState(false)
  useEffect(() => {
    sb.auth.getSession().then(({ data }) => setS(data.session))
    const { data } = sb.auth.onAuthStateChange((ev, s) => { if (ev === 'PASSWORD_RECOVERY') setRecovering(true); setS(s) })
    return () => data.subscription.unsubscribe()
  }, [])
  return { session, recovering, setRecovering }
}
