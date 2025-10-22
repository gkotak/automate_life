'use client'

import { useState, FormEvent, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'

export default function ResetPasswordPage() {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const { updatePassword, user, loading: authLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    // Give auth context time to load user session from cookie
    // Supabase sets the session cookie before redirecting here
    const timer = setTimeout(() => {
      setIsCheckingAuth(false)
      if (!user) {
        setError('Invalid or expired reset link. Please request a new password reset.')
      }
    }, 2000) // Wait 2 seconds for auth to initialize

    // If user loads immediately, stop checking
    if (user) {
      setIsCheckingAuth(false)
      clearTimeout(timer)
    }

    return () => clearTimeout(timer)
  }, [user])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)

    // Validate passwords match
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Validate password length
    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)

    const { error } = await updatePassword(newPassword)

    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      setSuccess(true)
      setLoading(false)
      // Redirect to home after 2 seconds
      setTimeout(() => router.push('/'), 2000)
    }
  }

  // Show loading while checking for authentication
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="border border-slate-200 rounded-2xl p-8">
          <div className="text-gray-950">Loading...</div>
        </div>
      </div>
    )
  }

  // If no user after checking, show error with option to request new link
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white px-8 py-8">
        <div className="w-full max-w-lg border border-slate-200 rounded-2xl py-12 px-6">
          <div className="text-center max-w-sm mx-auto">
            <h2 className="text-3xl font-semibold text-gray-950 mb-4">
              Reset Link Expired
            </h2>
            <div className="bg-red-900/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
              <p className="text-sm">
                This password reset link has expired or is invalid. Please request a new one.
              </p>
            </div>
            <button
              onClick={() => router.push('/forgot-password')}
              className="w-full py-2.5 px-4 text-white rounded-md transition-colors font-semibold text-sm"
              style={{ backgroundColor: '#077331' }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#065a27')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#077331')}
            >
              Request New Reset Link
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-8 py-8">
      <div className="w-full max-w-lg border border-slate-200 rounded-2xl py-12 px-6">
        <div className="mb-6 text-center">
          <h2 className="text-3xl font-semibold text-gray-950 mb-2">
            Set New Password
          </h2>
          <p className="text-base text-gray-950">
            Enter your new password below
          </p>
        </div>

        <div className="max-w-sm mx-auto">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-900/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {success && (
              <div className="bg-green-900/20 border border-green-500 text-green-400 px-4 py-3 rounded-lg">
                <p className="font-medium mb-1">Password updated successfully!</p>
                <p className="text-sm">Redirecting you to the home page...</p>
              </div>
            )}

            <div className="space-y-5">
              <div>
                <label htmlFor="new-password" className="block text-sm font-medium text-gray-950 mb-2">
                  New password
                </label>
                <input
                  id="new-password"
                  name="new-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded text-gray-950 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-green focus:border-transparent text-sm"
                  placeholder="Enter your password"
                />
                <p className="mt-1 text-xs text-slate-600">Must be at least 6 characters</p>
              </div>

              <div>
                <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-950 mb-2">
                  Confirm new password
                </label>
                <input
                  id="confirm-password"
                  name="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded text-gray-950 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-green focus:border-transparent text-sm"
                  placeholder="Enter your password"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || success}
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              style={{ backgroundColor: '#077331' }}
              onMouseEnter={(e) => !loading && !success && (e.currentTarget.style.backgroundColor = '#065a27')}
              onMouseLeave={(e) => !loading && !success && (e.currentTarget.style.backgroundColor = '#077331')}
            >
              {loading ? 'Updating password...' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
