import { createClient } from '@supabase/supabase-js';
import { NextRequest, NextResponse } from 'next/server';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/**
 * GET - List all conversations
 * Returns conversations ordered by most recently updated
 */
export async function GET() {
  try {
    const { data: conversations, error } = await supabase
      .from('conversations')
      .select('*')
      .order('updated_at', { ascending: false })
      .limit(50);

    if (error) {
      console.error('Error fetching conversations:', error);
      return NextResponse.json(
        { error: 'Failed to fetch conversations', details: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      conversations: conversations || [],
      count: conversations?.length || 0
    });
  } catch (error) {
    console.error('Conversations API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * POST - Create a new conversation
 * Optional: Provide a title, otherwise it will be set when first message is added
 */
export async function POST(request: NextRequest) {
  try {
    const { title } = await request.json().catch(() => ({}));

    const { data: conversation, error } = await supabase
      .from('conversations')
      .insert({ title: title || null })
      .select()
      .single();

    if (error) {
      console.error('Error creating conversation:', error);
      return NextResponse.json(
        { error: 'Failed to create conversation', details: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ conversation });
  } catch (error) {
    console.error('Create conversation error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
