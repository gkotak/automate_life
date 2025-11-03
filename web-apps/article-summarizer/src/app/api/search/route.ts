import { createClient } from '@supabase/supabase-js';
import { NextRequest, NextResponse } from 'next/server';
import { generateEmbedding } from '@/lib/embeddings';
import Anthropic from '@anthropic-ai/sdk';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
);

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

interface SearchFilters {
  contentTypes?: string[]
  sources?: string[]
  dateFrom?: string
  dateTo?: string
  userId?: string  // Filter by user's articles only
}

/**
 * Extract key terms from search query for highlighting
 */
async function extractKeyTerms(query: string): Promise<string[]> {
  try {
    const message = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 500,
      messages: [
        {
          role: 'user',
          content: `Extract key terms and their common synonyms/variations from this search query for text highlighting purposes.

Search query: "${query}"

Return ONLY a JSON array of strings containing:
1. The main keywords from the query
2. Common synonyms and variations
3. Common abbreviations/acronyms
4. Related terms that would be semantically relevant

Keep terms concise (1-3 words max each). Focus on terms that would actually appear in article text.

Example input: "How does AI impact healthcare?"
Example output: ["AI", "artificial intelligence", "machine learning", "healthcare", "health", "medical", "medicine", "clinical", "patient care"]

Output format: Just the JSON array, nothing else.`
        }
      ]
    });

    const content = message.content[0];
    if (content.type !== 'text') {
      return query.toLowerCase().split(/\s+/).filter(word => word.length > 2);
    }

    // Parse JSON from Claude's response
    let jsonText = content.text.trim();
    jsonText = jsonText.replace(/```json\n?/g, '').replace(/```\n?/g, '');

    const terms = JSON.parse(jsonText);

    if (!Array.isArray(terms) || !terms.every(t => typeof t === 'string')) {
      return query.toLowerCase().split(/\s+/).filter(word => word.length > 2);
    }

    // Deduplicate and limit
    return [...new Set(terms.map(t => t.toLowerCase()))].slice(0, 20);
  } catch (error) {
    console.error('Failed to extract terms:', error);
    // Fallback to simple word splitting
    return query.toLowerCase().split(/\s+/).filter(word => word.length > 2);
  }
}

export async function POST(request: NextRequest) {
  try {
    const {
      query,
      limit = 20,
      mode = 'semantic',
      filters = {}
    }: {
      query: string
      limit?: number
      mode?: 'semantic' | 'keyword' | 'hybrid'
      filters?: SearchFilters
    } = await request.json();

    let results: any[] = []
    let extractedTerms: string[] = []

    // Extract key terms for hybrid search mode (do this once at search time)
    if (query && query.trim().length > 0 && mode === 'hybrid') {
      extractedTerms = await extractKeyTerms(query);
      console.log('Extracted terms for highlighting:', extractedTerms);
    }

    // If no query but we have filters, fetch all articles and apply filters
    if (!query || query.trim().length === 0) {
      const { data: allArticles, error } = await supabase
        .from('articles')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100)

      if (error) {
        console.error('Fetch error:', error);
        return NextResponse.json(
          { error: 'Fetch failed', details: error.message },
          { status: 500 }
        );
      }

      results = allArticles || []
    } else {
      // We have a query, perform search
      if (mode === 'semantic' || mode === 'hybrid') {
        // Generate embedding for semantic search using wrapped OpenAI client
        const queryEmbedding = await generateEmbedding(query);

        // Semantic search
        const { data: semanticResults, error } = await supabase.rpc('search_articles', {
          query_embedding: queryEmbedding,
          match_threshold: 0.3,
          match_count: limit * 2,
        });

        if (error) {
          console.error('Search error:', error);
          return NextResponse.json(
            { error: 'Search failed', details: error.message },
            { status: 500 }
          );
        }

        results = semanticResults || []
      }

      if (mode === 'keyword' || mode === 'hybrid') {
      // Keyword search
      let keywordQuery = supabase
        .from('articles')
        .select('*')
        .or(`title.ilike.%${query}%,summary_text.ilike.%${query}%,transcript_text.ilike.%${query}%`)
        .order('created_at', { ascending: false })
        .limit(mode === 'keyword' ? limit : limit * 2)

      const { data: keywordResults, error: kwError } = await keywordQuery

      if (kwError) {
        console.error('Keyword search error:', kwError);
      } else if (keywordResults) {
        if (mode === 'hybrid') {
          // Merge results, prioritizing semantic matches but including keyword matches
          const resultMap = new Map()

          // Add semantic results first (with similarity scores)
          results.forEach(r => resultMap.set(r.id, { ...r, source: 'semantic' }))

          // Add keyword results (without duplicates)
          keywordResults.forEach(r => {
            if (!resultMap.has(r.id)) {
              resultMap.set(r.id, { ...r, similarity: 0.5, source: 'keyword' })
            }
          })

          results = Array.from(resultMap.values())
        } else {
          results = keywordResults
        }
      }
    }
    }

    // Apply user filter first if specified
    if (filters.userId) {
      // Fetch article IDs for this user
      const { data: articleUsers, error: junctionError } = await supabase
        .from('article_users')
        .select('article_id')
        .eq('user_id', filters.userId)

      if (junctionError) {
        console.error('User filter error:', junctionError);
      } else if (articleUsers) {
        const userArticleIds = new Set(articleUsers.map(au => au.article_id))
        results = results.filter(r => userArticleIds.has(r.id))
      }
    }

    // Apply other filters
    if (filters.contentTypes && filters.contentTypes.length > 0) {
      results = results.filter(r => filters.contentTypes!.includes(r.content_source))
    }

    if (filters.sources && filters.sources.length > 0) {
      results = results.filter(r => filters.sources!.includes(r.source))
    }

    if (filters.dateFrom) {
      results = results.filter(r => new Date(r.created_at) >= new Date(filters.dateFrom!))
    }

    if (filters.dateTo) {
      results = results.filter(r => new Date(r.created_at) <= new Date(filters.dateTo!))
    }

    // Sort by similarity if available, otherwise by date
    results.sort((a, b) => {
      if (a.similarity !== undefined && b.similarity !== undefined) {
        return b.similarity - a.similarity
      }
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })

    // Limit final results
    results = results.slice(0, limit)

    return NextResponse.json({
      results,
      count: results.length,
      extractedTerms: extractedTerms.length > 0 ? extractedTerms : undefined
    });
  } catch (error) {
    console.error('Search API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
