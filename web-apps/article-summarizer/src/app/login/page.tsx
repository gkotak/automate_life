'use client'

import { useState, FormEvent, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import BrandPanel from '@/components/BrandPanel'
import ErrorMessage from '@/components/ErrorMessage'
import AuthPrimaryButton from '@/components/auth/AuthPrimaryButton'
import AuthInput from '@/components/auth/AuthInput'
import GoogleSignInButton from '@/components/auth/GoogleSignInButton'
import AuthDivider from '@/components/auth/AuthDivider'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const { user, signIn, signInWithGoogle } = useAuth()
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
    setLoading(true)

    const { error } = await signIn(email, password)

    if (error) {
      setError(error.message)
      setLoading(false)
    } else {
      router.push('/')
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
      <div className="border border-slate-200 rounded-2xl p-6 sm:p-12 flex gap-8 w-full max-w-[876px]" style={{ minHeight: '654px' }}>
        {/* Left column - Form */}
        <div className="flex-1 w-full sm:w-[364px]">
          <div className="mb-8">
            <h2 className="text-3xl font-semibold text-gray-950 mb-2 text-center">
              Welcome
            </h2>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
          {error && <ErrorMessage message={error} />}

          <div className="space-y-5">
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

            <div>
              <AuthInput
                id="password"
                name="password"
                type="password"
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
              />
              <div className="mt-2 text-right">
                <Link
                  href="/forgot-password"
                  className="text-sm text-primary-green hover:text-dark-green transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
            </div>
          </div>

          <AuthPrimaryButton type="submit" loading={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </AuthPrimaryButton>

          <div className="text-center">
            <span className="text-sm text-gray-600">Don't have an account? </span>
            <Link href="/signup" className="text-sm text-primary-green hover:text-dark-green font-medium">
              Sign Up
            </Link>
          </div>

          <AuthDivider text="or login with" />

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
