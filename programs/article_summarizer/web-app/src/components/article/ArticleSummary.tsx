import { Article } from '@/lib/supabase'
import InsightsList from './InsightsList'
import QuotesList from './QuotesList'

interface ArticleSummaryProps {
  article: Article
  onTimestampClick?: (seconds: number) => void
}

export default function ArticleSummary({ article, onTimestampClick }: ArticleSummaryProps) {
  // Check if we have structured data
  const hasStructuredData =
    article.key_insights?.length ||
    article.quotes?.length

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
        </div>
      </div>

      {/* Summary Text (Paragraph Form) */}
      {article.summary_text && (
        <div className="space-y-4">
          <h3 className="text-xl font-semibold text-gray-900">Summary</h3>
          <div
            className="prose prose-lg max-w-none text-gray-700 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: article.summary_text }}
          />
        </div>
      )}

      {/* Key Insights (Combined: insights, main points, takeaways) */}
      {article.key_insights && article.key_insights.length > 0 && (
        <InsightsList
          insights={article.key_insights}
          onTimestampClick={onTimestampClick}
        />
      )}

      {/* Quotes */}
      {article.quotes && article.quotes.length > 0 && (
        <QuotesList
          quotes={article.quotes}
          onTimestampClick={onTimestampClick}
        />
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