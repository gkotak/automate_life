import { createClient } from '@supabase/supabase-js';
import { NextRequest, NextResponse } from 'next/server';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/**
 * GET - Get a specific conversation with all its messages
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const conversationId = parseInt(params.id);

    if (isNaN(conversationId)) {
      return NextResponse.json(
        { error: 'Invalid conversation ID' },
        { status: 400 }
      );
    }

    // Fetch conversation
    const { data: conversation, error: convError } = await supabase
      .from('conversations')
      .select('*')
      .eq('id', conversationId)
      .single();

    if (convError || !conversation) {
      return NextResponse.json(
        { error: 'Conversation not found' },
        { status: 404 }
      );
    }

    // Fetch messages
    const { data: messages, error: messagesError } = await supabase
      .from('messages')
      .select('*')
      .eq('conversation_id', conversationId)
      .order('created_at', { ascending: true });

    if (messagesError) {
      console.error('Error fetching messages:', messagesError);
      return NextResponse.json(
        { error: 'Failed to fetch messages', details: messagesError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      conversation,
      messages: messages || []
    });
  } catch (error) {
    console.error('Get conversation error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * PATCH - Update conversation (e.g., change title)
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const conversationId = parseInt(params.id);

    if (isNaN(conversationId)) {
      return NextResponse.json(
        { error: 'Invalid conversation ID' },
        { status: 400 }
      );
    }

    const { title } = await request.json();

    if (!title) {
      return NextResponse.json(
        { error: 'Title is required' },
        { status: 400 }
      );
    }

    const { data: conversation, error } = await supabase
      .from('conversations')
      .update({ title })
      .eq('id', conversationId)
      .select()
      .single();

    if (error) {
      console.error('Error updating conversation:', error);
      return NextResponse.json(
        { error: 'Failed to update conversation', details: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ conversation });
  } catch (error) {
    console.error('Update conversation error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * DELETE - Delete a conversation and all its messages
 * (CASCADE delete handles messages automatically)
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const conversationId = parseInt(params.id);

    if (isNaN(conversationId)) {
      return NextResponse.json(
        { error: 'Invalid conversation ID' },
        { status: 400 }
      );
    }

    const { error } = await supabase
      .from('conversations')
      .delete()
      .eq('id', conversationId);

    if (error) {
      console.error('Error deleting conversation:', error);
      return NextResponse.json(
        { error: 'Failed to delete conversation', details: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Delete conversation error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
