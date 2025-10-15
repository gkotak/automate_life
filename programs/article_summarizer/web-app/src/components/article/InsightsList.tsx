import { Insight } from '@/lib/supabase'
import { Clock, Play } from 'lucide-react'

interface InsightsListProps {
  insights: Insight[]
  onTimestampClick?: (seconds: number) => void
}

export default function InsightsList({ insights, onTimestampClick }: InsightsListProps) {
  if (!insights || insights.length === 0) {
    return null
  }

  const handleTimestampClick = (seconds: number | null) => {
    if (seconds && onTimestampClick) {
      onTimestampClick(seconds)
    }
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-[#030712] flex items-center gap-2">
        💡 Key Insights
        <span className="text-sm font-normal text-[#475569]">({insights.length})</span>
      </h3>

      <div className="space-y-3">
        {insights.map((insight, index) => (
          <div
            key={index}
            className="flex items-start gap-3 p-3 bg-green-50 rounded-lg border border-[#e2e8f0]"
          >
            <div className="flex-1">
              <p className="text-[#030712] leading-relaxed">{insight.insight}</p>
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
        ))}
      </div>
    </div>
  )
}