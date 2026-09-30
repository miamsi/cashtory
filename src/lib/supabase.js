import { createClient } from '@supabase/supabase-js'
const url = import.meta.env.VITE_SUPABASE_URL, key = import.meta.env.VITE_SUPABASE_ANON_KEY
// Never crash on missing settings: App shows a "setup needed" screen instead of a blank page.
export const configured = Boolean(url && key)
export const sb = configured ? createClient(url, key) : null
