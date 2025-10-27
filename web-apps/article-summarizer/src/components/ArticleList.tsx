'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { supabase, Article } from '@/lib/supabase'
import { Search, Trash2, ExternalLink, Calendar, Tag, X, CheckCircle, AlertCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

type NotificationType = 'success' | 'error' | 'warning'

interface Notification {
  id: string
  type: NotificationType
  message: string
}

export default function ArticleList() {
  const { user } = useAuth()
  const pathname = usePathname()
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFilter, setSearchFilter] = useState<'all' | 'summary' | 'transcript' | 'article'>('all')
  const [searchMode, setSearchMode] = useState<'keyword' | 'hybrid'>('hybrid')
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [hasLoaded, setHasLoaded] = useState(false)

  // Filter states
  const [selectedContentTypes, setSelectedContentTypes] = useState<string[]>([])
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  // Source filter states
  const [availableSources, setAvailableSources] = useState<Array<{name: string, count: number}>>([])
  const [showAllSources, setShowAllSources] = useState(false)

  // Fetch articles on mount, when user changes, or when pathname changes (navigation)
  useEffect(() => {
    if (pathname === '/') {
      fetchArticles()
      fetchAvailableSources()
    }
  }, [user, pathname])

  const fetchAvailableSources = async () => {
    try {
      const { data, error } = await supabase
        .from('articles')
        .select('source')

      if (error) throw error

      // Count sources
      const sourceCounts: Record<string, number> = {}
      data?.forEach(article => {
        if (article.source) {
          sourceCounts[article.source] = (sourceCounts[article.source] || 0) + 1
        }
      })

      // Convert to array and sort by count
      const sourcesArray = Object.entries(sourceCounts)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count)

      setAvailableSources(sourcesArray)
    } catch (error) {
      console.error('Error fetching sources:', error)
    }
  }

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

      let query = supabase
        .from('articles')
        .select('*, key_insights, quotes, duration_minutes, word_count, topics')

      // NOTE: User filtering disabled - articles don't have user_id set yet
      // TODO: Implement user isolation when ready:
      // 1. Run migration to add user_id to existing articles
      // 2. Update article processor to set user_id on new articles
      // 3. Re-enable the filter below:
      // if (user) {
      //   query = query.eq('user_id', user.id)
      // }

      const { data, error } = await query.order('created_at', { ascending: false })

      if (error) throw error

      // Only update articles after we have the data
      if (data) {
        setArticles(data)
      }
      setHasLoaded(true)
    } catch (error) {
      console.error('Error fetching articles:', error)
      setHasLoaded(true)
    } finally {
      setLoading(false)
    }
  }

  const deleteArticle = async (id: number) => {
    // Phase 1: Only allow authenticated users to delete
    if (!user) {
      addNotification('error', 'You must be signed in to delete articles')
      return
    }

    if (!confirm('Are you sure you want to delete this article?')) return

    try {
      console.log(`🗑️ Attempting to delete article with ID: ${id}`)

      const { error } = await supabase
        .from('articles')
        .delete()
        .eq('id', id)

      if (error) {
        console.error('Supabase delete error:', error)
        throw error
      }

      // Delete successful - remove from local state
      console.log(`✅ Successfully deleted article with id: ${id}`)
      setArticles(articles.filter(article => article.id !== id))
      addNotification('success', 'Article deleted successfully!')
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

  const performSearch = async (query: string, contentTypes: string[], sources: string[], from: string, to: string) => {
    // Check if we have any filters applied
    const hasFilters = contentTypes.length > 0 || sources.length > 0 || from || to

    // If no search query and no filters, just fetch all articles
    if (!query.trim() && !hasFilters) {
      fetchArticles()
      return
    }

    try {
      setLoading(true)

      // Build filters object
      const filters: any = {}
      if (contentTypes.length > 0) filters.contentTypes = contentTypes
      if (sources.length > 0) filters.sources = sources
      if (from) filters.dateFrom = from
      if (to) filters.dateTo = to

      // Use API for search with filters (even if query is empty)
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query || '',
          limit: 30,
          mode: searchMode,
          filters,
        }),
      })

      if (!response.ok) {
        throw new Error('Search failed')
      }

      const { results } = await response.json()

      // Only update articles if we got results
      if (results) {
        setArticles(results)
      }
    } catch (error) {
      console.error('Error searching articles:', error)
      addNotification('error', 'Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const searchArticles = async () => {
    await performSearch(searchQuery, selectedContentTypes, selectedSources, dateFrom, dateTo)
  }

  const clearFilters = () => {
    setSelectedContentTypes([])
    setSelectedSources([])
    setDateFrom('')
    setDateTo('')
  }

  const toggleContentType = (type: string) => {
    setSelectedContentTypes(prev => {
      const newTypes = prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
      // Trigger search with the new state immediately
      setTimeout(() => performSearch(searchQuery, newTypes, selectedSources, dateFrom, dateTo), 0)
      return newTypes
    })
  }

  const toggleSource = (source: string) => {
    setSelectedSources(prev => {
      const newSources = prev.includes(source) ? prev.filter(s => s !== source) : [...prev, source]
      // Trigger search with the new state immediately
      setTimeout(() => performSearch(searchQuery, selectedContentTypes, newSources, dateFrom, dateTo), 0)
      return newSources
    })
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
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8">
      {/* Notifications Area */}
      {notifications.length > 0 && (
        <div className="fixed top-4 right-4 left-4 sm:left-auto z-50 space-y-2">
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg max-w-md transition-all duration-300 ${
                notification.type === 'success'
                  ? 'bg-green-50 border border-[#077331] text-[#077331]'
                  : notification.type === 'error'
                  ? 'bg-red-50 border border-red-200 text-red-800'
                  : 'bg-yellow-50 border border-yellow-200 text-yellow-800'
              }`}
            >
              {notification.type === 'success' && <CheckCircle className="h-5 w-5 text-[#077331] flex-shrink-0" />}
              {notification.type === 'error' && <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />}
              {notification.type === 'warning' && <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0" />}

              <span className="flex-1 text-sm font-medium">{notification.message}</span>

              <button
                onClick={() => removeNotification(notification.id)}
                className="text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mb-6 sm:mb-8">
        {/* Search Interface */}
        <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 mb-4 sm:mb-6">
          <div className="flex flex-col gap-4">
            {/* Search Mode Toggle */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
              <span className="text-sm font-medium text-gray-700 flex-shrink-0">Search Mode:</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setSearchMode('hybrid')}
                  className={`flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                    searchMode === 'hybrid'
                      ? 'bg-[#077331] text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  🧠 AI Search
                </button>
                <button
                  onClick={() => setSearchMode('keyword')}
                  className={`flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                    searchMode === 'keyword'
                      ? 'bg-[#077331] text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  Keyword
                </button>
              </div>
              {searchMode === 'hybrid' && (
                <span className="text-xs text-gray-500 italic hidden sm:block">
                  AI understanding + keyword matching for best results
                </span>
              )}
              {searchMode === 'keyword' && (
                <span className="text-xs text-gray-500 italic hidden sm:block">
                  Fast exact text matching
                </span>
              )}
            </div>

            {/* Search Input */}
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder={
                      searchMode === 'hybrid'
                        ? 'Ask a question or search by keywords...'
                        : 'Search articles by keywords...'
                    }
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="w-full pl-10 pr-10 py-2 border border-[#e2e8f0] rounded-md focus:ring-2 focus:ring-[#077331] focus:border-transparent"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => {
                        setSearchQuery('')
                        fetchArticles()
                      }}
                      className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
              <div className="flex gap-2 w-full sm:w-auto">
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={`flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                    showFilters
                      ? 'bg-green-50 text-[#077331] border border-[#077331]'
                      : 'bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50'
                  }`}
                >
                  Filters {(selectedContentTypes.length + selectedSources.length) > 0 && `(${selectedContentTypes.length + selectedSources.length})`}
                </button>
                <button
                  onClick={searchArticles}
                  className="flex-1 sm:flex-none px-4 sm:px-6 py-2 text-white rounded-md focus:ring-2 transition-colors text-xs sm:text-sm bg-[#077331] hover:bg-[#055a24] focus:ring-[#077331]"
                >
                  Search
                </button>
              </div>
            </div>

            {/* Filters Section */}
            {showFilters && (
              <div className="pt-4 border-t border-gray-200">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Content Type Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Content Type</label>
                    <div className="space-y-2">
                      {['video', 'audio', 'article'].map(type => (
                        <label key={type} className="flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedContentTypes.includes(type)}
                            onChange={() => toggleContentType(type)}
                            className="rounded border-gray-300 text-[#077331] focus:ring-[#077331]"
                          />
                          <span className="ml-2 text-sm text-gray-700 capitalize">{type}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Source Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Source</label>
                    <div className="space-y-2">
                      {(showAllSources ? availableSources : availableSources.slice(0, 4)).map(source => (
                        <label key={source.name} className="flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedSources.includes(source.name)}
                            onChange={() => toggleSource(source.name)}
                            className="rounded border-gray-300 text-[#077331] focus:ring-[#077331]"
                          />
                          <span className="ml-2 text-sm text-gray-700">{source.name}</span>
                          <span className="ml-auto text-xs text-gray-500">({source.count})</span>
                        </label>
                      ))}
                      {availableSources.length > 4 && (
                        <button
                          onClick={() => setShowAllSources(!showAllSources)}
                          className="text-sm text-[#077331] hover:text-[#055a24] font-medium"
                        >
                          {showAllSources ? 'Show less' : `More (${availableSources.length - 4})`}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Date Range Filter */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">From Date</label>
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => {
                        const newDateFrom = e.target.value
                        setDateFrom(newDateFrom)
                        // Trigger search with the new date
                        setTimeout(() => performSearch(searchQuery, selectedContentTypes, selectedSources, newDateFrom, dateTo), 0)
                      }}
                      className="w-full px-3 py-2 border border-[#e2e8f0] rounded-md focus:ring-2 focus:ring-[#077331]"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">To Date</label>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => {
                        const newDateTo = e.target.value
                        setDateTo(newDateTo)
                        // Trigger search with the new date
                        setTimeout(() => performSearch(searchQuery, selectedContentTypes, selectedSources, dateFrom, newDateTo), 0)
                      }}
                      className="w-full px-3 py-2 border border-[#e2e8f0] rounded-md focus:ring-2 focus:ring-[#077331]"
                    />
                  </div>
                </div>

                {/* Active Filters Display */}
                {(selectedContentTypes.length > 0 || selectedSources.length > 0 || dateFrom || dateTo) && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {selectedContentTypes.map(type => (
                      <span key={type} className="inline-flex items-center gap-1 px-3 py-1 bg-green-50 text-[#077331] rounded-full text-sm border border-[#077331]">
                        {type}
                        <button onClick={() => toggleContentType(type)} className="hover:text-[#055a24]">
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                    {selectedSources.map(source => (
                      <span key={source} className="inline-flex items-center gap-1 px-3 py-1 bg-green-50 text-[#077331] rounded-full text-sm border border-[#077331]">
                        {source}
                        <button onClick={() => toggleSource(source)} className="hover:text-[#055a24]">
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                    <button
                      onClick={clearFilters}
                      className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900"
                    >
                      Clear all filters
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-4 sm:mb-6">
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 border border-[#e2e8f0]">
            <div className="text-xl sm:text-2xl font-bold text-[#077331]">{articles.length}</div>
            <div className="text-xs sm:text-sm text-[#475569]">Total Articles</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 border border-[#e2e8f0]">
            <div className="text-xl sm:text-2xl font-bold text-[#077331]">
              {articles.filter(a => a.content_source === 'video').length}
            </div>
            <div className="text-xs sm:text-sm text-[#475569]">Videos</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 border border-[#e2e8f0]">
            <div className="text-xl sm:text-2xl font-bold text-[#077331]">
              {articles.filter(a => a.content_source === 'audio').length}
            </div>
            <div className="text-xs sm:text-sm text-[#475569]">Audio</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 border border-[#e2e8f0]">
            <div className="text-xl sm:text-2xl font-bold text-[#077331]">
              {articles.filter(a => a.content_source === 'article').length}
            </div>
            <div className="text-xs sm:text-sm text-[#475569]">Articles</div>
          </div>
        </div>
      </div>

      {/* Articles List */}
      {loading && articles.length === 0 ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading articles...</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:gap-6">
          {articles.map((article) => (
            <div key={article.id} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow border border-[#e2e8f0]">
              <div className="p-4 sm:p-6">
                <div className="flex justify-between items-start mb-3 sm:mb-4 gap-2">
                  <Link href={`/article/${article.id}`} className="flex-1 min-w-0">
                    <h2 className="text-base sm:text-lg lg:text-xl font-semibold text-[#030712] hover:text-[#077331] transition-colors cursor-pointer line-clamp-2">
                      {article.title}
                    </h2>
                  </Link>
                  <div className="flex gap-1 sm:gap-2 flex-shrink-0">
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 sm:p-2 text-gray-500 hover:text-blue-600 transition-colors"
                      title="Open original article"
                    >
                      <ExternalLink className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                    </a>
                    {user && (
                      <button
                        onClick={() => deleteArticle(article.id)}
                        className="p-1.5 sm:p-2 text-gray-500 hover:text-red-600 transition-colors"
                        title="Delete article"
                      >
                        <Trash2 className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Tags and metadata */}
                <div className="flex flex-wrap gap-1.5 sm:gap-2 mb-3 sm:mb-4">
                  {article.content_source && (
                    <span className={`px-2 py-0.5 sm:py-1 rounded-full text-xs font-medium ${getContentTypeColor(article.content_source)}`}>
                      {article.content_source}
                    </span>
                  )}
                  {article.source && (
                    <span className={`px-2 py-0.5 sm:py-1 rounded-full text-xs font-medium ${getPlatformColor(article.source)}`}>
                      {article.source}
                    </span>
                  )}
                  {article.tags?.map((tag, index) => (
                    <span key={index} className="px-2 py-0.5 sm:py-1 bg-gray-100 text-gray-700 rounded-full text-xs">
                      <Tag className="inline h-3 w-3 mr-1" />
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="flex items-center text-xs sm:text-sm text-gray-500 mb-3 sm:mb-4">
                  <Calendar className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 flex-shrink-0" />
                  <span className="truncate">{formatDate(article.created_at)}</span>
                </div>

                {/* Summary preview */}
                {article.summary_text && (
                  <div className="text-sm sm:text-base text-gray-700 line-clamp-2 sm:line-clamp-3">
                    {article.summary_text.slice(0, 300)}...
                  </div>
                )}
              </div>
            </div>
          ))}

          {articles.length === 0 && !loading && hasLoaded && (
            <div className="text-center py-12">
              <p className="text-gray-600">No articles found</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}