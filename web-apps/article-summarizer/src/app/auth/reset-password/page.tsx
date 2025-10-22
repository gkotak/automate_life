'use client'

import { useState, FormEvent, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import SuccessMessage from '@/components/SuccessMessage'
import ErrorMessage from '@/components/ErrorMessage'
import AuthPrimaryButton from '@/components/auth/AuthPrimaryButton'
import AuthInput from '@/components/auth/AuthInput'

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

  // If no user after checking, show error
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white px-8 py-8">
        <div className="w-full max-w-lg border border-slate-200 rounded-2xl py-12 px-6">
          <div className="text-center max-w-sm mx-auto">
            <h2 className="text-3xl font-semibold text-gray-950 mb-6">
              Reset Link Expired
            </h2>
            <ErrorMessage message="This password reset link has expired or is invalid. Please go to the forgot password page to request a new one." />
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
            {error && <ErrorMessage message={error} />}

            {success ? (
              <SuccessMessage
                title="Password updated!"
                message="Your password has been successfully updated. Redirecting you to the home page..."
              />
            ) : (
              <>
                <div className="space-y-5">
                  <AuthInput
                    id="new-password"
                    name="new-password"
                    type="password"
                    label="New password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    placeholder="Enter your password"
                    helperText="Must be at least 6 characters"
                  />

                  <AuthInput
                    id="confirm-password"
                    name="confirm-password"
                    type="password"
                    label="Confirm new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    placeholder="Enter your password"
                  />
                </div>

                <AuthPrimaryButton type="submit" disabled={success} loading={loading}>
                  {loading ? 'Updating password...' : 'Update Password'}
                </AuthPrimaryButton>
              </>
            )}
          </form>
        </div>
      </div>
    </div>
  )
}
