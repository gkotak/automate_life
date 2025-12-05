import { createClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

/**
 * GET - List all themes for user's organization with article counts
 */
export async function GET() {
  try {
    const supabase = await createClient();

    // Get user's organization_id
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { data: userProfile, error: profileError } = await supabase
      .from('users')
      .select('organization_id')
      .eq('id', user.id)
      .single();

    if (profileError || !userProfile) {
      return NextResponse.json(
        { error: 'Failed to get user profile', details: profileError?.message },
        { status: 500 }
      );
    }

    // Get themes for the organization
    const { data: themes, error: themesError } = await supabase
      .from('themes')
      .select('*')
      .eq('organization_id', userProfile.organization_id)
      .order('name', { ascending: true });

    if (themesError) {
      console.error('Error fetching themes:', themesError);
      return NextResponse.json(
        { error: 'Failed to fetch themes', details: themesError.message },
        { status: 500 }
      );
    }

    // Get article counts for each theme (count distinct articles with insights)
    const themesWithCounts = await Promise.all(
      (themes || []).map(async (theme) => {
        // Count distinct private articles that have insights for this theme
        const { data: insightArticles } = await supabase
          .from('private_article_themed_insights')
          .select('private_article_id')
          .eq('theme_id', theme.id);

        // Get unique article count
        const uniqueArticleIds = new Set(insightArticles?.map(i => i.private_article_id) || []);

        return {
          ...theme,
          article_count: uniqueArticleIds.size,
        };
      })
    );

    return NextResponse.json({
      themes: themesWithCounts,
      count: themesWithCounts.length,
    });
  } catch (error) {
    console.error('Themes API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * POST - Create a new theme (admin only)
 */
export async function POST(request: NextRequest) {
  try {
    const { name, description } = await request.json();

    if (!name || typeof name !== 'string' || name.trim() === '') {
      return NextResponse.json(
        { error: 'Theme name is required' },
        { status: 400 }
      );
    }

    const supabase = await createClient();

    // Get user's organization_id and role
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { data: userProfile, error: profileError } = await supabase
      .from('users')
      .select('organization_id, role')
      .eq('id', user.id)
      .single();

    if (profileError || !userProfile) {
      return NextResponse.json(
        { error: 'Failed to get user profile', details: profileError?.message },
        { status: 500 }
      );
    }

    // Check if user is admin
    if (userProfile.role !== 'admin') {
      return NextResponse.json(
        { error: 'Only admins can create themes' },
        { status: 403 }
      );
    }

    // Create the theme
    const { data: theme, error: createError } = await supabase
      .from('themes')
      .insert({
        organization_id: userProfile.organization_id,
        name: name.trim(),
        description: description?.trim() || null,
      })
      .select()
      .single();

    if (createError) {
      // Check for unique constraint violation
      if (createError.code === '23505') {
        return NextResponse.json(
          { error: 'A theme with this name already exists' },
          { status: 409 }
        );
      }
      console.error('Error creating theme:', createError);
      return NextResponse.json(
        { error: 'Failed to create theme', details: createError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      theme: {
        ...theme,
        article_count: 0,
      },
    });
  } catch (error) {
    console.error('Create theme error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
