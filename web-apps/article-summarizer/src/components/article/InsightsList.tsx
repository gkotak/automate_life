import { Insight } from '@/lib/supabase'
import { Play, Tag } from 'lucide-react'
import HighlightedText from '../HighlightedText'
import { useState, useEffect } from 'react'

interface ThemedInsight {
  id: number
  insight_text: string
  timestamp_seconds: number | null
  time_formatted: string | null
  theme_name: string
  theme_id: number
}

interface GroupedThemedInsights {
  theme_id: number
  theme_name: string
  insights: ThemedInsight[]
}

interface InsightsListProps {
  insights: Insight[]
  onTimestampClick?: (seconds: number) => void
  searchQuery?: string
  clickedTimestamp?: number | null
  articleId?: number
  isPrivate?: boolean
}

export default function InsightsList({
  insights,
  onTimestampClick,
  searchQuery,
  clickedTimestamp,
  articleId,
  isPrivate
}: InsightsListProps) {
  const [isCollapsed, setIsCollapsed] = useState(true)
  const [themedInsights, setThemedInsights] = useState<GroupedThemedInsights[]>([])
  const [loadingThemed, setLoadingThemed] = useState(false)

  // Fetch themed insights for private articles
  useEffect(() => {
    if (isPrivate && articleId) {
      fetchThemedInsights()
    }
  }, [articleId, isPrivate])

  const fetchThemedInsights = async () => {
    try {
      setLoadingThemed(true)
      const response = await fetch(`/api/private-articles/${articleId}/themed-insights`)
      if (response.ok) {
        const data = await response.json()
        setThemedInsights(data.grouped_insights || [])
      }
    } catch (error) {
      console.error('Error fetching themed insights:', error)
    } finally {
      setLoadingThemed(false)
    }
  }

  const totalCount = (insights?.length || 0) + themedInsights.reduce((acc, g) => acc + g.insights.length, 0)

  if (totalCount === 0) {
    return null
  }

  const handleTimestampClick = (seconds: number | null) => {
    if (seconds && onTimestampClick) {
      onTimestampClick(seconds)
    }
  }

  return (
    <div className="space-y-4">
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="flex items-center justify-between w-full text-left group"
      >
        <h3 className="text-lg font-semibold text-[#030712] flex items-center gap-2">
          💡 Key Insights
          <span className="text-sm font-normal text-[#475569]">({totalCount})</span>
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
        <div className="space-y-6">
          {/* Themed Insights subsections (shown first) */}
          {themedInsights.map((group) => (
            <div key={group.theme_id} className="space-y-3">
              <h4 className="text-sm font-semibold text-[#475569] flex items-center gap-2 uppercase tracking-wide">
                <Tag className="h-4 w-4" />
                {group.theme_name}
                <span className="font-normal">({group.insights.length})</span>
              </h4>
              <div className="space-y-3">
                {group.insights.map((insight) => (
                  <div
                    key={insight.id}
                    className="bg-green-50 rounded-lg border border-[#e2e8f0] overflow-hidden"
                  >
                    <div className="flex items-start gap-3 p-3">
                      <div className="flex-1">
                        <HighlightedText
                          text={insight.insight_text}
                          query={searchQuery}
                          className="text-[#030712] leading-relaxed"
                        />
                      </div>

                      {insight.timestamp_seconds && insight.time_formatted && (
                        <button
                          onClick={() => handleTimestampClick(insight.timestamp_seconds)}
                          className="flex items-center gap-1 px-2 py-1 bg-[#077331] text-white rounded text-sm hover:bg-[#055a24] transition-colors shrink-0"
                          title={`Jump to ${insight.time_formatted}`}
                        >
                          <Play className="h-3 w-3" />
                          {insight.time_formatted}
                        </button>
                      )}
                    </div>

                    {insight.timestamp_seconds && clickedTimestamp === insight.timestamp_seconds && (
                      <div className="text-xs text-blue-600 italic px-3 py-2 border-t border-blue-200 bg-blue-50">
                        We've moved the video to this point, however, you'll need to scroll up and hit play.
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* General Insights subsection */}
          {insights && insights.length > 0 && (
            <div className="space-y-3">
              {themedInsights.length > 0 && (
                <h4 className="text-sm font-semibold text-[#475569] flex items-center gap-2 uppercase tracking-wide">
                  General Insights
                  <span className="font-normal">({insights.length})</span>
                </h4>
              )}
              <div className="space-y-3">
                {insights.map((insight, index) => (
                  <div
                    key={index}
                    className="bg-green-50 rounded-lg border border-[#e2e8f0] overflow-hidden"
                  >
                    <div className="flex items-start gap-3 p-3">
                      <div className="flex-1">
                        <HighlightedText
                          text={insight.insight}
                          query={searchQuery}
                          className="text-[#030712] leading-relaxed"
                        />
                      </div>

                      {insight.timestamp_seconds && insight.time_formatted && (
                        <button
                          onClick={() => handleTimestampClick(insight.timestamp_seconds)}
                          className="flex items-center gap-1 px-2 py-1 bg-[#077331] text-white rounded text-sm hover:bg-[#055a24] transition-colors shrink-0"
                          title={`Jump to ${insight.time_formatted}`}
                        >
                          <Play className="h-3 w-3" />
                          {insight.time_formatted}
                        </button>
                      )}
                    </div>

                    {insight.timestamp_seconds && clickedTimestamp === insight.timestamp_seconds && (
                      <div className="text-xs text-blue-600 italic px-3 py-2 border-t border-blue-200 bg-blue-50">
                        We've moved the video to this point, however, you'll need to scroll up and hit play.
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}