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

  // Fetch user profile and organization
  const fetchUserProfile = async (userId: string) => {
    try {
      // Fetch user profile with organization data in a single optimized query
      const { data: profileData, error: profileError } = await supabase
        .from('users')
        .select('id, organization_id, role, display_name, created_at, updated_at, organization:organizations(id, name, created_at, updated_at)')
        .eq('id', userId)
        .single()

      if (profileError) {
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
    // Check active session (original approach that was working)
    const checkSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        const currentUser = session?.user ?? null
        setUser(currentUser)

        // Fetch profile if user exists
        if (currentUser) {
          await fetchUserProfile(currentUser.id)
        }
      } catch (error) {
        console.error('Error in checkSession:', error)
      } finally {
        // Always set loading to false, even if there's an error
        setLoading(false)
      }
    }

    checkSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      console.log('Auth event:', _event)
      const currentUser = session?.user ?? null
      setUser(currentUser)

      // Fetch profile when user signs in
      if (currentUser && _event === 'SIGNED_IN') {
        await fetchUserProfile(currentUser.id)
      } else if (_event === 'SIGNED_OUT') {
        setUserProfile(null)
        setOrganization(null)
      }
    })

    return () => subscription.unsubscribe()
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
