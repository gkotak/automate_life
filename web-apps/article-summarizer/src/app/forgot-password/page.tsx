'use client'

import { useState, FormEvent } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import Link from 'next/link'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const { resetPassword } = useAuth()

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
            {error && (
              <div className="bg-red-900/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {success && (
              <div className="bg-green-900/20 border border-green-500 text-green-400 px-4 py-3 rounded-lg">
                <p className="font-medium mb-1">Request submitted</p>
                <p className="text-sm">
                  If an account exists with <strong>{email}</strong>, you'll receive a password reset link shortly.
                </p>
              </div>
            )}

            {!success && (
              <>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-950 mb-2">
                    Email address
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded text-gray-950 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-green focus:border-transparent text-sm"
                    placeholder="Enter your email address"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  style={{ backgroundColor: '#077331' }}
                  onMouseEnter={(e) => !loading && (e.currentTarget.style.backgroundColor = '#065a27')}
                  onMouseLeave={(e) => !loading && (e.currentTarget.style.backgroundColor = '#077331')}
                >
                  {loading ? 'Sending...' : 'Submit'}
                </button>
              </>
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
