import { createClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

/**
 * GET - Get a folder with its articles
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const folderId = parseInt(id);

    if (isNaN(folderId)) {
      return NextResponse.json({ error: 'Invalid folder ID' }, { status: 400 });
    }

    const supabase = await createClient();

    // Get folder (RLS will ensure user has access)
    const { data: folder, error: folderError } = await supabase
      .from('folders')
      .select('*')
      .eq('id', folderId)
      .single();

    if (folderError) {
      if (folderError.code === 'PGRST116') {
        return NextResponse.json({ error: 'Folder not found' }, { status: 404 });
      }
      console.error('Error fetching folder:', folderError);
      return NextResponse.json(
        { error: 'Failed to fetch folder', details: folderError.message },
        { status: 500 }
      );
    }

    // Get public articles in folder
    const { data: folderArticles } = await supabase
      .from('folder_articles')
      .select(`
        article_id,
        added_at,
        articles (
          id,
          title,
          url,
          source,
          summary_text,
          content_source,
          created_at
        )
      `)
      .eq('folder_id', folderId)
      .order('added_at', { ascending: false });

    // Get private articles in folder
    const { data: folderPrivateArticles } = await supabase
      .from('folder_private_articles')
      .select(`
        private_article_id,
        added_at,
        private_articles (
          id,
          title,
          url,
          source,
          summary_text,
          content_source,
          created_at
        )
      `)
      .eq('folder_id', folderId)
      .order('added_at', { ascending: false });

    // Format articles with type indicator
    const publicArticles = (folderArticles || []).map((fa: any) => ({
      ...fa.articles,
      type: 'public' as const,
      added_at: fa.added_at,
    }));

    const privateArticles = (folderPrivateArticles || []).map((fpa: any) => ({
      ...fpa.private_articles,
      type: 'private' as const,
      added_at: fpa.added_at,
    }));

    // Combine and sort by added_at
    const allArticles = [...publicArticles, ...privateArticles].sort(
      (a, b) => new Date(b.added_at).getTime() - new Date(a.added_at).getTime()
    );

    return NextResponse.json({
      folder: {
        ...folder,
        article_count: publicArticles.length,
        private_article_count: privateArticles.length,
        total_count: allArticles.length,
      },
      articles: allArticles,
    });
  } catch (error) {
    console.error('Get folder error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * PATCH - Update a folder
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const folderId = parseInt(id);

    if (isNaN(folderId)) {
      return NextResponse.json({ error: 'Invalid folder ID' }, { status: 400 });
    }

    const { name, description } = await request.json();

    if (name !== undefined && (typeof name !== 'string' || name.trim() === '')) {
      return NextResponse.json(
        { error: 'Folder name cannot be empty' },
        { status: 400 }
      );
    }

    const supabase = await createClient();

    // Build update object
    const updates: Record<string, any> = {};
    if (name !== undefined) updates.name = name.trim();
    if (description !== undefined) updates.description = description?.trim() || null;

    if (Object.keys(updates).length === 0) {
      return NextResponse.json(
        { error: 'No fields to update' },
        { status: 400 }
      );
    }

    const { data: folder, error: updateError } = await supabase
      .from('folders')
      .update(updates)
      .eq('id', folderId)
      .select()
      .single();

    if (updateError) {
      if (updateError.code === '23505') {
        return NextResponse.json(
          { error: 'A folder with this name already exists' },
          { status: 409 }
        );
      }
      if (updateError.code === 'PGRST116') {
        return NextResponse.json({ error: 'Folder not found' }, { status: 404 });
      }
      console.error('Error updating folder:', updateError);
      return NextResponse.json(
        { error: 'Failed to update folder', details: updateError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ folder });
  } catch (error) {
    console.error('Update folder error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * DELETE - Delete a folder
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const folderId = parseInt(id);

    if (isNaN(folderId)) {
      return NextResponse.json({ error: 'Invalid folder ID' }, { status: 400 });
    }

    const supabase = await createClient();

    const { error: deleteError } = await supabase
      .from('folders')
      .delete()
      .eq('id', folderId);

    if (deleteError) {
      console.error('Error deleting folder:', deleteError);
      return NextResponse.json(
        { error: 'Failed to delete folder', details: deleteError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Delete folder error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
