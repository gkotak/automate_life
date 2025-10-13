import { Quote } from '@/lib/supabase'
import { Quote as QuoteIcon, User } from 'lucide-react'

interface QuotesListProps {
  quotes: Quote[]
  onTimestampClick?: (seconds: number) => void
}

export default function QuotesList({ quotes, onTimestampClick }: QuotesListProps) {
  if (!quotes || quotes.length === 0) {
    return null
  }

  const handleTimestampClick = (seconds: number | null | undefined) => {
    if (seconds && onTimestampClick) {
      onTimestampClick(seconds)
    }
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
        💬 Notable Quotes
        <span className="text-sm font-normal text-gray-500">({quotes.length})</span>
      </h3>

      <div className="space-y-4">
        {quotes.map((quote, index) => (
          <div
            key={index}
            className="relative p-4 bg-gray-50 rounded-lg border border-gray-200"
          >
            <QuoteIcon className="absolute top-2 left-2 h-4 w-4 text-gray-400" />

            <div className="pl-6">
              <blockquote className="text-gray-800 italic leading-relaxed">
                "{quote.quote}"
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

                {quote.timestamp_seconds && (
                  <button
                    onClick={() => handleTimestampClick(quote.timestamp_seconds)}
                    className="text-xs px-2 py-1 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
                    title="Jump to quote"
                  >
                    {Math.floor(quote.timestamp_seconds / 60)}:{(quote.timestamp_seconds % 60).toString().padStart(2, '0')}
                  </button>
                )}
              </div>

              {quote.context && (
                <p className="text-xs text-gray-500 mt-2">{quote.context}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}