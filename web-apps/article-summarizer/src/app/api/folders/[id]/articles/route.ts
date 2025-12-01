import { createClient } from '@/lib/supabase-server';
import { NextRequest, NextResponse } from 'next/server';

/**
 * POST - Add an article to a folder
 * Body: { articleId: number, isPrivate: boolean }
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const folderId = parseInt(id);

    if (isNaN(folderId)) {
      return NextResponse.json({ error: 'Invalid folder ID' }, { status: 400 });
    }

    const { articleId, isPrivate } = await request.json();

    if (!articleId || typeof articleId !== 'number') {
      return NextResponse.json(
        { error: 'Article ID is required' },
        { status: 400 }
      );
    }

    const supabase = await createClient();

    // Verify folder exists and user has access (via RLS)
    const { data: folder, error: folderError } = await supabase
      .from('folders')
      .select('id')
      .eq('id', folderId)
      .single();

    if (folderError || !folder) {
      return NextResponse.json({ error: 'Folder not found' }, { status: 404 });
    }

    // Add to appropriate junction table
    if (isPrivate) {
      const { error: insertError } = await supabase
        .from('folder_private_articles')
        .insert({
          folder_id: folderId,
          private_article_id: articleId,
        });

      if (insertError) {
        if (insertError.code === '23505') {
          // Already in folder - treat as success
          return NextResponse.json({ success: true, alreadyExists: true });
        }
        if (insertError.code === '23503') {
          return NextResponse.json(
            { error: 'Article not found' },
            { status: 404 }
          );
        }
        console.error('Error adding private article to folder:', insertError);
        return NextResponse.json(
          { error: 'Failed to add article to folder', details: insertError.message },
          { status: 500 }
        );
      }
    } else {
      const { error: insertError } = await supabase
        .from('folder_articles')
        .insert({
          folder_id: folderId,
          article_id: articleId,
        });

      if (insertError) {
        if (insertError.code === '23505') {
          // Already in folder - treat as success
          return NextResponse.json({ success: true, alreadyExists: true });
        }
        if (insertError.code === '23503') {
          return NextResponse.json(
            { error: 'Article not found' },
            { status: 404 }
          );
        }
        console.error('Error adding article to folder:', insertError);
        return NextResponse.json(
          { error: 'Failed to add article to folder', details: insertError.message },
          { status: 500 }
        );
      }
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Add article to folder error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * DELETE - Remove an article from a folder
 * Body: { articleId: number, isPrivate: boolean }
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

    const { articleId, isPrivate } = await request.json();

    if (!articleId || typeof articleId !== 'number') {
      return NextResponse.json(
        { error: 'Article ID is required' },
        { status: 400 }
      );
    }

    const supabase = await createClient();

    // Remove from appropriate junction table
    if (isPrivate) {
      const { error: deleteError } = await supabase
        .from('folder_private_articles')
        .delete()
        .eq('folder_id', folderId)
        .eq('private_article_id', articleId);

      if (deleteError) {
        console.error('Error removing private article from folder:', deleteError);
        return NextResponse.json(
          { error: 'Failed to remove article from folder', details: deleteError.message },
          { status: 500 }
        );
      }
    } else {
      const { error: deleteError } = await supabase
        .from('folder_articles')
        .delete()
        .eq('folder_id', folderId)
        .eq('article_id', articleId);

      if (deleteError) {
        console.error('Error removing article from folder:', deleteError);
        return NextResponse.json(
          { error: 'Failed to remove article from folder', details: deleteError.message },
          { status: 500 }
        );
      }
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Remove article from folder error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
