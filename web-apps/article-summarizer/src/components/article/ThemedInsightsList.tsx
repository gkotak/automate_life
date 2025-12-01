'use client'

import { useState, useEffect } from 'react'
import { Play, Tag, ChevronDown } from 'lucide-react'
import HighlightedText from '../HighlightedText'

interface ThemedInsight {
  id: number
  insight_text: string
  timestamp_seconds: number | null
  time_formatted: string | null
  theme_name: string
  theme_id: number
}

interface ThemedInsightsListProps {
  articleId: number
  onTimestampClick?: (seconds: number) => void
  searchQuery?: string
  clickedTimestamp?: number | null
}

interface GroupedInsights {
  theme_id: number
  theme_name: string
  insights: ThemedInsight[]
}

export default function ThemedInsightsList({
  articleId,
  onTimestampClick,
  searchQuery,
  clickedTimestamp
}: ThemedInsightsListProps) {
  const [loading, setLoading] = useState(true)
  const [groupedInsights, setGroupedInsights] = useState<GroupedInsights[]>([])
  const [expandedThemes, setExpandedThemes] = useState<Set<number>>(new Set())

  useEffect(() => {
    fetchThemedInsights()
  }, [articleId])

  const fetchThemedInsights = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/private-articles/${articleId}/themed-insights`)

      if (!response.ok) {
        // 404 or other error - just silently fail (no themed insights)
        setGroupedInsights([])
        return
      }

      const data = await response.json()
      setGroupedInsights(data.grouped_insights || [])

      // Auto-expand themes that have insights
      if (data.grouped_insights?.length > 0) {
        setExpandedThemes(new Set(data.grouped_insights.map((g: GroupedInsights) => g.theme_id)))
      }
    } catch (error) {
      console.error('Error fetching themed insights:', error)
      setGroupedInsights([])
    } finally {
      setLoading(false)
    }
  }

  const handleTimestampClick = (seconds: number | null) => {
    if (seconds && onTimestampClick) {
      onTimestampClick(seconds)
    }
  }

  const toggleTheme = (themeId: number) => {
    setExpandedThemes(prev => {
      const newSet = new Set(prev)
      if (newSet.has(themeId)) {
        newSet.delete(themeId)
      } else {
        newSet.add(themeId)
      }
      return newSet
    })
  }

  if (loading) {
    return (
      <div className="py-4">
        <div className="animate-pulse flex items-center gap-2">
          <div className="h-5 w-5 bg-gray-200 rounded"></div>
          <div className="h-5 w-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (groupedInsights.length === 0) {
    return null
  }

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-[#030712] flex items-center gap-2">
        <Tag className="h-5 w-5 text-blue-600" />
        Themed Insights
      </h3>

      {groupedInsights.map((group) => (
        <div key={group.theme_id} className="border border-blue-200 rounded-lg overflow-hidden">
          {/* Theme Header */}
          <button
            onClick={() => toggleTheme(group.theme_id)}
            className="w-full flex items-center justify-between px-4 py-3 bg-blue-50 hover:bg-blue-100 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Tag className="h-4 w-4 text-blue-600" />
              <span className="font-medium text-blue-900">{group.theme_name}</span>
              <span className="text-sm text-blue-600">({group.insights.length})</span>
            </div>
            <ChevronDown
              className={`h-5 w-5 text-blue-600 transition-transform ${
                expandedThemes.has(group.theme_id) ? 'rotate-180' : ''
              }`}
            />
          </button>

          {/* Theme Insights */}
          {expandedThemes.has(group.theme_id) && (
            <div className="p-4 space-y-3 bg-white">
              {group.insights.map((insight) => (
                <div
                  key={insight.id}
                  className="bg-blue-50 rounded-lg border border-blue-100 overflow-hidden"
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
                        className="flex items-center gap-1 px-2 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors shrink-0"
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
          )}
        </div>
      ))}
    </div>
  )
}
