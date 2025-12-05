import { createClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

/**
 * GET - Get a theme with its article count
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

    const supabase = await createClient();

    // Get theme (RLS will ensure user has access)
    const { data: theme, error: themeError } = await supabase
      .from('themes')
      .select('*')
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

    // Count distinct articles with insights for this theme
    const { data: insightArticles } = await supabase
      .from('private_article_themed_insights')
      .select('private_article_id')
      .eq('theme_id', themeId);

    const uniqueArticleIds = new Set(insightArticles?.map(i => i.private_article_id) || []);

    return NextResponse.json({
      theme: {
        ...theme,
        article_count: uniqueArticleIds.size,
      },
    });
  } catch (error) {
    console.error('Get theme error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * PUT - Update a theme (admin only)
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const themeId = parseInt(id);

    if (isNaN(themeId)) {
      return NextResponse.json({ error: 'Invalid theme ID' }, { status: 400 });
    }

    const { name, description } = await request.json();

    if (!name || typeof name !== 'string' || name.trim() === '') {
      return NextResponse.json(
        { error: 'Theme name is required' },
        { status: 400 }
      );
    }

    const supabase = await createClient();

    // Check if user is admin
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { data: userProfile, error: profileError } = await supabase
      .from('users')
      .select('role')
      .eq('id', user.id)
      .single();

    if (profileError || !userProfile) {
      return NextResponse.json(
        { error: 'Failed to get user profile', details: profileError?.message },
        { status: 500 }
      );
    }

    if (userProfile.role !== 'admin') {
      return NextResponse.json(
        { error: 'Only admins can update themes' },
        { status: 403 }
      );
    }

    const { data: theme, error: updateError } = await supabase
      .from('themes')
      .update({
        name: name.trim(),
        description: description?.trim() || null,
      })
      .eq('id', themeId)
      .select()
      .single();

    if (updateError) {
      if (updateError.code === '23505') {
        return NextResponse.json(
          { error: 'A theme with this name already exists' },
          { status: 409 }
        );
      }
      if (updateError.code === 'PGRST116') {
        return NextResponse.json({ error: 'Theme not found' }, { status: 404 });
      }
      console.error('Error updating theme:', updateError);
      return NextResponse.json(
        { error: 'Failed to update theme', details: updateError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ theme });
  } catch (error) {
    console.error('Update theme error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * DELETE - Delete a theme (admin only)
 * Note: This will cascade delete all themed insights for this theme
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const themeId = parseInt(id);

    if (isNaN(themeId)) {
      return NextResponse.json({ error: 'Invalid theme ID' }, { status: 400 });
    }

    const supabase = await createClient();

    // Check if user is admin
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { data: userProfile, error: profileError } = await supabase
      .from('users')
      .select('role')
      .eq('id', user.id)
      .single();

    if (profileError || !userProfile) {
      return NextResponse.json(
        { error: 'Failed to get user profile', details: profileError?.message },
        { status: 500 }
      );
    }

    if (userProfile.role !== 'admin') {
      return NextResponse.json(
        { error: 'Only admins can delete themes' },
        { status: 403 }
      );
    }

    const { error: deleteError } = await supabase
      .from('themes')
      .delete()
      .eq('id', themeId);

    if (deleteError) {
      console.error('Error deleting theme:', deleteError);
      return NextResponse.json(
        { error: 'Failed to delete theme', details: deleteError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Delete theme error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
