'use client'

import { useEffect } from 'react'
import { supabase } from '@/lib/supabase'

/**
 * Bridge component to expose auth token to Chrome extension
 *
 * The extension can't read cookies from SSR Supabase clients,
 * so we write the token to a special localStorage key for the extension.
 */
export function ExtensionBridge() {
  useEffect(() => {
    if (typeof window === 'undefined') return

    const EXTENSION_AUTH_KEY = 'particles-extension-auth'

    // Helper to store token for extension
    const storeTokenForExtension = (session: any) => {
      if (session?.access_token) {
        const authData = {
          access_token: session.access_token,
          expires_at: session.expires_at,
          refresh_token: session.refresh_token,
          user: session.user
        }
        localStorage.setItem(EXTENSION_AUTH_KEY, JSON.stringify(authData))
        console.log('[Extension Bridge] Token stored for extension')
      } else {
        localStorage.removeItem(EXTENSION_AUTH_KEY)
        console.log('[Extension Bridge] Token removed (signed out)')
      }
    }

    // Just listen for auth state changes - don't make initial getSession() call
    // The INITIAL_SESSION event from onAuthStateChange will provide the session
    // This avoids racing with AuthContext's auth initialization
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      console.log('[Extension Bridge] Auth state changed:', event)
      storeTokenForExtension(session)
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  return null // This component doesn't render anything
}
