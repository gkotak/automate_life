import { createClient } from '@supabase/supabase-js';
import { NextRequest, NextResponse } from 'next/server';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
);

export async function POST(request: NextRequest) {
  try {
    const { articleId, limit = 5 } = await request.json();

    if (!articleId) {
      return NextResponse.json(
        { error: 'Article ID is required' },
        { status: 400 }
      );
    }

    // First, get the embedding of the current article
    const { data: article, error: articleError } = await supabase
      .from('articles')
      .select('embedding, title')
      .eq('id', articleId)
      .single();

    if (articleError || !article || !article.embedding) {
      return NextResponse.json(
        { error: 'Article not found or has no embedding' },
        { status: 404 }
      );
    }

    // Find similar articles using the embedding
    const { data: relatedArticles, error } = await supabase.rpc('search_articles', {
      query_embedding: article.embedding,
      match_threshold: 0.5, // Higher threshold for better quality matches
      match_count: 10, // Get more to ensure we have 5 after filtering
    });

    if (error) {
      console.error('Related articles error:', error);
      return NextResponse.json(
        { error: 'Failed to find related articles', details: error.message },
        { status: 500 }
      );
    }

    // Filter out the current article itself and only keep similarity >= 0.5
    const filtered = (relatedArticles || [])
      .filter((a: any) => a.id !== articleId && a.similarity >= 0.5)
      .slice(0, 5); // Limit to exactly 5 articles

    return NextResponse.json({
      related: filtered,
      count: filtered.length
    });
  } catch (error) {
    console.error('Related articles API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
