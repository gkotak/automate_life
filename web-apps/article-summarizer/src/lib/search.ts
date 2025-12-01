/**
 * Article Search Utilities
 *
 * Shared functions for searching articles using semantic (vector) and keyword search.
 */

import { supabase } from '@/lib/supabase'
import { generateEmbedding } from './embeddings'

export interface ArticleSearchResult {
  id: number
  title: string
  url: string
  summary_text: string
  transcript_text?: string
  key_insights?: any
  quotes?: any
  content_source: string
  platform?: string
  source?: string
  created_at: string
  similarity?: number
  type?: 'public' | 'private'  // Distinguishes between public and private articles
}

export interface SearchOptions {
  matchThreshold?: number
  matchCount?: number
  includePrivate?: boolean  // Include private articles in search results
}

const DEFAULT_SEARCH_OPTIONS: SearchOptions = {
  matchThreshold: 0.3,
  matchCount: 10,
  includePrivate: true  // Default to including private articles
}

/**
 * Performs semantic search on articles using vector similarity.
 * Searches both public and private articles (based on options).
 *
 * @param query - The search query text
 * @param options - Optional search configuration
 * @returns Array of matching articles with similarity scores
 */
export async function searchArticlesBySemantic(
  query: string,
  options: SearchOptions = {}
): Promise<ArticleSearchResult[]> {
  const { matchThreshold, matchCount, includePrivate } = { ...DEFAULT_SEARCH_OPTIONS, ...options }

  // Generate embedding for the query
  const queryEmbedding = await generateEmbedding(query)

  // Search public articles
  const publicSearchPromise = supabase.rpc('search_articles', {
    query_embedding: queryEmbedding,
    match_threshold: matchThreshold,
    match_count: matchCount,
  })

  // Search private articles if requested
  const privateSearchPromise = includePrivate
    ? supabase.rpc('search_private_articles', {
        query_embedding: queryEmbedding,
        match_threshold: matchThreshold,
        match_count: matchCount,
      })
    : Promise.resolve({ data: [], error: null })

  // Run searches in parallel
  const [publicResult, privateResult] = await Promise.all([publicSearchPromise, privateSearchPromise])

  if (publicResult.error) {
    throw new Error(`Public semantic search failed: ${publicResult.error.message}`)
  }

  if (privateResult.error) {
    console.error('Private semantic search failed:', privateResult.error.message)
    // Don't throw - just use public results if private search fails
  }

  // Tag results with their type and merge
  const publicArticles = (publicResult.data || []).map((a: ArticleSearchResult) => ({
    ...a,
    type: 'public' as const
  }))

  const privateArticles = (privateResult.data || []).map((a: ArticleSearchResult) => ({
    ...a,
    type: 'private' as const
  }))

  // Combine and sort by similarity
  const allResults = [...publicArticles, ...privateArticles]
    .sort((a, b) => (b.similarity || 0) - (a.similarity || 0))
    .slice(0, matchCount)

  return allResults
}

/**
 * Performs keyword-based search on articles.
 * Searches both public and private articles.
 *
 * @param query - The search query text
 * @param limit - Maximum number of results to return
 * @param includePrivate - Whether to include private articles (default: true)
 * @returns Array of matching articles
 */
export async function searchArticlesByKeyword(
  query: string,
  limit: number = 10,
  includePrivate: boolean = true
): Promise<ArticleSearchResult[]> {
  // Search public articles
  const publicSearchPromise = supabase
    .from('articles')
    .select('*')
    .or(`title.ilike.%${query}%,summary_text.ilike.%${query}%,transcript_text.ilike.%${query}%`)
    .order('created_at', { ascending: false })
    .limit(limit)

  // Search private articles if requested
  const privateSearchPromise = includePrivate
    ? supabase
        .from('private_articles')
        .select('*')
        .or(`title.ilike.%${query}%,summary_text.ilike.%${query}%,transcript_text.ilike.%${query}%`)
        .order('created_at', { ascending: false })
        .limit(limit)
    : Promise.resolve({ data: [], error: null })

  const [publicResult, privateResult] = await Promise.all([publicSearchPromise, privateSearchPromise])

  if (publicResult.error) {
    throw new Error(`Public keyword search failed: ${publicResult.error.message}`)
  }

  if (privateResult.error) {
    console.error('Private keyword search failed:', privateResult.error.message)
  }

  // Tag results with their type
  const publicArticles = (publicResult.data || []).map((a: ArticleSearchResult) => ({
    ...a,
    type: 'public' as const
  }))

  const privateArticles = (privateResult.data || []).map((a: ArticleSearchResult) => ({
    ...a,
    type: 'private' as const
  }))

  // Combine and sort by date, limit to requested count
  const allResults = [...publicArticles, ...privateArticles]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, limit)

  return allResults
}

/**
 * Performs hybrid search combining semantic and keyword search.
 * Searches both public and private articles.
 *
 * @param query - The search query text
 * @param options - Optional search configuration
 * @returns Array of matching articles with similarity scores
 */
export async function searchArticlesHybrid(
  query: string,
  options: SearchOptions = {}
): Promise<ArticleSearchResult[]> {
  const { matchCount = 10, includePrivate = true } = options

  // Run both searches (they now internally search both public and private)
  const [semanticResults, keywordResults] = await Promise.all([
    searchArticlesBySemantic(query, { ...options, matchCount: matchCount * 2, includePrivate }),
    searchArticlesByKeyword(query, matchCount * 2, includePrivate)
  ])

  // Merge results, using composite key (type + id) to handle duplicates correctly
  const resultMap = new Map<string, ArticleSearchResult>()

  // Add semantic results first (with similarity scores)
  semanticResults.forEach(result => {
    const key = `${result.type}-${result.id}`
    resultMap.set(key, { ...result, similarity: result.similarity })
  })

  // Add keyword results (without duplicates)
  keywordResults.forEach(result => {
    const key = `${result.type}-${result.id}`
    if (!resultMap.has(key)) {
      resultMap.set(key, { ...result, similarity: 0.5 })
    }
  })

  // Sort by similarity and limit
  const results = Array.from(resultMap.values())
    .sort((a, b) => (b.similarity || 0) - (a.similarity || 0))
    .slice(0, matchCount)

  return results
}

/**
 * Finds articles similar to a given article using its embedding.
 *
 * @param articleId - The ID of the article to find similar articles for
 * @param limit - Maximum number of similar articles to return
 * @param minSimilarity - Minimum similarity threshold (0-1)
 * @returns Array of similar articles
 */
export async function findSimilarArticles(
  articleId: number,
  limit: number = 5,
  minSimilarity: number = 0.5
): Promise<ArticleSearchResult[]> {
  // Get the article's embedding
  const { data: article, error: articleError } = await supabase
    .from('articles')
    .select('embedding')
    .eq('id', articleId)
    .single()

  if (articleError || !article || !article.embedding) {
    throw new Error(`Article not found or has no embedding: ${articleId}`)
  }

  // Find similar articles
  const { data, error } = await supabase.rpc('search_articles', {
    query_embedding: article.embedding,
    match_threshold: minSimilarity,
    match_count: limit + 1, // +1 to account for the article itself
  })

  if (error) {
    throw new Error(`Similar articles search failed: ${error.message}`)
  }

  // Filter out the original article
  const results = (data || [])
    .filter((a: ArticleSearchResult) => a.id !== articleId && a.similarity && a.similarity >= minSimilarity)
    .slice(0, limit)

  return results
}
