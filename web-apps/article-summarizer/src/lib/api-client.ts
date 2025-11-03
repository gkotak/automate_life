/**
 * API Client Utility
 *
 * Provides authenticated fetch functions for backend API calls
 * Automatically includes Supabase JWT token in requests
 */

import { supabase } from './supabase'

/**
 * Get the current user's auth token
 * @returns JWT access token or null if not authenticated
 */
async function getAuthToken(): Promise<string | null> {
  const { data: { session }, error } = await supabase.auth.getSession()

  if (error) {
    console.error('Error getting session:', error)
    return null
  }

  return session?.access_token || null
}

/**
 * Authenticated fetch to Article Summarizer Backend
 * @param endpoint - API endpoint (e.g., '/process-article')
 * @param options - Fetch options
 * @returns Fetch response
 */
export async function fetchArticleBackend(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getAuthToken()

  if (!token) {
    throw new Error('Not authenticated. Please sign in.')
  }

  const baseUrl = process.env.NEXT_PUBLIC_ARTICLE_BACKEND_URL || 'http://localhost:8000'
  const url = `${baseUrl}${endpoint}`

  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${token}`)
  headers.set('Content-Type', 'application/json')

  return fetch(url, {
    ...options,
    headers,
  })
}

/**
 * Authenticated fetch to Content Checker Backend
 * @param endpoint - API endpoint (e.g., '/posts/check')
 * @param options - Fetch options
 * @returns Fetch response
 */
export async function fetchContentCheckerBackend(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getAuthToken()

  if (!token) {
    throw new Error('Not authenticated. Please sign in.')
  }

  const baseUrl = process.env.NEXT_PUBLIC_CONTENT_CHECKER_BACKEND_URL || 'http://localhost:8001'
  const url = `${baseUrl}${endpoint}`

  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${token}`)
  headers.set('Content-Type', 'application/json')

  return fetch(url, {
    ...options,
    headers,
  })
}

/**
 * Process an article via the Article Summarizer Backend
 * @param articleUrl - URL of the article to process
 * @param forceReprocess - Whether to reprocess if article already exists
 * @returns Article ID
 */
export async function processArticle(
  articleUrl: string,
  forceReprocess: boolean = false
): Promise<{ article_id: number; status: string; message: string }> {
  const response = await fetchArticleBackend('/process-article', {
    method: 'POST',
    body: JSON.stringify({ url: articleUrl }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || 'Failed to process article')
  }

  return response.json()
}

/**
 * Check for new posts via the Content Checker Backend
 * @returns Check results
 */
export async function checkNewPosts(): Promise<{
  message: string
  new_posts_found: number
  total_sources_checked: number
  newly_discovered_ids: string[]
}> {
  const response = await fetchContentCheckerBackend('/posts/check', {
    method: 'POST',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || 'Failed to check posts')
  }

  return response.json()
}

/**
 * Get discovered posts from the Content Checker Backend
 * @param limit - Maximum number of posts to return
 * @returns List of discovered posts
 */
export async function getDiscoveredPosts(limit: number = 200): Promise<{
  posts: Array<{
    id: string
    title: string
    url: string
    channel_title?: string
    channel_url?: string
    platform: string
    source_feed?: string
    published_date?: string
    found_at: string
    status: string
  }>
  total: number
}> {
  const response = await fetchContentCheckerBackend(`/posts/discovered?limit=${limit}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || 'Failed to get discovered posts')
  }

  return response.json()
}

/**
 * Content Source types
 */
export interface ContentSource {
  id: number
  name: string
  url: string
  description?: string
  is_active: boolean
  source_type: string
  user_id: string
  created_at: string
  updated_at?: string
  last_checked_at?: string
}

export interface ContentSourceCreate {
  name: string
  url: string
  description?: string
  is_active?: boolean
  source_type?: string
}

export interface ContentSourceUpdate {
  name?: string
  url?: string
  description?: string
  is_active?: boolean
  source_type?: string
}

/**
 * Get all content sources for the current user
 * @param includeInactive - Whether to include inactive sources
 * @returns List of content sources
 */
export async function getContentSources(includeInactive: boolean = false): Promise<{
  sources: ContentSource[]
  total: number
}> {
  const response = await fetchContentCheckerBackend(
    `/sources?include_inactive=${includeInactive}`
  )

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || 'Failed to get content sources')
  }

  return response.json()
}

/**
 * Get a specific content source by ID
 * @param sourceId - ID of the content source
 * @returns Content source details
 */
export async function getContentSource(sourceId: number): Promise<{
  source: ContentSource
}> {
  const response = await fetchContentCheckerBackend(`/sources/${sourceId}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || 'Failed to get content source')
  }

  return response.json()
}

/**
 * Create a new content source
 * @param source - Content source data
 * @returns Created content source
 */
export async function createContentSource(source: ContentSourceCreate): Promise<{
  source: ContentSource
  message?: string
}> {
  const response = await fetchContentCheckerBackend('/sources', {
    method: 'POST',
    body: JSON.stringify(source),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || 'Failed to create content source')
  }

  return response.json()
}

/**
 * Update an existing content source
 * @param sourceId - ID of the content source
 * @param updates - Fields to update
 * @returns Updated content source
 */
export async function updateContentSource(
  sourceId: number,
  updates: ContentSourceUpdate
): Promise<{
  source: ContentSource
  message?: string
}> {
  const response = await fetchContentCheckerBackend(`/sources/${sourceId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || 'Failed to update content source')
  }

  return response.json()
}

/**
 * Delete a content source
 * @param sourceId - ID of the content source
 */
export async function deleteContentSource(sourceId: number): Promise<void> {
  const response = await fetchContentCheckerBackend(`/sources/${sourceId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || 'Failed to delete content source')
  }
}
