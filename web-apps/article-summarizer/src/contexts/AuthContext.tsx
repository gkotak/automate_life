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
        .select('id, organization_id, role, display_name, created_at, updated_at, organization:organizations(id, name, metadata, created_at, updated_at)')
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

    // Safety timeout - backup only, should not fire in normal operation
    // Increased to 10s since we're no longer racing multiple auth checks
    const safetyTimeout = setTimeout(() => {
      if (loading && mounted) {
        console.warn('[Auth] Safety timeout triggered - this should not happen in normal operation')
        setLoading(false)
      }
    }, 10000)

    // Single listener pattern - this is Supabase's recommended approach
    // IMPORTANT: Do NOT await Supabase calls inside this callback - it causes deadlocks!
    // See: https://github.com/supabase/auth-js/issues/762
    // Use setTimeout to dispatch async operations outside the callback
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      console.log('[Auth] Auth event:', event, { hasSession: !!session })
      if (!mounted) return

      const currentUser = session?.user ?? null
      setUser(currentUser)

      if (event === 'INITIAL_SESSION') {
        // Page load - fetch profile if user exists
        // Use setTimeout to avoid deadlock - profile fetch must happen outside this callback
        if (currentUser) {
          console.log('[Auth] Initial session - scheduling profile fetch...')
          setTimeout(() => {
            if (mounted) {
              fetchUserProfile(currentUser.id).finally(() => {
                if (mounted) {
                  setLoading(false)
                  clearTimeout(safetyTimeout)
                }
              })
            }
          }, 0)
        } else {
          // No user - just stop loading
          setLoading(false)
          clearTimeout(safetyTimeout)
        }
      } else if (event === 'SIGNED_IN') {
        // User just signed in - fetch profile outside callback
        console.log('[Auth] Signed in - scheduling profile fetch...')
        setTimeout(() => {
          if (mounted && currentUser) {
            fetchUserProfile(currentUser.id).finally(() => {
              if (mounted) setLoading(false)
            })
          }
        }, 0)
      } else if (event === 'SIGNED_OUT') {
        setUserProfile(null)
        setOrganization(null)
        setLoading(false)
      } else if (event === 'TOKEN_REFRESHED') {
        // Token was refreshed by middleware or automatic refresh
        console.log('[Auth] Token refreshed')
      }
    })

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
