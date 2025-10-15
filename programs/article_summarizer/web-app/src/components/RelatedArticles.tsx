'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Article } from '@/lib/supabase'

interface RelatedArticlesProps {
  articleId: number
}

export default function RelatedArticles({ articleId }: RelatedArticlesProps) {
  const [relatedArticles, setRelatedArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchRelatedArticles()
  }, [articleId])

  const fetchRelatedArticles = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/related', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          articleId,
          limit: 5,
        }),
      })

      if (response.ok) {
        const { related } = await response.json()
        setRelatedArticles(related || [])
      }
    } catch (error) {
      console.error('Error fetching related articles:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="mt-8 p-6 bg-gray-50 rounded-lg">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Related Articles</h2>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  if (relatedArticles.length === 0) {
    return null
  }

  return (
    <div className="mt-8 p-6 bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg border border-purple-100">
      <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <span>🔗</span>
        Related Articles
        <span className="text-sm font-normal text-gray-500">(AI-powered recommendations)</span>
      </h2>
      <div className="space-y-3">
        {relatedArticles.map((article: any) => (
          <Link
            key={article.id}
            href={`/article/${article.id}`}
            className="block p-4 bg-white rounded-lg hover:shadow-md transition-all border border-gray-200 hover:border-purple-300"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="flex-1">
                <h3 className="font-medium text-gray-900 hover:text-purple-600 line-clamp-2">
                  {article.title}
                </h3>
                {article.summary_text && (
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                    {article.summary_text.slice(0, 150)}...
                  </p>
                )}
                <div className="flex gap-2 mt-2">
                  {article.content_source && (
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                      {article.content_source}
                    </span>
                  )}
                  {article.similarity && (
                    <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">
                      {Math.round(article.similarity * 100)}% match
                    </span>
                  )}
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
