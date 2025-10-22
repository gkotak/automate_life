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
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-white">Loading...</div>
      </div>
    )
  }

  // If no user after checking, show error with option to request new link
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-white mb-4">
              Reset Link Expired
            </h2>
            <div className="bg-red-900/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-6">
              <p className="text-sm">
                This password reset link has expired or is invalid. Please request a new one.
              </p>
            </div>
            <button
              onClick={() => router.push('/forgot-password')}
              className="w-full py-3 px-4 bg-primary-green hover:bg-dark-green text-white rounded-lg transition-colors"
            >
              Request New Reset Link
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="text-3xl font-bold text-center text-white">
            Set new password
          </h2>
          <p className="mt-2 text-center text-sm text-slate-400">
            Enter your new password below
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
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

          <div className="space-y-4">
            <div>
              <label htmlFor="new-password" className="block text-sm font-medium text-slate-300 mb-2">
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
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-green focus:border-transparent"
                placeholder="••••••••"
              />
              <p className="mt-1 text-xs text-slate-500">Must be at least 6 characters</p>
            </div>

            <div>
              <label htmlFor="confirm-password" className="block text-sm font-medium text-slate-300 mb-2">
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
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-green focus:border-transparent"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || success}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg text-white bg-primary-green hover:bg-dark-green focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-green disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Updating password...' : 'Update password'}
          </button>
        </form>
      </div>
    </div>
  )
}
