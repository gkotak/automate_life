import { createClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

/**
 * GET - List all folders for user's organization with article counts
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

    // Get folders with article counts
    const { data: folders, error: foldersError } = await supabase
      .from('folders')
      .select('*')
      .eq('organization_id', userProfile.organization_id)
      .order('name', { ascending: true });

    if (foldersError) {
      console.error('Error fetching folders:', foldersError);
      return NextResponse.json(
        { error: 'Failed to fetch folders', details: foldersError.message },
        { status: 500 }
      );
    }

    // Get article counts for each folder
    const foldersWithCounts = await Promise.all(
      (folders || []).map(async (folder) => {
        // Count public articles
        const { count: articleCount } = await supabase
          .from('folder_articles')
          .select('*', { count: 'exact', head: true })
          .eq('folder_id', folder.id);

        // Count private articles
        const { count: privateArticleCount } = await supabase
          .from('folder_private_articles')
          .select('*', { count: 'exact', head: true })
          .eq('folder_id', folder.id);

        return {
          ...folder,
          article_count: articleCount || 0,
          private_article_count: privateArticleCount || 0,
          total_count: (articleCount || 0) + (privateArticleCount || 0),
        };
      })
    );

    return NextResponse.json({
      folders: foldersWithCounts,
      count: foldersWithCounts.length,
    });
  } catch (error) {
    console.error('Folders API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * POST - Create a new folder
 */
export async function POST(request: NextRequest) {
  try {
    const { name, description } = await request.json();

    if (!name || typeof name !== 'string' || name.trim() === '') {
      return NextResponse.json(
        { error: 'Folder name is required' },
        { status: 400 }
      );
    }

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

    // Create the folder
    const { data: folder, error: createError } = await supabase
      .from('folders')
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
          { error: 'A folder with this name already exists' },
          { status: 409 }
        );
      }
      console.error('Error creating folder:', createError);
      return NextResponse.json(
        { error: 'Failed to create folder', details: createError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      folder: {
        ...folder,
        article_count: 0,
        private_article_count: 0,
        total_count: 0,
      },
    });
  } catch (error) {
    console.error('Create folder error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
