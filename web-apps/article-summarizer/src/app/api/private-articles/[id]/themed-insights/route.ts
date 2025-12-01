import { createClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

/**
 * GET - Get themed insights for a private article, grouped by theme
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const articleId = parseInt(id);

    if (isNaN(articleId)) {
      return NextResponse.json({ error: 'Invalid article ID' }, { status: 400 });
    }

    const supabase = await createClient();

    // First verify the article exists and user has access
    const { data: article, error: articleError } = await supabase
      .from('private_articles')
      .select('id')
      .eq('id', articleId)
      .single();

    if (articleError) {
      if (articleError.code === 'PGRST116') {
        return NextResponse.json({ error: 'Article not found' }, { status: 404 });
      }
      console.error('Error fetching article:', articleError);
      return NextResponse.json(
        { error: 'Failed to fetch article', details: articleError.message },
        { status: 500 }
      );
    }

    // Get themed insights with theme info
    const { data: insights, error: insightsError } = await supabase
      .from('private_article_themed_insights')
      .select(`
        id,
        insight_text,
        timestamp_seconds,
        time_formatted,
        theme_id,
        created_at,
        themes (
          id,
          name
        )
      `)
      .eq('private_article_id', articleId)
      .order('created_at', { ascending: true });

    if (insightsError) {
      console.error('Error fetching insights:', insightsError);
      return NextResponse.json(
        { error: 'Failed to fetch insights', details: insightsError.message },
        { status: 500 }
      );
    }

    // Group insights by theme
    const groupedByTheme: Record<number, {
      theme_id: number;
      theme_name: string;
      insights: Array<{
        id: number;
        insight_text: string;
        timestamp_seconds: number | null;
        time_formatted: string | null;
        theme_name: string;
        theme_id: number;
      }>;
    }> = {};

    for (const insight of (insights || [])) {
      const themeId = insight.theme_id;
      const themeName = (insight.themes as any)?.name || 'Unknown Theme';

      if (!groupedByTheme[themeId]) {
        groupedByTheme[themeId] = {
          theme_id: themeId,
          theme_name: themeName,
          insights: [],
        };
      }

      groupedByTheme[themeId].insights.push({
        id: insight.id,
        insight_text: insight.insight_text,
        timestamp_seconds: insight.timestamp_seconds,
        time_formatted: insight.time_formatted,
        theme_name: themeName,
        theme_id: themeId,
      });
    }

    // Convert to array and sort by theme name
    const groupedInsights = Object.values(groupedByTheme).sort((a, b) =>
      a.theme_name.localeCompare(b.theme_name)
    );

    return NextResponse.json({
      article_id: articleId,
      grouped_insights: groupedInsights,
      total_insights: insights?.length || 0,
    });
  } catch (error) {
    console.error('Get themed insights error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
