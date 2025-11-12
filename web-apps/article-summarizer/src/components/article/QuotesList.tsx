import { Quote } from '@/lib/supabase'
import { Quote as QuoteIcon, User } from 'lucide-react'
import HighlightedText from '../HighlightedText'
import { useState } from 'react'

interface QuotesListProps {
  quotes: Quote[]
  onTimestampClick?: (seconds: number) => void
  searchQuery?: string
  clickedTimestamp?: number | null
}

export default function QuotesList({ quotes, onTimestampClick, searchQuery, clickedTimestamp }: QuotesListProps) {
  const [isCollapsed, setIsCollapsed] = useState(false) // Expanded by default

  if (!quotes || quotes.length === 0) {
    return null
  }

  const handleTimestampClick = (seconds: number | null | undefined) => {
    console.log('Quote timestamp clicked:', seconds)
    if (seconds !== null && seconds !== undefined && onTimestampClick) {
      console.log('Calling onTimestampClick with:', seconds)
      onTimestampClick(seconds)
    } else {
      console.warn('Cannot jump to timestamp:', { seconds, hasCallback: !!onTimestampClick })
    }
  }

  return (
    <div className="space-y-4">
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="flex items-center justify-between w-full text-left group"
      >
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          💬 Notable Quotes
          <span className="text-sm font-normal text-gray-500">({quotes.length})</span>
        </h3>
        <svg
          className={`w-5 h-5 text-gray-500 transition-transform ${isCollapsed ? '' : 'rotate-180'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {!isCollapsed && (
        <div className="space-y-4">
        {quotes.map((quote, index) => (
          <div
            key={index}
            className="relative p-4 bg-gray-50 rounded-lg border border-gray-200"
          >
            <QuoteIcon className="absolute top-2 left-2 h-4 w-4 text-gray-400" />

            <div className="pl-6">
              <blockquote className="text-gray-800 italic leading-relaxed">
                "<HighlightedText text={quote.quote} query={searchQuery} />"
              </blockquote>

              <div className="flex items-center justify-between mt-3">
                <div className="flex items-center gap-2">
                  {quote.speaker && (
                    <div className="flex items-center gap-1 text-sm text-gray-600">
                      <User className="h-3 w-3" />
                      {quote.speaker}
                    </div>
                  )}
                </div>

                {quote.timestamp_seconds !== null && quote.timestamp_seconds !== undefined && (
                  <button
                    onClick={() => handleTimestampClick(quote.timestamp_seconds!)}
                    className="text-xs px-2 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors cursor-pointer"
                    title="Jump to this moment in the video"
                  >
                    {Math.floor(quote.timestamp_seconds! / 60)}:{String(Math.floor(quote.timestamp_seconds! % 60)).padStart(2, '0')}
                  </button>
                )}
              </div>

              {quote.context && (
                <p className="text-xs text-gray-500 mt-2">
                  <HighlightedText text={quote.context} query={searchQuery} />
                </p>
              )}

              {quote.timestamp_seconds !== null && quote.timestamp_seconds !== undefined && clickedTimestamp === quote.timestamp_seconds && (
                <div className="text-xs text-blue-600 italic mt-2 pt-2 border-t border-blue-200 bg-blue-50 -mx-4 -mb-4 px-4 py-2 rounded-b-lg">
                  We've moved the video to this point, however, you'll need to scroll up and hit play.
                </div>
              )}
            </div>
          </div>
        ))}
        </div>
      )}
    </div>
  )
}