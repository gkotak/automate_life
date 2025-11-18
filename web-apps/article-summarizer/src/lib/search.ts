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
}

export interface SearchOptions {
  matchThreshold?: number
  matchCount?: number
}

const DEFAULT_SEARCH_OPTIONS: SearchOptions = {
  matchThreshold: 0.3,
  matchCount: 10
}

/**
 * Performs semantic search on articles using vector similarity.
 *
 * @param query - The search query text
 * @param options - Optional search configuration
 * @returns Array of matching articles with similarity scores
 */
export async function searchArticlesBySemantic(
  query: string,
  options: SearchOptions = {}
): Promise<ArticleSearchResult[]> {
  const { matchThreshold, matchCount } = { ...DEFAULT_SEARCH_OPTIONS, ...options }

  // Generate embedding for the query
  const queryEmbedding = await generateEmbedding(query)

  // Perform vector similarity search
  const { data, error } = await supabase.rpc('search_articles', {
    query_embedding: queryEmbedding,
    match_threshold: matchThreshold,
    match_count: matchCount,
  })

  if (error) {
    throw new Error(`Semantic search failed: ${error.message}`)
  }

  return data || []
}

/**
 * Performs keyword-based search on articles.
 *
 * @param query - The search query text
 * @param limit - Maximum number of results to return
 * @returns Array of matching articles
 */
export async function searchArticlesByKeyword(
  query: string,
  limit: number = 10
): Promise<ArticleSearchResult[]> {
  const { data, error } = await supabase
    .from('articles')
    .select('*')
    .or(`title.ilike.%${query}%,summary_text.ilike.%${query}%,transcript_text.ilike.%${query}%`)
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) {
    throw new Error(`Keyword search failed: ${error.message}`)
  }

  return data || []
}

/**
 * Performs hybrid search combining semantic and keyword search.
 *
 * @param query - The search query text
 * @param options - Optional search configuration
 * @returns Array of matching articles with similarity scores
 */
export async function searchArticlesHybrid(
  query: string,
  options: SearchOptions = {}
): Promise<ArticleSearchResult[]> {
  const { matchCount = 10 } = options

  // Run both searches
  const [semanticResults, keywordResults] = await Promise.all([
    searchArticlesBySemantic(query, { ...options, matchCount: matchCount * 2 }),
    searchArticlesByKeyword(query, matchCount * 2)
  ])

  // Merge results, prioritizing semantic matches
  const resultMap = new Map<number, ArticleSearchResult>()

  // Add semantic results first (with similarity scores)
  semanticResults.forEach(result => {
    resultMap.set(result.id, { ...result, similarity: result.similarity })
  })

  // Add keyword results (without duplicates)
  keywordResults.forEach(result => {
    if (!resultMap.has(result.id)) {
      resultMap.set(result.id, { ...result, similarity: 0.5 })
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
