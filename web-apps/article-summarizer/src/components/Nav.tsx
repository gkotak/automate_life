'use client'

import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { usePathname } from 'next/navigation'

export default function Nav() {
  const { user, loading, signOut } = useAuth()
  const pathname = usePathname()

  // Don't show nav on login/signup pages
  if (pathname === '/login' || pathname === '/signup') {
    return null
  }

  return (
    <nav className="bg-slate-900 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-8">
            <Link href="/" className="text-xl font-bold text-white hover:text-primary-green transition-colors">
              Article Summarizer
            </Link>
            {user && (
              <Link
                href="/admin"
                className="text-slate-300 hover:text-white transition-colors"
              >
                Add Article
              </Link>
            )}
          </div>

          <div className="flex items-center space-x-4">
            {loading ? (
              <div className="text-slate-400">Loading...</div>
            ) : user ? (
              <>
                <span className="text-slate-400 text-sm">{user.email}</span>
                <button
                  onClick={signOut}
                  className="px-4 py-2 text-sm font-medium text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
                >
                  Sign in
                </Link>
                <Link
                  href="/signup"
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-green hover:bg-dark-green rounded-lg transition-colors"
                >
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
