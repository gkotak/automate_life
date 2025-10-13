import { Article } from '@/lib/supabase'
import InsightsList from './InsightsList'
import MainPointsList from './MainPointsList'
import QuotesList from './QuotesList'
import TakeawaysList from './TakeawaysList'

interface ArticleSummaryProps {
  article: Article
  onTimestampClick?: (seconds: number) => void
}

export default function ArticleSummary({ article, onTimestampClick }: ArticleSummaryProps) {
  // Check if we have structured data
  const hasStructuredData =
    article.key_insights?.length ||
    article.main_points?.length ||
    article.quotes?.length ||
    article.takeaways?.length

  // If no structured data, fall back to HTML rendering
  if (!hasStructuredData && article.summary_html) {
    return (
      <div className="space-y-6">
        <div
          className="prose max-w-none"
          dangerouslySetInnerHTML={{ __html: article.summary_html }}
        />
      </div>
    )
  }

  // Render structured data
  return (
    <div className="space-y-8">
      {/* Article metadata */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex flex-wrap gap-4 text-sm text-gray-600">
          {article.duration_minutes && (
            <div className="flex items-center gap-1">
              🕐 Duration: {article.duration_minutes} minutes
            </div>
          )}
          {article.word_count && (
            <div className="flex items-center gap-1">
              📝 ~{article.word_count} words
            </div>
          )}
          {article.complexity_level && (
            <div className="flex items-center gap-1">
              🎯 Level: {article.complexity_level}
            </div>
          )}
          {article.sentiment && (
            <div className="flex items-center gap-1">
              😊 Tone: {article.sentiment}
            </div>
          )}
        </div>
      </div>

      {/* Key Insights */}
      {article.key_insights && article.key_insights.length > 0 && (
        <InsightsList
          insights={article.key_insights}
          onTimestampClick={onTimestampClick}
        />
      )}

      {/* Main Points */}
      {article.main_points && article.main_points.length > 0 && (
        <MainPointsList points={article.main_points} />
      )}

      {/* Quotes */}
      {article.quotes && article.quotes.length > 0 && (
        <QuotesList
          quotes={article.quotes}
          onTimestampClick={onTimestampClick}
        />
      )}

      {/* Takeaways */}
      {article.takeaways && article.takeaways.length > 0 && (
        <TakeawaysList takeaways={article.takeaways} />
      )}

      {/* Fallback to text summary if no structured content */}
      {!hasStructuredData && article.summary_text && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Summary</h3>
          <div className="prose max-w-none">
            <p className="text-gray-700 leading-relaxed whitespace-pre-line">
              {article.summary_text}
            </p>
          </div>
        </div>
      )}

      {/* Topics */}
      {article.topics && article.topics.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Topics:</h4>
          <div className="flex flex-wrap gap-2">
            {article.topics.map((topic, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-purple-100 text-purple-800 rounded-full text-xs"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}