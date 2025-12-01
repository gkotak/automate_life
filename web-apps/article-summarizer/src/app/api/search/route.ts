import { createClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';
import { generateEmbedding } from '@/lib/embeddings';
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

interface SearchFilters {
  contentTypes?: string[]
  sources?: string[]
  dateFrom?: string
  dateTo?: string
  userId?: string  // Filter by user's articles only
  themeIds?: number[]  // Filter by themes (OR logic - articles with insights for ANY selected theme)
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

    const supabase = await createClient();

    let results: any[] = []
    let extractedTerms: string[] = []

    // Extract key terms for hybrid search mode (do this once at search time)
    if (query && query.trim().length > 0 && mode === 'hybrid') {
      extractedTerms = await extractKeyTerms(query);
      console.log('Extracted terms for highlighting:', extractedTerms);
    }

    // If no query but we have filters, fetch all articles and apply filters
    if (!query || query.trim().length === 0) {
      // Fetch both public and private articles in parallel
      const [publicResult, privateResult] = await Promise.all([
        supabase
          .from('articles')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(100),
        supabase
          .from('private_articles')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(100)
      ]);

      if (publicResult.error) {
        console.error('Fetch public error:', publicResult.error);
        return NextResponse.json(
          { error: 'Fetch failed', details: publicResult.error.message },
          { status: 500 }
        );
      }

      // Tag articles with their type
      const publicArticles = (publicResult.data || []).map((a: any) => ({ ...a, type: 'public' }));
      const privateArticles = (privateResult.data || []).map((a: any) => ({ ...a, type: 'private' }));

      // Combine and sort by date
      results = [...publicArticles, ...privateArticles]
        .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 100);
    } else {
      // We have a query, perform search
      if (mode === 'semantic' || mode === 'hybrid') {
        // Generate embedding for semantic search using wrapped OpenAI client
        const queryEmbedding = await generateEmbedding(query);

        // Semantic search - both public and private articles in parallel
        const [publicSemanticResult, privateSemanticResult] = await Promise.all([
          supabase.rpc('search_articles', {
            query_embedding: queryEmbedding,
            match_threshold: 0.3,
            match_count: limit * 2,
          }),
          supabase.rpc('search_private_articles', {
            query_embedding: queryEmbedding,
            match_threshold: 0.3,
            match_count: limit * 2,
          })
        ]);

        if (publicSemanticResult.error) {
          console.error('Public search error:', publicSemanticResult.error);
          return NextResponse.json(
            { error: 'Search failed', details: publicSemanticResult.error.message },
            { status: 500 }
          );
        }

        // Tag and combine semantic results
        const publicSemantic = (publicSemanticResult.data || []).map((a: any) => ({ ...a, type: 'public' }));
        const privateSemantic = (privateSemanticResult.data || []).map((a: any) => ({ ...a, type: 'private' }));
        results = [...publicSemantic, ...privateSemantic];
      }

      if (mode === 'keyword' || mode === 'hybrid') {
        // Keyword search - both public and private articles in parallel
        const searchLimit = mode === 'keyword' ? limit : limit * 2;

        const [publicKeywordResult, privateKeywordResult] = await Promise.all([
          supabase
            .from('articles')
            .select('*')
            .or(`title.ilike.%${query}%,summary_text.ilike.%${query}%,transcript_text.ilike.%${query}%`)
            .order('created_at', { ascending: false })
            .limit(searchLimit),
          supabase
            .from('private_articles')
            .select('*')
            .or(`title.ilike.%${query}%,summary_text.ilike.%${query}%,transcript_text.ilike.%${query}%`)
            .order('created_at', { ascending: false })
            .limit(searchLimit)
        ]);

        if (publicKeywordResult.error) {
          console.error('Public keyword search error:', publicKeywordResult.error);
        }

        // Tag keyword results
        const publicKeyword = (publicKeywordResult.data || []).map((a: any) => ({ ...a, type: 'public' }));
        const privateKeyword = (privateKeywordResult.data || []).map((a: any) => ({ ...a, type: 'private' }));
        const keywordResults = [...publicKeyword, ...privateKeyword];

        if (mode === 'hybrid') {
          // Merge results, prioritizing semantic matches but including keyword matches
          // Use composite key (type + id) to handle public/private with same IDs
          const resultMap = new Map()

          // Add semantic results first (with similarity scores)
          results.forEach((r: any) => resultMap.set(`${r.type}-${r.id}`, { ...r, source: 'semantic' }))

          // Add keyword results (without duplicates)
          keywordResults.forEach((r: any) => {
            const key = `${r.type}-${r.id}`;
            if (!resultMap.has(key)) {
              resultMap.set(key, { ...r, similarity: 0.5, source: 'keyword' })
            }
          })

          results = Array.from(resultMap.values())
        } else {
          results = keywordResults
        }
      }
    }

    // Apply user filter first if specified
    if (filters.userId) {
      // Fetch article IDs for this user from both junction tables
      const [publicArticleUsers, privateArticleUsers] = await Promise.all([
        supabase
          .from('article_users')
          .select('article_id')
          .eq('user_id', filters.userId),
        supabase
          .from('private_article_users')
          .select('private_article_id')
          .eq('user_id', filters.userId)
      ]);

      if (publicArticleUsers.error) {
        console.error('User filter error (public):', publicArticleUsers.error);
      }

      const userPublicIds = new Set((publicArticleUsers.data || []).map((au: any) => au.article_id));
      const userPrivateIds = new Set((privateArticleUsers.data || []).map((au: any) => au.private_article_id));

      // Filter results based on type and matching IDs
      results = results.filter((r: any) => {
        if (r.type === 'private') {
          return userPrivateIds.has(r.id);
        } else {
          return userPublicIds.has(r.id);
        }
      });
    }

    // Apply other filters
    if (filters.contentTypes && filters.contentTypes.length > 0) {
      results = results.filter((r: any) => filters.contentTypes!.includes(r.content_source))
    }

    if (filters.sources && filters.sources.length > 0) {
      results = results.filter((r: any) => filters.sources!.includes(r.source))
    }

    if (filters.dateFrom) {
      results = results.filter((r: any) => new Date(r.created_at) >= new Date(filters.dateFrom!))
    }

    if (filters.dateTo) {
      results = results.filter((r: any) => new Date(r.created_at) <= new Date(filters.dateTo!))
    }

    // Apply theme filter (only for private articles)
    // Theme filtering uses OR logic - shows articles with insights for ANY selected theme
    if (filters.themeIds && filters.themeIds.length > 0) {
      // Get private article IDs that have insights for any of the selected themes
      const { data: themedArticles, error: themeError } = await supabase
        .from('private_article_themed_insights')
        .select('private_article_id')
        .in('theme_id', filters.themeIds);

      if (themeError) {
        console.error('Theme filter error:', themeError);
      } else if (themedArticles) {
        const themedArticleIds = new Set(themedArticles.map((ta: any) => ta.private_article_id));
        // Filter to only private articles that have themed insights
        results = results.filter((r: any) =>
          r.type === 'private' && themedArticleIds.has(r.id)
        );
      }
    }

    // Sort by similarity if available, otherwise by date
    results.sort((a: any, b: any) => {
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
