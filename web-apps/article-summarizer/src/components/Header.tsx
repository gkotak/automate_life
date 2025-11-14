'use client'

import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { usePathname } from 'next/navigation'
import { useState, useEffect, useRef } from 'react'

export default function Header() {
  const { user, loading, signOut } = useAuth()
  const pathname = usePathname()
  const [showNewDropdown, setShowNewDropdown] = useState(false)
  const [showProfileDropdown, setShowProfileDropdown] = useState(false)
  const newDropdownRef = useRef<HTMLDivElement>(null)
  const profileDropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (newDropdownRef.current && !newDropdownRef.current.contains(event.target as Node)) {
        setShowNewDropdown(false)
      }
      if (profileDropdownRef.current && !profileDropdownRef.current.contains(event.target as Node)) {
        setShowProfileDropdown(false)
      }
    }

    if (showNewDropdown || showProfileDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('touchstart', handleClickOutside as any, { passive: true })
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('touchstart', handleClickOutside as any, { passive: true } as any)
    }
  }, [showNewDropdown, showProfileDropdown])

  // Don't show header on login/signup/forgot-password/reset-password pages
  if (
    pathname === '/login' ||
    pathname === '/signup' ||
    pathname === '/forgot-password' ||
    pathname?.startsWith('/auth/reset-password')
  ) {
    return null
  }

  // Get initials from user
  const getInitials = () => {
    if (!user) return ''

    // If display name exists, use first letters of first and last name
    if (user.user_metadata?.display_name) {
      const names = user.user_metadata.display_name.trim().split(' ')
      if (names.length >= 2) {
        return `${names[0][0]}${names[names.length - 1][0]}`.toUpperCase()
      }
      // If only one name, use first two letters
      return user.user_metadata.display_name.substring(0, 2).toUpperCase()
    }

    // Fallback to first two letters of email
    if (user.email) {
      return user.email.substring(0, 2).toUpperCase()
    }

    return 'U'
  }

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          {/* Left side - Logo */}
          <Link href="/" className="transition-opacity hover:opacity-70">
            <img
              src="/particles_logo.svg"
              alt="Particles"
              className="h-10 w-auto"
            />
          </Link>

          {/* Right side - Action buttons */}
          <div className="flex items-center gap-3">
            {/* New Dropdown */}
            {user && (
              <div
                ref={newDropdownRef}
                className="relative"
              >
                <button
                  onClick={() => setShowNewDropdown(!showNewDropdown)}
                  className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-white hover:bg-gray-50 text-gray-700 rounded-lg transition-all duration-200 border border-gray-300 font-medium text-sm"
                >
                  <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <span>New</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* New Dropdown Menu */}
                {showNewDropdown && (
                  <div className="absolute left-0 mt-2 z-50">
                    <div className="w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1">
                      <Link
                        href="/new/article"
                        onClick={() => setShowNewDropdown(false)}
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          New Article
                        </div>
                      </Link>
                      <Link
                        href="/new/podcast-history"
                        onClick={() => setShowNewDropdown(false)}
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                          </svg>
                          Podcast Listening History
                        </div>
                      </Link>
                      <Link
                        href="/new/posts"
                        onClick={() => setShowNewDropdown(false)}
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          Check for Posts
                        </div>
                      </Link>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Chat Button */}
            {user && (
              <Link
                href="/chat"
                className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-white hover:bg-gray-50 text-gray-700 rounded-lg transition-all duration-200 border border-gray-300 font-medium text-sm"
              >
                <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="hidden sm:inline">Chat</span>
              </Link>
            )}

            {/* Auth Section */}
            {loading ? (
              <div className="text-gray-400 text-sm">Loading...</div>
            ) : user ? (
              <div
                ref={profileDropdownRef}
                className="relative"
                onMouseEnter={() => setShowProfileDropdown(true)}
                onMouseLeave={() => setShowProfileDropdown(false)}
              >
                {/* Avatar with Initials */}
                <button
                  onClick={() => setShowProfileDropdown(!showProfileDropdown)}
                  className="w-10 h-10 rounded-full bg-gray-200 text-gray-900 font-semibold text-sm flex items-center justify-center hover:bg-gray-300 transition-colors"
                >
                  {getInitials()}
                </button>

                {/* Dropdown on Hover - with padding bridge to prevent gap */}
                {showProfileDropdown && (
                  <div className="absolute right-0 pt-2 z-50">
                    <div className="w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1">
                      <div className="px-4 py-2 border-b border-gray-100">
                        <p className="text-sm font-medium text-gray-900">
                          {user.user_metadata?.display_name || 'User'}
                        </p>
                        <p className="text-xs text-gray-500 truncate">
                          {user.email}
                        </p>
                      </div>
                      <button
                        onClick={signOut}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-2"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        Sign out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Link
                href="/login"
                className="px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
