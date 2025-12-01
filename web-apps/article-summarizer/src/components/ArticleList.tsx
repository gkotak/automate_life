'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Article } from '@/lib/supabase'
import { Search, Trash2, ExternalLink, Calendar, Tag, X, CheckCircle, AlertCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { supabase } from '@/lib/supabase'
import { FolderWithCount, ThemeWithCount } from '@/types/database'
import AddToFolderDropdown from './AddToFolderDropdown'
import CreateFolderModal from './CreateFolderModal'

type NotificationType = 'success' | 'error' | 'warning'

interface Notification {
  id: string
  type: NotificationType
  message: string
}

interface ArticleListProps {
  folderId?: number | null
}

export default function ArticleList({ folderId = null }: ArticleListProps) {
  const { user } = useAuth()
  const pathname = usePathname()

  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchMode, setSearchMode] = useState<'keyword' | 'hybrid'>('hybrid')
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [hasLoaded, setHasLoaded] = useState(false)
  const [extractedTerms, setExtractedTerms] = useState<string[]>([])

  // Filter states
  const [selectedContentTypes, setSelectedContentTypes] = useState<string[]>([])
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [showMyArticlesOnly, setShowMyArticlesOnly] = useState<boolean>(() => {
    // Default to true, but check localStorage for saved preference
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('showMyArticlesOnly')
      return saved !== null ? saved === 'true' : true
    }
    return true
  })

  // Source filter states
  const [availableSources, setAvailableSources] = useState<Array<{name: string, count: number}>>([])
  const [showAllSources, setShowAllSources] = useState(false)

  // Theme filter states
  const [availableThemes, setAvailableThemes] = useState<ThemeWithCount[]>([])
  const [selectedThemes, setSelectedThemes] = useState<number[]>([])

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1)
  const [totalArticles, setTotalArticles] = useState(0)
  const articlesPerPage = 50

  // Stats states for total counts by content type
  const [totalVideos, setTotalVideos] = useState(0)
  const [totalAudio, setTotalAudio] = useState(0)
  const [totalTextArticles, setTotalTextArticles] = useState(0)

  // Folder-related state
  const [folders, setFolders] = useState<FolderWithCount[]>([])
  const [articleFolderMap, setArticleFolderMap] = useState<Map<string, number[]>>(new Map())
  const [showCreateFolderModal, setShowCreateFolderModal] = useState(false)

  // Restore search state from sessionStorage on mount
  useEffect(() => {
    const savedState = sessionStorage.getItem('articleSearchState')
    if (savedState) {
      try {
        const {
          query,
          mode,
          articles: savedArticles,
          extractedTerms: savedTerms,
          contentTypes,
          sources,
          dateFrom: savedDateFrom,
          dateTo: savedDateTo
        } = JSON.parse(savedState)

        setSearchQuery(query || '')
        setSearchMode(mode || 'hybrid')
        setArticles(savedArticles || [])
        setExtractedTerms(savedTerms || [])
        setSelectedContentTypes(contentTypes || [])
        setSelectedSources(sources || [])
        setDateFrom(savedDateFrom || '')
        setDateTo(savedDateTo || '')
        setHasLoaded(true)
        setLoading(false) // Ensure we're not in loading state
      } catch (error) {
        console.error('Failed to restore search state:', error)
        setLoading(false)
      }
    }
  }, [])

  // Fetch articles on mount or when user changes
  useEffect(() => {
    // Only fetch if we're on the home page or a folder page
    const isValidPath = pathname === '/' || pathname.startsWith('/folder/')
    if (!isValidPath) return

    // If we have saved search state and we're on home page, don't fetch (state will be restored)
    if (pathname === '/' && sessionStorage.getItem('articleSearchState')) {
      fetchAvailableSources()
      fetchThemes()
      return
    }

    // Skip if we've already loaded articles (prevents re-fetch when user profile loads)
    // folderId changes are handled by a separate effect
    if (hasLoaded) {
      return
    }

    // If not logged in, ensure "My Articles" filter is off
    if (!user?.id && showMyArticlesOnly) {
      setShowMyArticlesOnly(false)
      localStorage.setItem('showMyArticlesOnly', 'false')
    }

    // Fetch articles (fetchArticles handles all edge cases internally)
    fetchArticles()
    fetchAvailableSources()
    fetchThemes()
  }, [pathname, user?.id])

  // Re-fetch articles when My Articles filter changes (but only after initial load)
  useEffect(() => {
    // Save preference to localStorage
    localStorage.setItem('showMyArticlesOnly', String(showMyArticlesOnly))

    // Only re-fetch if we've loaded before and we're on a valid page
    const isValidPath = pathname === '/' || pathname.startsWith('/folder/')
    if (!hasLoaded || !isValidPath) return

    setCurrentPage(1) // Reset to page 1 when filter changes
    fetchArticles()
    fetchAvailableSources()
  }, [showMyArticlesOnly])

  // Re-fetch articles when page changes
  useEffect(() => {
    // Only re-fetch if we've loaded before and we're on a valid page
    const isValidPath = pathname === '/' || pathname.startsWith('/folder/')
    if (!hasLoaded || !isValidPath) return

    fetchArticles()

    // Scroll to top when page changes
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [currentPage])

  // Fetch articles when user loads (if we're waiting for auth)
  useEffect(() => {
    // Only fetch if:
    // 1. We're on a valid page (home or folder)
    // 2. User just loaded (has ID now)
    // 3. We want My Articles
    // 4. We haven't loaded articles yet
    const isValidPath = pathname === '/' || pathname.startsWith('/folder/')
    if (isValidPath && user?.id && showMyArticlesOnly && !hasLoaded) {
      fetchArticles()
      fetchAvailableSources()
    }
  }, [user?.id])

  // Fetch folders when user is logged in
  useEffect(() => {
    if (user?.id) {
      fetchFolders()
    } else {
      setFolders([])
      setArticleFolderMap(new Map())
    }
  }, [user?.id])

  // Fetch articles when folderId changes (including initial load with folder)
  useEffect(() => {
    const isValidPath = pathname === '/' || pathname.startsWith('/folder/')
    if (!isValidPath) return

    // For folder pages, fetch even on initial load
    // For home page, only re-fetch if already loaded (initial load handled above)
    if (folderId === null && !hasLoaded) return

    setCurrentPage(1)
    fetchArticles()
  }, [folderId])

  // Fetch folders from API
  const fetchFolders = async () => {
    try {
      const response = await fetch('/api/folders')
      if (response.ok) {
        const data = await response.json()
        setFolders(data.folders || [])
      }
    } catch (error) {
      console.error('Failed to fetch folders:', error)
    }
  }

  // Fetch which folders an article belongs to
  const fetchArticleFolders = async (articleIds: number[], privateArticleIds: number[]) => {
    if (!user?.id) return

    try {
      const newMap = new Map<string, number[]>()

      // Fetch folder memberships for public articles
      if (articleIds.length > 0) {
        const { data: publicMemberships } = await supabase
          .from('folder_articles')
          .select('article_id, folder_id')
          .in('article_id', articleIds)

        publicMemberships?.forEach((m) => {
          const key = `public-${m.article_id}`
          const existing = newMap.get(key) || []
          newMap.set(key, [...existing, m.folder_id])
        })
      }

      // Fetch folder memberships for private articles
      if (privateArticleIds.length > 0) {
        const { data: privateMemberships } = await supabase
          .from('folder_private_articles')
          .select('private_article_id, folder_id')
          .in('private_article_id', privateArticleIds)

        privateMemberships?.forEach((m) => {
          const key = `private-${m.private_article_id}`
          const existing = newMap.get(key) || []
          newMap.set(key, [...existing, m.folder_id])
        })
      }

      setArticleFolderMap(newMap)
    } catch (error) {
      console.error('Failed to fetch article folders:', error)
    }
  }

  // Toggle article in/out of folder
  const handleToggleFolder = async (articleId: number, isPrivate: boolean, targetFolderId: number, isInFolder: boolean) => {
    try {
      const response = await fetch(`/api/folders/${targetFolderId}/articles`, {
        method: isInFolder ? 'DELETE' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ articleId, isPrivate }),
      })

      if (response.ok) {
        // Update local state
        const key = `${isPrivate ? 'private' : 'public'}-${articleId}`
        const currentFolders = articleFolderMap.get(key) || []

        const newFolders = isInFolder
          ? currentFolders.filter((id) => id !== targetFolderId)
          : [...currentFolders, targetFolderId]

        setArticleFolderMap((prev) => {
          const updated = new Map(prev)
          updated.set(key, newFolders)
          return updated
        })

        // Update folder counts
        setFolders((prev) =>
          prev.map((f) =>
            f.id === targetFolderId
              ? {
                  ...f,
                  [isPrivate ? 'private_article_count' : 'article_count']:
                    f[isPrivate ? 'private_article_count' : 'article_count'] + (isInFolder ? -1 : 1),
                  total_count: f.total_count + (isInFolder ? -1 : 1),
                }
              : f
          )
        )

        addNotification('success', isInFolder ? 'Removed from folder' : 'Added to folder')
      }
    } catch (error) {
      console.error('Failed to toggle folder:', error)
      addNotification('error', 'Failed to update folder')
    }
  }

  // Create a new folder
  const handleCreateFolder = async (name: string, description: string) => {
    const response = await fetch('/api/folders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to create folder')
    }

    const data = await response.json()
    setFolders((prev) => [...prev, data.folder].sort((a, b) => a.name.localeCompare(b.name)))
    addNotification('success', `Folder "${name}" created`)
  }

  const fetchAvailableSources = async () => {
    try {
      let data

      if (showMyArticlesOnly && user?.id) {
        // Fetch sources only from user's articles
        const { data: articleUsers, error: junctionError } = await supabase
          .from('article_users')
          .select('article_id')
          .eq('user_id', user.id)

        if (junctionError) throw junctionError

        const articleIds = articleUsers.map(au => au.article_id)

        if (articleIds.length === 0) {
          setAvailableSources([])
          return
        }

        const { data: articlesData, error: articlesError } = await supabase
          .from('articles')
          .select('source')
          .in('id', articleIds)

        if (articlesError) throw articlesError
        data = articlesData
      } else {
        // Fetch all sources
        const { data: allSources, error } = await supabase
          .from('articles')
          .select('source')

        if (error) throw error
        data = allSources
      }

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

  // Fetch available themes for the user's organization
  const fetchThemes = async () => {
    if (!user) return

    try {
      const response = await fetch('/api/themes')
      if (!response.ok) {
        throw new Error('Failed to fetch themes')
      }
      const data = await response.json()
      setAvailableThemes(data.themes || [])
    } catch (error) {
      console.error('Error fetching themes:', error)
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
      // Clear search state when fetching all articles
      sessionStorage.removeItem('articleSearchState')
      setSearchQuery('')
      setExtractedTerms([])

      let data

      // If filtering by folder, fetch articles from that folder
      if (folderId !== null) {
        // Fetch articles in the selected folder
        const [folderArticlesData, folderPrivateArticlesData] = await Promise.all([
          supabase
            .from('folder_articles')
            .select('article_id')
            .eq('folder_id', folderId),
          supabase
            .from('folder_private_articles')
            .select('private_article_id')
            .eq('folder_id', folderId),
        ])

        const publicArticleIds = folderArticlesData.data?.map((fa) => fa.article_id) || []
        const privateArticleIds = folderPrivateArticlesData.data?.map((fpa) => fpa.private_article_id) || []

        if (publicArticleIds.length === 0 && privateArticleIds.length === 0) {
          setArticles([])
          setTotalArticles(0)
          setTotalVideos(0)
          setTotalAudio(0)
          setTotalTextArticles(0)
          setHasLoaded(true)
          setLoading(false)
          return
        }

        setTotalArticles(publicArticleIds.length + privateArticleIds.length)

        // Fetch stats for folder articles
        const [videoCountPublic, audioCountPublic, articleCountPublic, videoCountPrivate, audioCountPrivate, articleCountPrivate] = await Promise.all([
          publicArticleIds.length > 0 ? supabase.from('articles').select('*', { count: 'exact', head: true }).in('id', publicArticleIds).eq('content_source', 'video') : Promise.resolve({ count: 0 }),
          publicArticleIds.length > 0 ? supabase.from('articles').select('*', { count: 'exact', head: true }).in('id', publicArticleIds).eq('content_source', 'audio') : Promise.resolve({ count: 0 }),
          publicArticleIds.length > 0 ? supabase.from('articles').select('*', { count: 'exact', head: true }).in('id', publicArticleIds).eq('content_source', 'article') : Promise.resolve({ count: 0 }),
          privateArticleIds.length > 0 ? supabase.from('private_articles').select('*', { count: 'exact', head: true }).in('id', privateArticleIds).eq('content_source', 'video') : Promise.resolve({ count: 0 }),
          privateArticleIds.length > 0 ? supabase.from('private_articles').select('*', { count: 'exact', head: true }).in('id', privateArticleIds).eq('content_source', 'audio') : Promise.resolve({ count: 0 }),
          privateArticleIds.length > 0 ? supabase.from('private_articles').select('*', { count: 'exact', head: true }).in('id', privateArticleIds).eq('content_source', 'article') : Promise.resolve({ count: 0 })
        ])

        setTotalVideos((videoCountPublic.count || 0) + (videoCountPrivate.count || 0))
        setTotalAudio((audioCountPublic.count || 0) + (audioCountPrivate.count || 0))
        setTotalTextArticles((articleCountPublic.count || 0) + (articleCountPrivate.count || 0))

        // Fetch article details
        const [publicArticlesData, privateArticlesData] = await Promise.all([
          publicArticleIds.length > 0
            ? supabase
                .from('articles')
                .select('id, title, url, summary_text, content_source, source, created_at, tags')
                .in('id', publicArticleIds)
            : Promise.resolve({ data: [] }),
          privateArticleIds.length > 0
            ? supabase
                .from('private_articles')
                .select('id, title, url, summary_text, content_source, source, created_at, tags')
                .in('id', privateArticleIds)
            : Promise.resolve({ data: [] })
        ])

        // Combine and tag articles
        const combinedArticles = [
          ...(publicArticlesData.data || []).map((article) => ({
            ...article,
            type: 'public' as const,
          })),
          ...(privateArticlesData.data || []).map((article) => ({
            ...article,
            type: 'private' as const,
          })),
        ]

        // Sort by created_at descending
        combinedArticles.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

        // Apply pagination
        const offset = (currentPage - 1) * articlesPerPage
        data = combinedArticles.slice(offset, offset + articlesPerPage)

        // Fetch folder memberships
        fetchArticleFolders(publicArticleIds, privateArticleIds)

        setArticles(data as any)
        setHasLoaded(true)
        setLoading(false)
        return
      }

      if (showMyArticlesOnly && user?.id) {
        // Fetch both public and private articles the user has saved

        // Fetch public articles via article_users junction table
        const { data: articleUsers, error: junctionError } = await supabase
          .from('article_users')
          .select('article_id, saved_at')
          .eq('user_id', user.id)

        if (junctionError) throw junctionError

        // Fetch private articles via private_article_users junction table
        const { data: privateArticleUsers, error: privateJunctionError } = await supabase
          .from('private_article_users')
          .select('private_article_id, saved_at')
          .eq('user_id', user.id)

        if (privateJunctionError) throw privateJunctionError

        const publicArticleIds = articleUsers.map(au => au.article_id)
        const privateArticleIds = privateArticleUsers.map(pau => pau.private_article_id)

        if (publicArticleIds.length === 0 && privateArticleIds.length === 0) {
          // User has no articles yet
          setArticles([])
          setTotalArticles(0)
          setHasLoaded(true)
          setLoading(false)
          return
        }

        // Set total count for pagination
        setTotalArticles(publicArticleIds.length + privateArticleIds.length)

        // Fetch content type breakdown for stats using count queries (both public and private)
        const [videoCountPublic, audioCountPublic, articleCountPublic, videoCountPrivate, audioCountPrivate, articleCountPrivate] = await Promise.all([
          publicArticleIds.length > 0 ? supabase.from('articles').select('*', { count: 'exact', head: true }).in('id', publicArticleIds).eq('content_source', 'video') : Promise.resolve({ count: 0 }),
          publicArticleIds.length > 0 ? supabase.from('articles').select('*', { count: 'exact', head: true }).in('id', publicArticleIds).eq('content_source', 'audio') : Promise.resolve({ count: 0 }),
          publicArticleIds.length > 0 ? supabase.from('articles').select('*', { count: 'exact', head: true }).in('id', publicArticleIds).eq('content_source', 'article') : Promise.resolve({ count: 0 }),
          privateArticleIds.length > 0 ? supabase.from('private_articles').select('*', { count: 'exact', head: true }).in('id', privateArticleIds).eq('content_source', 'video') : Promise.resolve({ count: 0 }),
          privateArticleIds.length > 0 ? supabase.from('private_articles').select('*', { count: 'exact', head: true }).in('id', privateArticleIds).eq('content_source', 'audio') : Promise.resolve({ count: 0 }),
          privateArticleIds.length > 0 ? supabase.from('private_articles').select('*', { count: 'exact', head: true }).in('id', privateArticleIds).eq('content_source', 'article') : Promise.resolve({ count: 0 })
        ])

        setTotalVideos((videoCountPublic.count || 0) + (videoCountPrivate.count || 0))
        setTotalAudio((audioCountPublic.count || 0) + (audioCountPrivate.count || 0))
        setTotalTextArticles((articleCountPublic.count || 0) + (articleCountPrivate.count || 0))

        // Fetch both public and private articles
        const [publicArticlesData, privateArticlesData] = await Promise.all([
          publicArticleIds.length > 0
            ? supabase
                .from('articles')
                .select('id, title, url, summary_text, content_source, source, created_at, tags')
                .in('id', publicArticleIds)
            : Promise.resolve({ data: [] }),
          privateArticleIds.length > 0
            ? supabase
                .from('private_articles')
                .select('id, title, url, summary_text, content_source, source, created_at, tags')
                .in('id', privateArticleIds)
            : Promise.resolve({ data: [] })
        ])

        if (publicArticlesData.error) throw publicArticlesData.error
        if (privateArticlesData.error) throw privateArticlesData.error

        // Combine and tag articles with type and saved_at
        const combinedArticles = [
          ...(publicArticlesData.data || []).map(article => ({
            ...article,
            type: 'public' as const,
            saved_at: articleUsers.find(au => au.article_id === article.id)?.saved_at
          })),
          ...(privateArticlesData.data || []).map(article => ({
            ...article,
            type: 'private' as const,
            saved_at: privateArticleUsers.find(pau => pau.private_article_id === article.id)?.saved_at
          }))
        ]

        // Sort by created_at descending
        combinedArticles.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

        // Apply pagination
        const offset = (currentPage - 1) * articlesPerPage
        data = combinedArticles.slice(offset, offset + articlesPerPage)
      } else {
        // Fetch all articles (both public and private, no user filter)
        // Get total counts first - both public and private
        const [publicCount, privateCount] = await Promise.all([
          supabase.from('articles').select('*', { count: 'exact', head: true }),
          supabase.from('private_articles').select('*', { count: 'exact', head: true })
        ])

        if (publicCount.error) throw publicCount.error
        setTotalArticles((publicCount.count || 0) + (privateCount.count || 0))

        // Fetch content type breakdown for stats using count queries (both public and private)
        const [videoCountPublic, audioCountPublic, articleCountPublic, videoCountPrivate, audioCountPrivate, articleCountPrivate] = await Promise.all([
          supabase.from('articles').select('*', { count: 'exact', head: true }).eq('content_source', 'video'),
          supabase.from('articles').select('*', { count: 'exact', head: true }).eq('content_source', 'audio'),
          supabase.from('articles').select('*', { count: 'exact', head: true }).eq('content_source', 'article'),
          supabase.from('private_articles').select('*', { count: 'exact', head: true }).eq('content_source', 'video'),
          supabase.from('private_articles').select('*', { count: 'exact', head: true }).eq('content_source', 'audio'),
          supabase.from('private_articles').select('*', { count: 'exact', head: true }).eq('content_source', 'article')
        ])

        setTotalVideos((videoCountPublic.count || 0) + (videoCountPrivate.count || 0))
        setTotalAudio((audioCountPublic.count || 0) + (audioCountPrivate.count || 0))
        setTotalTextArticles((articleCountPublic.count || 0) + (articleCountPrivate.count || 0))

        // Fetch both public and private articles
        const [publicArticlesData, privateArticlesData] = await Promise.all([
          supabase
            .from('articles')
            .select('id, title, url, summary_text, content_source, source, created_at, tags')
            .order('created_at', { ascending: false }),
          supabase
            .from('private_articles')
            .select('id, title, url, summary_text, content_source, source, created_at, tags')
            .order('created_at', { ascending: false })
        ])

        if (publicArticlesData.error) throw publicArticlesData.error

        // Combine and tag articles with type
        const combinedArticles = [
          ...(publicArticlesData.data || []).map(article => ({
            ...article,
            type: 'public' as const
          })),
          ...(privateArticlesData.data || []).map(article => ({
            ...article,
            type: 'private' as const
          }))
        ]

        // Sort by created_at descending
        combinedArticles.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

        // Apply pagination
        const offset = (currentPage - 1) * articlesPerPage
        data = combinedArticles.slice(offset, offset + articlesPerPage)
      }

      // Only update articles after we have the data
      if (data) {
        setArticles(data)
        // Fetch folder memberships for displayed articles
        const publicIds = data.filter((a: any) => a.type !== 'private').map((a: any) => a.id)
        const privateIds = data.filter((a: any) => a.type === 'private').map((a: any) => a.id)
        fetchArticleFolders(publicIds, privateIds)
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
      const { error } = await supabase
        .from('articles')
        .delete()
        .eq('id', id)

      if (error) throw error

      // Delete successful - remove from local state
      setArticles(articles.filter(article => article.id !== id))
      addNotification('success', 'Article deleted successfully!')
    } catch (error) {
      console.error('Error deleting article:', error)
      addNotification('error', `Failed to delete article: ${error.message}`)
    }
  }

  const performSearch = async (query: string, contentTypes: string[], sources: string[], from: string, to: string, themes: number[] = []) => {
    // Check if we have any filters applied
    const hasFilters = contentTypes.length > 0 || sources.length > 0 || from || to || showMyArticlesOnly || themes.length > 0

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
      if (showMyArticlesOnly && user?.id) filters.userId = user.id
      if (themes.length > 0) filters.themeIds = themes

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

      const { results, extractedTerms: terms } = await response.json()

      // Only update articles if we got results
      if (results) {
        setArticles(results)
      }

      // Store extracted terms for highlighting
      if (terms && Array.isArray(terms)) {
        setExtractedTerms(terms)
      } else {
        setExtractedTerms([])
      }

      // Save search state to sessionStorage for persistence
      const searchState = {
        query: query || '',
        mode: searchMode,
        articles: results || [],
        extractedTerms: terms || [],
        contentTypes,
        sources,
        dateFrom: from,
        dateTo: to
      }
      sessionStorage.setItem('articleSearchState', JSON.stringify(searchState))
    } catch (error) {
      console.error('Error searching articles:', error)
      addNotification('error', 'Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const searchArticles = async () => {
    await performSearch(searchQuery, selectedContentTypes, selectedSources, dateFrom, dateTo, selectedThemes)
  }

  const clearFilters = () => {
    setSelectedContentTypes([])
    setSelectedSources([])
    setSelectedThemes([])
    setDateFrom('')
    setDateTo('')
  }

  const toggleContentType = (type: string) => {
    setSelectedContentTypes(prev => {
      const newTypes = prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
      // Trigger search with the new state immediately
      setTimeout(() => performSearch(searchQuery, newTypes, selectedSources, dateFrom, dateTo, selectedThemes), 0)
      return newTypes
    })
  }

  const toggleSource = (source: string) => {
    setSelectedSources(prev => {
      const newSources = prev.includes(source) ? prev.filter(s => s !== source) : [...prev, source]
      // Trigger search with the new state immediately
      setTimeout(() => performSearch(searchQuery, selectedContentTypes, newSources, dateFrom, dateTo, selectedThemes), 0)
      return newSources
    })
  }

  const toggleTheme = (themeId: number) => {
    setSelectedThemes(prev => {
      const newThemes = prev.includes(themeId) ? prev.filter(t => t !== themeId) : [...prev, themeId]
      // Trigger search with the new state immediately
      setTimeout(() => performSearch(searchQuery, selectedContentTypes, selectedSources, dateFrom, dateTo, newThemes), 0)
      return newThemes
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
                  disabled={loading}
                  className="flex-1 sm:flex-none px-4 sm:px-6 py-2 text-white rounded-md focus:ring-2 transition-colors text-xs sm:text-sm bg-[#077331] hover:bg-[#055a24] focus:ring-[#077331] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading && (
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                  )}
                  {loading ? 'Searching...' : 'Search'}
                </button>
              </div>
            </div>

            {/* Filters Section */}
            {showFilters && (
              <div className="pt-4 border-t border-gray-200">
                {/* My Articles Filter */}
                {user && (
                  <div className="mb-4 pb-4 border-b border-gray-200">
                    <label className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={showMyArticlesOnly}
                        onChange={(e) => setShowMyArticlesOnly(e.target.checked)}
                        className="rounded border-gray-300 text-[#077331] focus:ring-[#077331]"
                      />
                      <span className="ml-2 text-sm font-medium text-gray-700">My Articles Only</span>
                      <span className="ml-2 text-xs text-gray-500 italic">
                        ({showMyArticlesOnly ? 'Showing only your saved articles' : 'Showing all articles'})
                      </span>
                    </label>
                  </div>
                )}

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

                  {/* Theme Filter (only shown if themes exist) */}
                  {availableThemes.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Themes</label>
                      <div className="space-y-2">
                        {availableThemes.map(theme => (
                          <label key={theme.id} className="flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              checked={selectedThemes.includes(theme.id)}
                              onChange={() => toggleTheme(theme.id)}
                              className="rounded border-gray-300 text-[#077331] focus:ring-[#077331]"
                            />
                            <span className="ml-2 text-sm text-gray-700">{theme.name}</span>
                            <span className="ml-auto text-xs text-gray-500">({theme.article_count})</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

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
                        setTimeout(() => performSearch(searchQuery, selectedContentTypes, selectedSources, newDateFrom, dateTo, selectedThemes), 0)
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
                        setTimeout(() => performSearch(searchQuery, selectedContentTypes, selectedSources, dateFrom, newDateTo, selectedThemes), 0)
                      }}
                      className="w-full px-3 py-2 border border-[#e2e8f0] rounded-md focus:ring-2 focus:ring-[#077331]"
                    />
                  </div>
                </div>

                {/* Active Filters Display */}
                {(selectedContentTypes.length > 0 || selectedSources.length > 0 || selectedThemes.length > 0 || dateFrom || dateTo) && (
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
                    {selectedThemes.map(themeId => {
                      const theme = availableThemes.find(t => t.id === themeId)
                      return theme ? (
                        <span key={themeId} className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm border border-blue-300">
                          {theme.name}
                          <button onClick={() => toggleTheme(themeId)} className="hover:text-blue-900">
                            <X className="h-3 w-3" />
                          </button>
                        </span>
                      ) : null
                    })}
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
            <div className="text-xl sm:text-2xl font-bold text-[#077331]">{totalArticles}</div>
            <div className="text-xs sm:text-sm text-[#475569]">Total Articles</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 border border-[#e2e8f0]">
            <div className="text-xl sm:text-2xl font-bold text-[#077331]">
              {totalVideos}
            </div>
            <div className="text-xs sm:text-sm text-[#475569]">Videos</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 border border-[#e2e8f0]">
            <div className="text-xl sm:text-2xl font-bold text-[#077331]">
              {totalAudio}
            </div>
            <div className="text-xs sm:text-sm text-[#475569]">Audio</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4 sm:p-6 border border-[#e2e8f0]">
            <div className="text-xl sm:text-2xl font-bold text-[#077331]">
              {totalTextArticles}
            </div>
            <div className="text-xs sm:text-sm text-[#475569]">Articles</div>
          </div>
        </div>

        {/* Pagination Controls - Top */}
        {!loading && totalArticles > articlesPerPage && (
          <div className="mb-6 flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-lg shadow-md border border-[#e2e8f0]">
            {/* Page info */}
            <div className="text-sm text-gray-600">
              Showing {((currentPage - 1) * articlesPerPage) + 1} to {Math.min(currentPage * articlesPerPage, totalArticles)} of {totalArticles} articles
            </div>

            {/* Pagination buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50 disabled:hover:bg-white"
              >
                First
              </button>

              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50 disabled:hover:bg-white"
              >
                Previous
              </button>

              {/* Page numbers */}
              <div className="hidden sm:flex items-center gap-1">
                {Array.from({ length: Math.min(5, Math.ceil(totalArticles / articlesPerPage)) }, (_, i) => {
                  const totalPages = Math.ceil(totalArticles / articlesPerPage)
                  let pageNum

                  if (totalPages <= 5) {
                    // Show all pages if 5 or fewer
                    pageNum = i + 1
                  } else if (currentPage <= 3) {
                    // Near the start
                    pageNum = i + 1
                  } else if (currentPage >= totalPages - 2) {
                    // Near the end
                    pageNum = totalPages - 4 + i
                  } else {
                    // In the middle
                    pageNum = currentPage - 2 + i
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        currentPage === pageNum
                          ? 'bg-[#077331] text-white'
                          : 'bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  )
                })}
              </div>

              {/* Current page indicator for mobile */}
              <div className="sm:hidden px-3 py-2 bg-[#077331] text-white rounded-md text-sm font-medium">
                {currentPage} / {Math.ceil(totalArticles / articlesPerPage)}
              </div>

              <button
                onClick={() => setCurrentPage(prev => Math.min(Math.ceil(totalArticles / articlesPerPage), prev + 1))}
                disabled={currentPage >= Math.ceil(totalArticles / articlesPerPage)}
                className="px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50 disabled:hover:bg-white"
              >
                Next
              </button>

              <button
                onClick={() => setCurrentPage(Math.ceil(totalArticles / articlesPerPage))}
                disabled={currentPage >= Math.ceil(totalArticles / articlesPerPage)}
                className="px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50 disabled:hover:bg-white"
              >
                Last
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Articles List */}
      <div className="relative">
        {/* Loading overlay when searching with existing results */}
        {loading && articles.length > 0 && (
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10 rounded-lg">
            <div className="text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-[#077331] mx-auto"></div>
              <p className="mt-4 text-gray-600 font-medium">Searching...</p>
            </div>
          </div>
        )}

        {loading && articles.length === 0 ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading articles...</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:gap-6">
          {articles.map((article) => {
            // Determine article path based on type
            const articlePath = (article as any).type === 'private'
              ? `/private-article/${article.id}`
              : `/article/${article.id}`
            const queryString = searchQuery
              ? `?q=${encodeURIComponent(searchQuery)}&mode=${searchMode}${extractedTerms.length > 0 ? `&terms=${encodeURIComponent(extractedTerms.join(','))}` : ''}`
              : ''

            return (
              <div key={`${(article as any).type || 'public'}-${article.id}`} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow border border-[#e2e8f0]">
                <div className="p-4 sm:p-6">
                  <div className="flex justify-between items-start mb-3 sm:mb-4 gap-2">
                    <Link
                      href={`${articlePath}${queryString}`}
                      className="flex-1 min-w-0"
                    >
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
                      <>
                        <AddToFolderDropdown
                          articleId={article.id}
                          isPrivate={(article as any).type === 'private'}
                          folders={folders}
                          articleFolderIds={articleFolderMap.get(`${(article as any).type === 'private' ? 'private' : 'public'}-${article.id}`) || []}
                          onToggleFolder={(targetFolderId, isInFolder) =>
                            handleToggleFolder(article.id, (article as any).type === 'private', targetFolderId, isInFolder)
                          }
                          onCreateFolder={() => setShowCreateFolderModal(true)}
                        />
                        <button
                          onClick={() => deleteArticle(article.id)}
                          className="p-1.5 sm:p-2 text-gray-500 hover:text-red-600 transition-colors"
                          title="Delete article"
                        >
                          <Trash2 className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                        </button>
                      </>
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
                  {/* Folder badges */}
                  {(() => {
                    const articleKey = `${(article as any).type === 'private' ? 'private' : 'public'}-${article.id}`
                    const folderIds = articleFolderMap.get(articleKey) || []
                    return folderIds.map((fId) => {
                      const folder = folders.find((f) => f.id === fId)
                      if (!folder) return null
                      return (
                        <Link
                          key={fId}
                          href={`/folder/${encodeURIComponent(folder.name)}`}
                          className="px-2 py-0.5 sm:py-1 bg-[#077331] text-white rounded-full text-xs font-medium hover:bg-[#055a24] transition-colors"
                        >
                          {folder.name}
                        </Link>
                      )
                    })
                  })()}
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
          )
        })}

          {articles.length === 0 && !loading && hasLoaded && (
            <div className="text-center py-12">
              <p className="text-gray-600">No articles found</p>
            </div>
          )}
        </div>
        )}

        {/* Pagination Controls - Bottom */}
        {!loading && totalArticles > articlesPerPage && (
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-lg shadow-md border border-[#e2e8f0]">
            {/* Page info */}
            <div className="text-sm text-gray-600">
              Showing {((currentPage - 1) * articlesPerPage) + 1} to {Math.min(currentPage * articlesPerPage, totalArticles)} of {totalArticles} articles
            </div>

            {/* Pagination buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50 disabled:hover:bg-white"
              >
                First
              </button>

              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50 disabled:hover:bg-white"
              >
                Previous
              </button>

              {/* Page numbers */}
              <div className="hidden sm:flex items-center gap-1">
                {Array.from({ length: Math.min(5, Math.ceil(totalArticles / articlesPerPage)) }, (_, i) => {
                  const totalPages = Math.ceil(totalArticles / articlesPerPage)
                  let pageNum

                  if (totalPages <= 5) {
                    // Show all pages if 5 or fewer
                    pageNum = i + 1
                  } else if (currentPage <= 3) {
                    // Near the start
                    pageNum = i + 1
                  } else if (currentPage >= totalPages - 2) {
                    // Near the end
                    pageNum = totalPages - 4 + i
                  } else {
                    // In the middle
                    pageNum = currentPage - 2 + i
                  }

                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        currentPage === pageNum
                          ? 'bg-[#077331] text-white'
                          : 'bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  )
                })}
              </div>

              {/* Current page indicator for mobile */}
              <div className="sm:hidden px-3 py-2 bg-[#077331] text-white rounded-md text-sm font-medium">
                {currentPage} / {Math.ceil(totalArticles / articlesPerPage)}
              </div>

              <button
                onClick={() => setCurrentPage(prev => Math.min(Math.ceil(totalArticles / articlesPerPage), prev + 1))}
                disabled={currentPage >= Math.ceil(totalArticles / articlesPerPage)}
                className="px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50 disabled:hover:bg-white"
              >
                Next
              </button>

              <button
                onClick={() => setCurrentPage(Math.ceil(totalArticles / articlesPerPage))}
                disabled={currentPage >= Math.ceil(totalArticles / articlesPerPage)}
                className="px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-white text-gray-700 border border-[#e2e8f0] hover:bg-gray-50 disabled:hover:bg-white"
              >
                Last
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create Folder Modal */}
      <CreateFolderModal
        isOpen={showCreateFolderModal}
        onClose={() => setShowCreateFolderModal(false)}
        onSave={handleCreateFolder}
      />
    </div>
  )
}