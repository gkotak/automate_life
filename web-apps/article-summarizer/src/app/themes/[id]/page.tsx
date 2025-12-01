'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { ArrowLeft, Tag, FileText, ChevronDown, ChevronUp, Play } from 'lucide-react'

interface ThemedInsight {
  id: number
  insight_text: string
  timestamp_seconds: number | null
  time_formatted: string | null
  private_article_id: number
  created_at: string
}

interface ArticleInsights {
  article_id: number
  article_title: string
  article_url: string
  insights: ThemedInsight[]
}

interface ThemeDetails {
  id: number
  name: string
  created_at: string
}

export default function ThemeAggregatePage() {
  const params = useParams()
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()

  const [theme, setTheme] = useState<ThemeDetails | null>(null)
  const [insightsByArticle, setInsightsByArticle] = useState<ArticleInsights[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedArticles, setExpandedArticles] = useState<Set<number>>(new Set())
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [totalInsights, setTotalInsights] = useState(0)

  const themeId = params.id as string

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  // Load theme details and insights
  useEffect(() => {
    if (user && themeId) {
      loadThemeDetails()
      loadInsights(1)
    }
  }, [user, themeId])

  const loadThemeDetails = async () => {
    try {
      const response = await fetch(`/api/themes/${themeId}`)
      if (!response.ok) {
        if (response.status === 404) {
          setError('Theme not found')
          return
        }
        throw new Error('Failed to load theme')
      }
      const data = await response.json()
      setTheme(data.theme)
    } catch (err) {
      console.error('Error loading theme:', err)
      setError(err instanceof Error ? err.message : 'Failed to load theme')
    }
  }

  const loadInsights = async (pageNum: number) => {
    try {
      setLoading(true)
      const response = await fetch(`/api/themes/${themeId}/insights?page=${pageNum}&limit=20`)

      if (!response.ok) {
        throw new Error('Failed to load insights')
      }

      const data = await response.json()

      if (pageNum === 1) {
        setInsightsByArticle(data.insights_by_article || [])
        // Auto-expand all articles on first load
        const articleIds = (data.insights_by_article || []).map((a: ArticleInsights) => a.article_id)
        setExpandedArticles(new Set(articleIds))
      } else {
        setInsightsByArticle(prev => [...prev, ...(data.insights_by_article || [])])
        // Expand newly loaded articles
        const newIds = (data.insights_by_article || []).map((a: ArticleInsights) => a.article_id)
        setExpandedArticles(prev => new Set([...prev, ...newIds]))
      }

      setTotalInsights(data.total_count || 0)
      setHasMore(data.has_more || false)
      setPage(pageNum)
    } catch (err) {
      console.error('Error loading insights:', err)
      setError(err instanceof Error ? err.message : 'Failed to load insights')
    } finally {
      setLoading(false)
    }
  }

  const toggleArticle = (articleId: number) => {
    setExpandedArticles(prev => {
      const newSet = new Set(prev)
      if (newSet.has(articleId)) {
        newSet.delete(articleId)
      } else {
        newSet.add(articleId)
      }
      return newSet
    })
  }

  const loadMore = () => {
    loadInsights(page + 1)
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#077331]"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-gray-600 hover:text-[#077331] mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Articles
          </Link>
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-gray-600 hover:text-[#077331] mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Articles
          </Link>

          {theme ? (
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Tag className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{theme.name}</h1>
                <p className="text-gray-600">
                  {totalInsights} insight{totalInsights !== 1 ? 's' : ''} across {insightsByArticle.length} article{insightsByArticle.length !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
          ) : (
            <div className="animate-pulse flex items-center gap-3">
              <div className="h-12 w-12 bg-gray-200 rounded-lg"></div>
              <div>
                <div className="h-6 w-48 bg-gray-200 rounded mb-2"></div>
                <div className="h-4 w-32 bg-gray-200 rounded"></div>
              </div>
            </div>
          )}
        </div>

        {/* Insights grouped by article */}
        {loading && page === 1 ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-6 animate-pulse">
                <div className="h-5 w-64 bg-gray-200 rounded mb-4"></div>
                <div className="space-y-2">
                  <div className="h-4 w-full bg-gray-100 rounded"></div>
                  <div className="h-4 w-3/4 bg-gray-100 rounded"></div>
                </div>
              </div>
            ))}
          </div>
        ) : insightsByArticle.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <Tag className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No insights found for this theme yet.</p>
            <p className="text-gray-400 text-sm mt-1">
              Insights will appear here as private articles are processed.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {insightsByArticle.map((articleGroup) => (
              <div
                key={articleGroup.article_id}
                className="bg-white rounded-lg border border-gray-200 overflow-hidden"
              >
                {/* Article Header */}
                <button
                  onClick={() => toggleArticle(articleGroup.article_id)}
                  className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3 text-left">
                    <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
                    <div>
                      <Link
                        href={`/private-article/${articleGroup.article_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="font-medium text-gray-900 hover:text-[#077331] transition-colors"
                      >
                        {articleGroup.article_title}
                      </Link>
                      <p className="text-sm text-gray-500">
                        {articleGroup.insights.length} insight{articleGroup.insights.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                  {expandedArticles.has(articleGroup.article_id) ? (
                    <ChevronUp className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-400" />
                  )}
                </button>

                {/* Insights for this article */}
                {expandedArticles.has(articleGroup.article_id) && (
                  <div className="px-6 pb-4 space-y-3 border-t border-gray-100">
                    {articleGroup.insights.map((insight) => (
                      <div
                        key={insight.id}
                        className="bg-blue-50 rounded-lg border border-blue-100 p-4 mt-3"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex-1">
                            <p className="text-gray-800 leading-relaxed">
                              {insight.insight_text}
                            </p>
                          </div>
                          {insight.timestamp_seconds && insight.time_formatted && (
                            <Link
                              href={`/private-article/${articleGroup.article_id}?t=${insight.timestamp_seconds}`}
                              className="flex items-center gap-1 px-2 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors shrink-0"
                              title={`Jump to ${insight.time_formatted}`}
                            >
                              <Play className="h-3 w-3" />
                              {insight.time_formatted}
                            </Link>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {/* Load More */}
            {hasMore && (
              <div className="text-center py-4">
                <button
                  onClick={loadMore}
                  disabled={loading}
                  className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Loading...' : 'Load More'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
