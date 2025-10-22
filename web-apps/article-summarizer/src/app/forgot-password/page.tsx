'use client'

import { useState, FormEvent, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import SuccessMessage from '@/components/SuccessMessage'
import ErrorMessage from '@/components/ErrorMessage'
import AuthPrimaryButton from '@/components/auth/AuthPrimaryButton'
import AuthInput from '@/components/auth/AuthInput'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const { user, resetPassword } = useAuth()
  const router = useRouter()

  // Redirect if already authenticated
  useEffect(() => {
    if (user) {
      router.push('/')
    }
  }, [user, router])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)
    setLoading(true)

    const { error } = await resetPassword(email)

    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      setSuccess(true)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-8 py-8">
      <div className="w-full max-w-lg border border-slate-200 rounded-2xl py-12 px-6">
        <div className="mb-6 text-center">
          <h2 className="text-3xl font-semibold text-gray-950 mb-2">
            Forgot Password
          </h2>
          <p className="text-base text-gray-950">
            No worries! Enter your email address below, and we'll send you a link to reset your password.
          </p>
        </div>

        <div className="max-w-sm mx-auto">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && <ErrorMessage message={error} />}

            {!success ? (
              <>
                <AuthInput
                  id="email"
                  name="email"
                  type="email"
                  label="Email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  placeholder="Enter your email address"
                />

                <AuthPrimaryButton type="submit" loading={loading}>
                  {loading ? 'Sending...' : 'Submit'}
                </AuthPrimaryButton>
              </>
            ) : (
              <SuccessMessage
                title="Check your email"
                message={`If an account exists with ${email}, you'll receive a password reset link shortly.`}
              />
            )}

            <div className="text-center">
              <Link
                href="/login"
                className="text-sm text-gray-600 hover:text-primary-green transition-colors"
              >
                Back to sign in
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
