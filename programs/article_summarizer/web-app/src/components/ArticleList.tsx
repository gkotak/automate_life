'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { supabase, Article } from '@/lib/supabase'
import { Search, Trash2, ExternalLink, Calendar, Tag, X, CheckCircle, AlertCircle } from 'lucide-react'

type NotificationType = 'success' | 'error' | 'warning'

interface Notification {
  id: string
  type: NotificationType
  message: string
}

export default function ArticleList() {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFilter, setSearchFilter] = useState<'all' | 'summary' | 'transcript' | 'article'>('all')
  const [notifications, setNotifications] = useState<Notification[]>([])

  useEffect(() => {
    fetchArticles()
  }, [])

  const addNotification = (type: NotificationType, message: string) => {
    const id = Date.now().toString()
    const notification: Notification = { id, type, message }
    setNotifications(prev => [...prev, notification])

    // Auto-remove after 5 seconds
    setTimeout(() => {
      removeNotification(id)
    }, 5000)
  }

  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const fetchArticles = async () => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('articles')
        .select('*, key_insights, main_points, quotes, takeaways, duration_minutes, word_count, topics')
        .order('created_at', { ascending: false })

      if (error) throw error
      setArticles(data || [])
    } catch (error) {
      console.error('Error fetching articles:', error)
    } finally {
      setLoading(false)
    }
  }

  const deleteArticle = async (id: number) => {
    if (!confirm('Are you sure you want to delete this article?')) return

    try {
      console.log(`🗑️ Attempting to delete article with ID: ${id}`)

      const { data, error } = await supabase
        .from('articles')
        .delete()
        .eq('id', id)

      console.log('Delete response:', { data, error })

      if (error) {
        console.error('Supabase delete error:', error)
        throw error
      }

      if (data && data.length > 0) {
        console.log(`✅ Successfully deleted article: ${data[0].title || 'Unknown'}`)
        setArticles(articles.filter(article => article.id !== id))
        addNotification('success', 'Article deleted successfully!')
      } else {
        console.warn('⚠️ Delete operation completed but no data returned. This might indicate the record was not found or already deleted.')
        // Still remove from local state in case it was a soft delete or async operation
        setArticles(articles.filter(article => article.id !== id))
        addNotification('warning', 'Article delete completed (no confirmation data returned)')
      }
    } catch (error) {
      console.error('Error deleting article:', error)
      console.error('Error details:', {
        name: error.name,
        message: error.message,
        stack: error.stack
      })
      addNotification('error', `Failed to delete article: ${error.message}`)
    }
  }

  const searchArticles = async () => {
    if (!searchQuery.trim()) {
      fetchArticles()
      return
    }

    try {
      setLoading(true)

      // Basic text search for now
      let query = supabase
        .from('articles')
        .select('*')
        .order('created_at', { ascending: false })

      if (searchFilter === 'summary') {
        query = query.ilike('summary_text', `%${searchQuery}%`)
      } else if (searchFilter === 'transcript') {
        query = query.ilike('transcript_text', `%${searchQuery}%`)
      } else if (searchFilter === 'article') {
        query = query.ilike('original_article_text', `%${searchQuery}%`)
      } else {
        // Search across title, summary, and transcript
        query = query.or(`title.ilike.%${searchQuery}%,summary_text.ilike.%${searchQuery}%,transcript_text.ilike.%${searchQuery}%`)
      }

      const { data, error } = await query

      if (error) throw error
      setArticles(data || [])
    } catch (error) {
      console.error('Error searching articles:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      searchArticles()
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const getContentTypeColor = (contentSource: string | null) => {
    switch (contentSource) {
      case 'video': return 'bg-red-100 text-red-800'
      case 'audio': return 'bg-blue-100 text-blue-800'
      case 'article': return 'bg-green-100 text-green-800'
      case 'mixed': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getPlatformColor = (platform: string | null) => {
    switch (platform) {
      case 'youtube': return 'bg-red-100 text-red-800'
      case 'substack': return 'bg-orange-100 text-orange-800'
      case 'stratechery': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Notifications Area */}
      {notifications.length > 0 && (
        <div className="fixed top-4 right-4 z-50 space-y-2">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg max-w-md transition-all duration-300 ${
                notification.type === 'success'
                  ? 'bg-green-50 border border-green-200 text-green-800'
                  : notification.type === 'error'
                  ? 'bg-red-50 border border-red-200 text-red-800'
                  : 'bg-yellow-50 border border-yellow-200 text-yellow-800'
              }`}
            >
              {notification.type === 'success' && <CheckCircle className="h-5 w-5 text-green-600" />}
              {notification.type === 'error' && <AlertCircle className="h-5 w-5 text-red-600" />}
              {notification.type === 'warning' && <AlertCircle className="h-5 w-5 text-yellow-600" />}

              <span className="flex-1 text-sm font-medium">{notification.message}</span>

              <button
                onClick={() => removeNotification(notification.id)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Article Library</h1>
        <p className="text-gray-600 mb-6">Search and manage your article summaries</p>

        {/* Search Interface */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search articles..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <select
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Content</option>
                <option value="summary">Summary Only</option>
                <option value="transcript">Transcript Only</option>
                <option value="article">Article Only</option>
              </select>
              <button
                onClick={searchArticles}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500"
              >
                Search
              </button>
              <button
                onClick={fetchArticles}
                className="px-6 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 focus:ring-2 focus:ring-gray-500"
              >
                Clear
              </button>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-2xl font-bold text-blue-600">{articles.length}</div>
            <div className="text-gray-600">Total Articles</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-2xl font-bold text-green-600">
              {articles.filter(a => a.content_source === 'video').length}
            </div>
            <div className="text-gray-600">Videos</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-2xl font-bold text-purple-600">
              {articles.filter(a => a.content_source === 'audio').length}
            </div>
            <div className="text-gray-600">Audio</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-2xl font-bold text-orange-600">
              {articles.filter(a => a.content_source === 'article').length}
            </div>
            <div className="text-gray-600">Articles</div>
          </div>
        </div>
      </div>

      {/* Articles List */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading articles...</p>
        </div>
      ) : (
        <div className="grid gap-6">
          {articles.map((article) => (
            <div key={article.id} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <Link href={`/article/${article.id}`} className="flex-1 mr-4">
                    <h2 className="text-xl font-semibold text-gray-900 hover:text-blue-600 transition-colors cursor-pointer">
                      {article.title}
                    </h2>
                  </Link>
                  <div className="flex gap-2">
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-gray-500 hover:text-blue-600 transition-colors"
                      title="Open original article"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                    <button
                      onClick={() => deleteArticle(article.id)}
                      className="p-2 text-gray-500 hover:text-red-600 transition-colors"
                      title="Delete article"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Tags and metadata */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {article.content_source && (
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getContentTypeColor(article.content_source)}`}>
                      {article.content_source}
                    </span>
                  )}
                  {article.platform && (
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPlatformColor(article.platform)}`}>
                      {article.platform}
                    </span>
                  )}
                  {article.tags?.map((tag, index) => (
                    <span key={index} className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">
                      <Tag className="inline h-3 w-3 mr-1" />
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="flex items-center text-sm text-gray-500 mb-4">
                  <Calendar className="h-4 w-4 mr-1" />
                  {formatDate(article.created_at)}
                </div>

                {/* Summary preview */}
                {article.summary_text && (
                  <div className="text-gray-700 line-clamp-3">
                    {article.summary_text.slice(0, 300)}...
                  </div>
                )}
              </div>
            </div>
          ))}

          {articles.length === 0 && !loading && (
            <div className="text-center py-12">
              <p className="text-gray-600">No articles found</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}