'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { User } from '@supabase/supabase-js'
import { useRouter } from 'next/navigation'
import { UserProfile, Organization } from '@/types/database'
import { supabase } from '@/lib/supabase'

interface AuthContextType {
  user: User | null
  userProfile: UserProfile | null
  organization: Organization | null
  loading: boolean
  signUp: (email: string, password: string, displayName?: string) => Promise<{ error: Error | null }>
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>
  signInWithGoogle: () => Promise<{ error: Error | null }>
  resetPassword: (email: string) => Promise<{ error: Error | null }>
  updatePassword: (newPassword: string) => Promise<{ error: Error | null }>
  signOut: () => Promise<void>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)
  const [organization, setOrganization] = useState<Organization | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  // Fetch user profile and organization with retry logic
  const fetchUserProfile = async (userId: string, retries = 3, delay = 1000) => {
    console.log('[Auth] Fetching profile for user:', userId)
    try {
      // Fetch user profile with organization data in a single optimized query
      const { data: profileData, error: profileError } = await supabase
        .from('users')
        .select('id, organization_id, role, display_name, created_at, updated_at, organization:organizations(id, name, created_at, updated_at)')
        .eq('id', userId)
        .single()

      if (profileError) {
        // If error is "Row not found" (PGRST116) and we have retries left, wait and retry
        // This handles the race condition where auth.users exists but public.users trigger hasn't finished
        if (profileError.code === 'PGRST116' && retries > 0) {
          console.log(`[Auth] Profile not found, retrying in ${delay}ms... (${retries} retries left)`)
          await new Promise(resolve => setTimeout(resolve, delay))
          return fetchUserProfile(userId, retries - 1, delay * 1.5)
        }

        console.error('Error fetching user profile:', profileError)
        return
      }

      if (profileData) {
        const { organization: org, ...profile } = profileData
        setUserProfile(profile as UserProfile)
        // Organization comes as an array from the join, take first element
        setOrganization(Array.isArray(org) ? org[0] as Organization : org as Organization)
      }
    } catch (error) {
      console.error('Error in fetchUserProfile:', error)
    }
  }

  // Refresh profile data
  const refreshProfile = async () => {
    if (user) {
      await fetchUserProfile(user.id)
    }
  }

  useEffect(() => {
    console.log('[Auth] Setting up auth listener...')
    let mounted = true

    // Safety timeout to prevent infinite loading
    const safetyTimeout = setTimeout(() => {
      if (loading && mounted) {
        console.warn('[Auth] Safety timeout triggered - forcing loading to false')
        setLoading(false)
      }
    }, 5000)

    // 1. Setup listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[Auth] Auth event:', event, { hasSession: !!session })
      if (!mounted) return

      const currentUser = session?.user ?? null
      setUser(currentUser)

      if (event === 'INITIAL_SESSION') {
        // Page load - fetch profile if user exists
        if (currentUser) {
          console.log('[Auth] Initial session - fetching profile...')
          await fetchUserProfile(currentUser.id)
        }
        // Always set loading to false after initial session check
        setLoading(false)
        clearTimeout(safetyTimeout)
      } else if (event === 'SIGNED_IN') {
        // User just signed in - fetch profile
        console.log('[Auth] Signed in - fetching profile...')
        await fetchUserProfile(currentUser!.id)
        setLoading(false)
      } else if (event === 'SIGNED_OUT') {
        setUserProfile(null)
        setOrganization(null)
        setLoading(false)
      } else if (event === 'TOKEN_REFRESHED') {
        // Handle token refresh if needed
        console.log('[Auth] Token refreshed')
      }
    })

    // 2. Explicit check for session (fallback)
    // This ensures we initialize even if INITIAL_SESSION doesn't fire (which can happen in some SSR/client setups)
    const checkSession = async () => {
      try {
        console.log('[Auth] Checking session explicitly...')
        const start = Date.now()

        // Race getSession with a 2s timeout to detect hangs
        const sessionPromise = supabase.auth.getSession()
        const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('getSession timeout')), 4000))

        // @ts-ignore
        const { data: { session }, error } = await Promise.race([sessionPromise, timeoutPromise])

        console.log(`[Auth] getSession completed in ${Date.now() - start}ms`)

        if (error) {
          console.error('[Auth] Error checking session:', error)
          return
        }

        if (mounted) {
          if (session?.user) {
            console.log('[Auth] Manual session check found user:', session.user.id)
            setUser(session.user)
            // Only fetch profile if we haven't already (optimization)
            if (!userProfile) {
              await fetchUserProfile(session.user.id)
            }
          } else {
            console.log('[Auth] Manual session check: No session')
          }
          // Ensure loading is false if we're done checking
          setLoading(false)
          clearTimeout(safetyTimeout)
        }
      } catch (e) {
        console.error('[Auth] Exception checking session:', e)
        if (mounted) setLoading(false)
      }
    }

    checkSession()

    return () => {
      mounted = false
      clearTimeout(safetyTimeout)
      subscription.unsubscribe()
    }
  }, [])

  const signUp = async (email: string, password: string, displayName?: string) => {
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${location.origin}/auth/callback`,
          data: {
            display_name: displayName || '',
          },
        },
      })
      return { error }
    } catch (error) {
      return { error: error as Error }
    }
  }

  const signIn = async (email: string, password: string) => {
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      return { error }
    } catch (error) {
      return { error: error as Error }
    }
  }

  const signInWithGoogle = async () => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${location.origin}/auth/callback`,
        },
      })
      return { error }
    } catch (error) {
      return { error: error as Error }
    }
  }

  const resetPassword = async (email: string) => {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${location.origin}/auth/reset-password`,
      })
      return { error }
    } catch (error) {
      return { error: error as Error }
    }
  }

  const updatePassword = async (newPassword: string) => {
    try {
      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      })
      return { error }
    } catch (error) {
      return { error: error as Error }
    }
  }

  const signOut = async () => {
    await supabase.auth.signOut()
    setUser(null)
    setUserProfile(null)
    setOrganization(null)
    router.push('/')
  }

  const value = {
    user,
    userProfile,
    organization,
    loading,
    signUp,
    signIn,
    signInWithGoogle,
    resetPassword,
    updatePassword,
    signOut,
    refreshProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
