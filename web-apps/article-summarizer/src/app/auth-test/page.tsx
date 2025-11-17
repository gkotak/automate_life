'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { supabase } from '@/lib/supabase'

export default function AuthTestPage() {
  const { user, userProfile, organization, loading } = useAuth()
  const [logs, setLogs] = useState<string[]>([])
  const [sessionInfo, setSessionInfo] = useState<any>(null)

  const addLog = (message: string) => {
    const timestamp = new Date().toISOString().split('T')[1].slice(0, -1)
    setLogs(prev => [...prev, `[${timestamp}] ${message}`])
  }

  useEffect(() => {
    addLog('Component mounted')
    addLog(`Loading: ${loading}`)
    addLog(`User: ${user ? user.id : 'null'}`)
    addLog(`UserProfile: ${userProfile ? 'loaded' : 'null'}`)
    addLog(`Organization: ${organization ? organization.name : 'null'}`)

    // Check raw Supabase session
    const checkSession = async () => {
      addLog('🔍 Calling supabase.auth.getSession()...')
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        addLog(`Supabase getSession - Session: ${session ? 'exists' : 'null'}, Error: ${error ? error.message : 'none'}`)
        setSessionInfo(session)

        if (session) {
          addLog(`Session access token: ${session.access_token.substring(0, 20)}...`)
          addLog(`Session expires at: ${new Date(session.expires_at! * 1000).toISOString()}`)
        }
      } catch (err: any) {
        addLog(`❌ Exception in checkSession: ${err.message}`)
      }
    }
    checkSession()

    // Listen to auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      addLog(`Auth state changed: ${event}`)
      if (session) {
        addLog(`Session user: ${session.user.id}`)
      }
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  useEffect(() => {
    if (user) {
      addLog(`✅ User loaded: ${user.id}`)
      addLog(`   Email: ${user.email}`)
    }
  }, [user])

  useEffect(() => {
    if (userProfile) {
      addLog(`✅ UserProfile loaded: role=${userProfile.role}, org_id=${userProfile.organization_id}`)
    }
  }, [userProfile])

  useEffect(() => {
    if (organization) {
      addLog(`✅ Organization loaded: ${organization.name} (${organization.id})`)
    }
  }, [organization])

  const testUserQuery = async () => {
    addLog('🔍 Testing direct user query...')
    const { data: session } = await supabase.auth.getSession()
    if (!session.session?.user) {
      addLog('❌ No session found')
      return
    }

    const userId = session.session.user.id
    addLog(`User ID from session: ${userId}`)

    const { data, error } = await supabase
      .from('users')
      .select('*')
      .eq('id', userId)
      .single()

    if (error) {
      addLog(`❌ Error fetching user profile: ${error.message}`)
      addLog(`   Code: ${error.code}`)
      addLog(`   Details: ${JSON.stringify(error.details)}`)
      addLog(`   Hint: ${error.hint}`)
    } else {
      addLog(`✅ User profile fetched: ${JSON.stringify(data)}`)
    }
  }

  const testOrgQuery = async () => {
    addLog('🔍 Testing organization query...')
    if (!userProfile?.organization_id) {
      addLog('❌ No organization_id in userProfile')
      return
    }

    const { data, error } = await supabase
      .from('organizations')
      .select('*')
      .eq('id', userProfile.organization_id)
      .single()

    if (error) {
      addLog(`❌ Error fetching organization: ${error.message}`)
    } else {
      addLog(`✅ Organization fetched: ${JSON.stringify(data)}`)
    }
  }

  const testRLSPolicies = async () => {
    addLog('🔍 Testing RLS policies...')

    // Test users table
    const { data: usersData, error: usersError } = await supabase
      .from('users')
      .select('*')
      .limit(1)

    addLog(`Users table: ${usersError ? '❌ ' + usersError.message : '✅ ' + usersData?.length + ' rows'}`)

    // Test organizations table
    const { data: orgsData, error: orgsError } = await supabase
      .from('organizations')
      .select('*')
      .limit(1)

    addLog(`Organizations table: ${orgsError ? '❌ ' + orgsError.message : '✅ ' + orgsData?.length + ' rows'}`)

    // Test articles table
    const { data: articlesData, error: articlesError } = await supabase
      .from('articles')
      .select('*')
      .limit(1)

    addLog(`Articles table: ${articlesError ? '❌ ' + articlesError.message : '✅ ' + articlesData?.length + ' rows'}`)
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Authentication Debug Page</h1>

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className={`p-4 rounded-lg ${loading ? 'bg-yellow-100' : 'bg-green-100'}`}>
            <div className="text-sm text-gray-600">Auth Loading</div>
            <div className="text-2xl font-bold">{loading ? 'Yes ⏳' : 'No ✅'}</div>
          </div>

          <div className={`p-4 rounded-lg ${user ? 'bg-green-100' : 'bg-red-100'}`}>
            <div className="text-sm text-gray-600">User</div>
            <div className="text-2xl font-bold">{user ? '✅ Loaded' : '❌ Null'}</div>
            {user && <div className="text-xs mt-1 truncate">{user.email}</div>}
          </div>

          <div className={`p-4 rounded-lg ${userProfile ? 'bg-green-100' : 'bg-red-100'}`}>
            <div className="text-sm text-gray-600">User Profile</div>
            <div className="text-2xl font-bold">{userProfile ? '✅ Loaded' : '❌ Null'}</div>
            {userProfile && <div className="text-xs mt-1">{userProfile.role}</div>}
          </div>

          <div className={`p-4 rounded-lg ${organization ? 'bg-green-100' : 'bg-red-100'}`}>
            <div className="text-sm text-gray-600">Organization</div>
            <div className="text-2xl font-bold">{organization ? '✅ Loaded' : '❌ Null'}</div>
            {organization && <div className="text-xs mt-1">{organization.name}</div>}
          </div>

          <div className={`p-4 rounded-lg ${sessionInfo ? 'bg-green-100' : 'bg-red-100'}`}>
            <div className="text-sm text-gray-600">Supabase Session</div>
            <div className="text-2xl font-bold">{sessionInfo ? '✅ Active' : '❌ None'}</div>
          </div>
        </div>

        {/* Test Buttons */}
        <div className="mb-8 flex flex-wrap gap-4">
          {!user && (
            <a
              href="/auth/signin"
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-bold"
            >
              ➜ Go to Sign In Page
            </a>
          )}
          <button
            onClick={testUserQuery}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Test User Query
          </button>
          <button
            onClick={testOrgQuery}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            disabled={!userProfile}
          >
            Test Org Query
          </button>
          <button
            onClick={testRLSPolicies}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Test RLS Policies
          </button>
        </div>

        {/* Session Info */}
        {sessionInfo && (
          <div className="mb-8 p-4 bg-white rounded-lg shadow">
            <h2 className="font-bold mb-2">Session Info</h2>
            <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-60">
              {JSON.stringify(sessionInfo, null, 2)}
            </pre>
          </div>
        )}

        {/* User Data */}
        {user && (
          <div className="mb-8 p-4 bg-white rounded-lg shadow">
            <h2 className="font-bold mb-2">User Data</h2>
            <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40">
              {JSON.stringify(user, null, 2)}
            </pre>
          </div>
        )}

        {/* User Profile Data */}
        {userProfile && (
          <div className="mb-8 p-4 bg-white rounded-lg shadow">
            <h2 className="font-bold mb-2">User Profile Data</h2>
            <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40">
              {JSON.stringify(userProfile, null, 2)}
            </pre>
          </div>
        )}

        {/* Organization Data */}
        {organization && (
          <div className="mb-8 p-4 bg-white rounded-lg shadow">
            <h2 className="font-bold mb-2">Organization Data</h2>
            <pre className="text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40">
              {JSON.stringify(organization, null, 2)}
            </pre>
          </div>
        )}

        {/* Logs */}
        <div className="p-4 bg-white rounded-lg shadow">
          <h2 className="font-bold mb-2">Event Log</h2>
          <div className="bg-black text-green-400 p-4 rounded font-mono text-xs h-96 overflow-auto">
            {logs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
