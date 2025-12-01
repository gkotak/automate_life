import { createClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

/**
 * GET - Get all insights for a theme across all articles (paginated)
 * Returns insights grouped by article with article metadata
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const themeId = parseInt(id);

    if (isNaN(themeId)) {
      return NextResponse.json({ error: 'Invalid theme ID' }, { status: 400 });
    }

    // Get pagination params
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '50');
    const offset = (page - 1) * limit;

    const supabase = await createClient();

    // First verify user has access to this theme
    const { data: theme, error: themeError } = await supabase
      .from('themes')
      .select('id, name')
      .eq('id', themeId)
      .single();

    if (themeError) {
      if (themeError.code === 'PGRST116') {
        return NextResponse.json({ error: 'Theme not found' }, { status: 404 });
      }
      console.error('Error fetching theme:', themeError);
      return NextResponse.json(
        { error: 'Failed to fetch theme', details: themeError.message },
        { status: 500 }
      );
    }

    // Get total count for pagination
    const { count: totalCount } = await supabase
      .from('private_article_themed_insights')
      .select('*', { count: 'exact', head: true })
      .eq('theme_id', themeId);

    // Get insights with article details
    const { data: insights, error: insightsError } = await supabase
      .from('private_article_themed_insights')
      .select(`
        id,
        insight_text,
        timestamp_seconds,
        time_formatted,
        created_at,
        private_article_id,
        private_articles (
          id,
          title,
          url,
          source,
          created_at
        )
      `)
      .eq('theme_id', themeId)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (insightsError) {
      console.error('Error fetching insights:', insightsError);
      return NextResponse.json(
        { error: 'Failed to fetch insights', details: insightsError.message },
        { status: 500 }
      );
    }

    // Format insights with article metadata
    const formattedInsights = (insights || []).map((insight: any) => ({
      id: insight.id,
      insight_text: insight.insight_text,
      timestamp_seconds: insight.timestamp_seconds,
      time_formatted: insight.time_formatted,
      created_at: insight.created_at,
      private_article_id: insight.private_article_id,
      article_title: insight.private_articles?.title,
      article_url: insight.private_articles?.url,
      article_source: insight.private_articles?.source,
      article_created_at: insight.private_articles?.created_at,
    }));

    // Group insights by article for the response
    const insightsByArticle: Record<number, any> = {};
    for (const insight of formattedInsights) {
      const articleId = insight.private_article_id;
      if (!insightsByArticle[articleId]) {
        insightsByArticle[articleId] = {
          article_id: articleId,
          article_title: insight.article_title,
          article_url: insight.article_url,
          article_source: insight.article_source,
          article_created_at: insight.article_created_at,
          insights: [],
        };
      }
      insightsByArticle[articleId].insights.push({
        id: insight.id,
        insight_text: insight.insight_text,
        timestamp_seconds: insight.timestamp_seconds,
        time_formatted: insight.time_formatted,
        created_at: insight.created_at,
      });
    }

    return NextResponse.json({
      theme,
      insights: formattedInsights,
      insights_by_article: Object.values(insightsByArticle),
      pagination: {
        page,
        limit,
        total: totalCount || 0,
        total_pages: Math.ceil((totalCount || 0) / limit),
      },
    });
  } catch (error) {
    console.error('Get theme insights error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
