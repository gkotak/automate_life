'use client'

import { useState, useRef, useEffect } from 'react'
import { Share2, Link as LinkIcon, Clock } from 'lucide-react'

interface ShareButtonProps {
  articleId: string
  getCurrentTime?: () => number
  className?: string
}

export default function ShareButton({ articleId, getCurrentTime, className = '' }: ShareButtonProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const [copySuccess, setCopySuccess] = useState<string | null>(null)
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
      document.addEventListener('touchstart', handleClickOutside as any, { passive: true })
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('touchstart', handleClickOutside as any, { passive: true } as any)
    }
  }, [showDropdown])

  const getShareUrl = (withTimestamp: boolean = false) => {
    const baseUrl = `${window.location.origin}/article/${articleId}`
    if (withTimestamp && getCurrentTime) {
      const currentTime = Math.floor(getCurrentTime())
      return `${baseUrl}?timestamp=${currentTime}`
    }
    return baseUrl
  }

  const copyToClipboard = async (url: string, type: string) => {
    try {
      await navigator.clipboard.writeText(url)
      setCopySuccess(type)
      setTimeout(() => {
        setCopySuccess(null)
        setShowDropdown(false)
      }, 1500)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleShare = (withTimestamp: boolean) => {
    const url = getShareUrl(withTimestamp)
    const type = withTimestamp ? 'timestamp' : 'link'
    copyToClipboard(url, type)
  }

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-3 py-2 bg-white hover:bg-gray-50 text-gray-700 rounded-lg transition-all duration-200 border border-gray-300 font-medium text-sm"
        title="Share"
      >
        <Share2 className="w-4 h-4" />
        <span>Share</span>
      </button>

      {/* Dropdown Menu */}
      {showDropdown && (
        <div className="absolute left-0 mt-2 z-50">
          <div className="w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1">
            {/* Share Link */}
            <button
              onClick={() => handleShare(false)}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <LinkIcon className="w-4 h-4" />
                <div>
                  <div className="font-medium">Share Link</div>
                  <div className="text-xs text-gray-500">Copy article URL</div>
                </div>
              </div>
            </button>

            {/* Share at Current Moment */}
            {getCurrentTime && (
              <button
                onClick={() => handleShare(true)}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Clock className="w-4 h-4" />
                  <div>
                    <div className="font-medium">Share at Current Moment</div>
                    <div className="text-xs text-gray-500">Copy link with timestamp</div>
                  </div>
                </div>
              </button>
            )}

            {/* Success Message */}
            {copySuccess && (
              <div className="px-4 py-2 text-xs text-green-600 bg-green-50 border-t border-gray-200">
                {copySuccess === 'timestamp' ? 'Link with timestamp copied!' : 'Link copied!'}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
