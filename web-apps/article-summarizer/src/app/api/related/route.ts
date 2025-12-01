import { createClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';
import { generateEmbedding } from '@/lib/embeddings';

export async function POST(request: NextRequest) {
  try {
    const { articleId, limit = 5 } = await request.json();

    if (!articleId) {
      return NextResponse.json(
        { error: 'Article ID is required' },
        { status: 400 }
      );
    }

    const supabase = await createClient();

    // First get the source article to get its embedding or generate one
    const { data: sourceArticle, error: fetchError } = await supabase
      .from('articles')
      .select('*')
      .eq('id', articleId)
      .single();

    if (fetchError || !sourceArticle) {
      return NextResponse.json(
        { error: 'Article not found' },
        { status: 404 }
      );
    }

    // If we don't have an embedding stored (assuming we might store it later),
    // we generate one from the content
    // Note: In a real app, you'd likely store embeddings in a vector column
    // For now, we'll generate it on the fly from the summary/title
    const textToEmbed = `${sourceArticle.title} ${sourceArticle.summary_text || ''}`;
    const embedding = await generateEmbedding(textToEmbed);

    // Call the search RPC function
    const { data: relatedArticles, error: searchError } = await supabase.rpc('search_articles', {
      query_embedding: embedding,
      match_threshold: 0.5, // Higher threshold for "related" than general search
      match_count: limit + 1, // Fetch one extra to filter out self
    });

    if (searchError) {
      console.error('Related search error:', searchError);
      return NextResponse.json(
        { error: 'Failed to find related articles' },
        { status: 500 }
      );
    }

    // Filter out the source article itself
    const filteredResults = (relatedArticles || [])
      .filter((a: any) => a.id !== articleId)
      .slice(0, limit);

    return NextResponse.json({
      related: filteredResults
    });

  } catch (error) {
    console.error('Related API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
