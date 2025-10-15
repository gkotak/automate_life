import { createClient } from '@supabase/supabase-js';
import { NextRequest, NextResponse } from 'next/server';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

interface SearchFilters {
  contentTypes?: string[]
  platforms?: string[]
  dateFrom?: string
  dateTo?: string
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
        // Generate embedding for semantic search
        const openaiApiKey = process.env.OPENAI_API_KEY;
        if (!openaiApiKey) {
          return NextResponse.json(
            { error: 'OpenAI API key not configured' },
            { status: 500 }
          );
        }

        const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${openaiApiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            input: query,
            model: 'text-embedding-3-small',
            dimensions: 384,
          }),
        });

        if (!embeddingResponse.ok) {
          throw new Error('Failed to generate embedding');
        }

        const embeddingData = await embeddingResponse.json();
        const queryEmbedding = embeddingData.data[0].embedding;

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

    // Apply filters
    if (filters.contentTypes && filters.contentTypes.length > 0) {
      results = results.filter(r => filters.contentTypes!.includes(r.content_source))
    }

    if (filters.platforms && filters.platforms.length > 0) {
      results = results.filter(r => filters.platforms!.includes(r.platform))
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

    return NextResponse.json({ results, count: results.length });
  } catch (error) {
    console.error('Search API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
