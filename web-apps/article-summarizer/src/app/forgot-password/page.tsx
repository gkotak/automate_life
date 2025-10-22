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
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="text-3xl font-bold text-center text-white">
            Reset your password
          </h2>
          <p className="mt-2 text-center text-sm text-slate-400">
            Enter your email and we'll send you a link to reset your password
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
              <p className="font-medium mb-1">Request submitted</p>
              <p className="text-sm">
                If an account exists with <strong>{email}</strong>, you'll receive a password reset link shortly.
              </p>
            </div>
          )}

          {!success && (
            <>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
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
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-green focus:border-transparent"
                  placeholder="you@example.com"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg text-white bg-primary-green hover:bg-dark-green focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-green disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Sending...' : 'Send reset link'}
              </button>
            </>
          )}

          <div className="text-center">
            <Link
              href="/login"
              className="text-sm text-slate-400 hover:text-primary-green transition-colors"
            >
              Back to sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
