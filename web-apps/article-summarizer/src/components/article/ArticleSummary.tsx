import { Article } from '@/lib/supabase'
import InsightsList from './InsightsList'
import QuotesList from './QuotesList'
import { highlightKeywords } from '@/lib/textHighlight'
import { useMemo } from 'react'

interface ArticleSummaryProps {
  article: Article
  onTimestampClick?: (seconds: number) => void
  searchQuery?: string
}

export default function ArticleSummary({ article, onTimestampClick, searchQuery }: ArticleSummaryProps) {
  const highlightedSummary = useMemo(() => {
    if (!searchQuery || !article.summary_text) return article.summary_text
    return highlightKeywords(article.summary_text, searchQuery)
  }, [article.summary_text, searchQuery])

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Summary Text (Paragraph Form) */}
      {article.summary_text && (
        <div className="space-y-3 sm:space-y-4">
          <h3 className="text-lg sm:text-xl font-semibold text-gray-900">Summary</h3>
          <div
            className="prose prose-sm sm:prose-base lg:prose-lg max-w-none text-gray-700 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: highlightedSummary }}
          />
        </div>
      )}

      {/* Key Insights (Combined: insights, main points, takeaways) */}
      {article.key_insights && article.key_insights.length > 0 && (
        <InsightsList
          insights={article.key_insights}
          onTimestampClick={onTimestampClick}
          searchQuery={searchQuery}
        />
      )}

      {/* Quotes */}
      {article.quotes && article.quotes.length > 0 && (
        <QuotesList
          quotes={article.quotes}
          onTimestampClick={onTimestampClick}
          searchQuery={searchQuery}
        />
      )}

      {/* Topics */}
      {article.topics && article.topics.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Topics:</h4>
          <div className="flex flex-wrap gap-1.5 sm:gap-2">
            {article.topics.map((topic, index) => (
              <span
                key={index}
                className="px-2 py-0.5 sm:py-1 bg-purple-100 text-purple-800 rounded-full text-xs"
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