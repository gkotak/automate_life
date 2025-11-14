'use client'

import { useState, FormEvent, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import BrandPanel from '@/components/BrandPanel'
import ErrorMessage from '@/components/ErrorMessage'
import SuccessMessage from '@/components/SuccessMessage'
import AuthPrimaryButton from '@/components/auth/AuthPrimaryButton'
import AuthInput from '@/components/auth/AuthInput'
import GoogleSignInButton from '@/components/auth/GoogleSignInButton'
import AuthDivider from '@/components/auth/AuthDivider'

export default function SignupPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const { user, signUp, signInWithGoogle } = useAuth()
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

    // Validate passwords match
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Validate password length
    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)

    const { error } = await signUp(email, password, name)

    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      setSuccess(true)
      setLoading(false)
      // Redirect after 2 seconds
      setTimeout(() => router.push('/'), 2000)
    }
  }

  const handleGoogleSignIn = async () => {
    setError(null)
    const { error } = await signInWithGoogle()
    if (error) {
      setError(error.message)
    }
    // Note: User will be redirected to Google, so no need to handle success here
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-4 sm:px-8 py-8">
      <div className="border border-slate-200 rounded-2xl p-6 sm:p-12 flex gap-8 w-full max-w-[876px]" style={{ minHeight: '720px' }}>
        {/* Left column - Form */}
        <div className="flex-1 w-full sm:w-[364px]">
          <div className="mb-8">
            <h2 className="text-3xl font-semibold text-gray-950 mb-2 text-center">
              Create your account
            </h2>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
          {error && <ErrorMessage message={error} />}

          {success && (
            <SuccessMessage
              title="Account created!"
              message="Check your email to confirm your account. Redirecting..."
            />
          )}

          <div className="space-y-5">
            <AuthInput
              id="name"
              name="name"
              type="text"
              label="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoComplete="name"
              placeholder="John Doe"
            />

            <AuthInput
              id="email"
              name="email"
              type="email"
              label="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="name@email.com"
            />

            <AuthInput
              id="password"
              name="password"
              type="password"
              label="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
              placeholder="••••••••"
              helperText="Must be at least 6 characters"
            />

            <AuthInput
              id="confirm-password"
              name="confirm-password"
              type="password"
              label="Confirm password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
              placeholder="••••••••"
            />
          </div>

          <AuthPrimaryButton type="submit" disabled={success} loading={loading}>
            {loading ? 'Creating account...' : 'Sign Up'}
          </AuthPrimaryButton>

          <div className="text-center">
            <span className="text-sm text-gray-600">Already have an account? </span>
            <Link href="/login" className="text-sm text-primary-green hover:text-dark-green font-medium">
              Sign In
            </Link>
          </div>

          <AuthDivider text="or signup with" />

          <GoogleSignInButton onClick={handleGoogleSignIn} text="Google" />
        </form>
        </div>

        {/* Right column - Brand Panel (hidden on mobile) */}
        <div className="hidden lg:flex flex-1" style={{ width: '364px' }}>
          <BrandPanel />
        </div>
      </div>
    </div>
  )
}
