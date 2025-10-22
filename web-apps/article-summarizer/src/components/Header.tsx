'use client'

import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { usePathname } from 'next/navigation'
import { useState, useEffect, useRef } from 'react'

export default function Header() {
  const { user, loading, signOut } = useAuth()
  const pathname = usePathname()
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }

    if (showDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('touchstart', handleClickOutside as any)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('touchstart', handleClickOutside as any)
    }
  }, [showDropdown])

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
          {/* Left side - Logo, Title, and Tagline */}
          <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            {/* Logo Icon */}
            <div className="relative flex-shrink-0">
              <div className="absolute inset-0 bg-gradient-to-br from-[#077331] to-[#055a24] opacity-20 blur-lg rounded-full"></div>
              <div className="relative bg-gradient-to-br from-[#077331] to-[#055a24] p-2 rounded-xl shadow-lg">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
            {/* Logo Text and Tagline */}
            <div className="flex flex-col">
              <h1 className="text-lg sm:text-2xl font-bold bg-gradient-to-r from-[#077331] to-[#055a24] bg-clip-text text-transparent leading-tight">
                Article Summarizer
              </h1>
              <p className="hidden sm:block text-sm text-gray-600 mt-0.5">
                Transform articles into actionable insights with AI-powered analysis
              </p>
            </div>
          </Link>

          {/* Right side - Action buttons */}
          <div className="flex items-center gap-3">
            {/* AI Chat Button */}
            <Link
              href="/chat"
              className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-[#077331] hover:bg-[#055a24] text-white rounded-lg transition-all duration-200 shadow-md hover:shadow-lg font-medium text-sm"
            >
              <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <span className="hidden sm:inline">AI Chat</span>
            </Link>

            {/* Auth Section */}
            {loading ? (
              <div className="text-gray-400 text-sm">Loading...</div>
            ) : user ? (
              <div
                ref={dropdownRef}
                className="relative"
                onMouseEnter={() => setShowDropdown(true)}
                onMouseLeave={() => setShowDropdown(false)}
              >
                {/* Avatar with Initials */}
                <button
                  onClick={() => setShowDropdown(!showDropdown)}
                  className="w-10 h-10 rounded-full bg-gray-200 text-gray-900 font-semibold text-sm flex items-center justify-center hover:bg-gray-300 transition-colors"
                >
                  {getInitials()}
                </button>

                {/* Dropdown on Hover - with padding bridge to prevent gap */}
                {showDropdown && (
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
