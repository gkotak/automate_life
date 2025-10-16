import { createClient } from '@supabase/supabase-js';
import { NextRequest } from 'next/server';
import { searchArticlesBySemantic } from '@/lib/search';
import { Message, ArticleSource } from '@/types/chat';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

interface ChatRequestBody {
  message: string;
  conversationId?: number;
  articleIds?: number[];
}

/**
 * Chat API endpoint with streaming support
 *
 * Flow:
 * 1. Receive user message
 * 2. Search for relevant articles using semantic search
 * 3. Build context from articles
 * 4. Call OpenAI Chat API with streaming
 * 5. Stream response to client
 * 6. Save conversation and messages to database
 */
export async function POST(request: NextRequest) {
  try {
    const { message, conversationId, articleIds }: ChatRequestBody = await request.json();

    if (!message || message.trim().length === 0) {
      return new Response(
        JSON.stringify({ error: 'Message is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const openaiApiKey = process.env.OPENAI_API_KEY;
    if (!openaiApiKey) {
      return new Response(
        JSON.stringify({ error: 'OpenAI API key not configured' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Step 1: Search for relevant articles
    let articles = await searchArticlesBySemantic(message, {
      matchThreshold: 0.3,
      matchCount: 10
    });

    // Optional: Filter to specific articles if provided
    if (articleIds && articleIds.length > 0) {
      articles = articles.filter(a => articleIds.includes(a.id));
    }

    // Limit to top 5 most relevant articles to keep context manageable
    const topArticles = articles.slice(0, 5);

    // Step 2: Build context from articles
    const context = topArticles.map(article => ({
      title: article.title,
      source: article.source || article.platform,
      summary: article.summary_text,
      key_insights: article.key_insights,
      url: article.url,
      similarity: article.similarity
    }));

    // Step 3: Get conversation history if continuing a chat
    let conversationHistory: Array<{ role: string; content: string }> = [];
    if (conversationId) {
      const { data: messages } = await supabase
        .from('messages')
        .select('role, content')
        .eq('conversation_id', conversationId)
        .order('created_at', { ascending: true })
        .limit(20); // Last 20 messages for context

      conversationHistory = messages || [];
    }

    // Step 4: Build messages array for OpenAI
    const systemPrompt = `You are a helpful AI assistant that answers questions based on article summaries and transcripts.

Context from relevant articles:
${JSON.stringify(context, null, 2)}

Guidelines:
- Answer questions based on the provided context from articles
- Cite articles by their title when referencing specific information
- If the context doesn't contain relevant information to answer the question, politely say so
- Be conversational, helpful, and concise
- Use markdown formatting for better readability
- If asked about sources, refer to the article titles provided in context`;

    const messages = [
      { role: 'system', content: systemPrompt },
      ...conversationHistory.slice(-10), // Last 10 messages to avoid token limits
      { role: 'user', content: message }
    ];

    // Step 5: Call OpenAI Chat API with streaming
    const openaiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openaiApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4-turbo-preview',
        messages,
        stream: true,
        temperature: 0.7,
        max_tokens: 1500
      })
    });

    if (!openaiResponse.ok) {
      const error = await openaiResponse.json().catch(() => ({}));
      console.error('OpenAI API error:', error);
      return new Response(
        JSON.stringify({ error: 'Failed to generate response' }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Step 6: Create a streaming response
    const encoder = new TextEncoder();
    let fullResponse = '';
    let currentConversationId = conversationId;

    const stream = new ReadableStream({
      async start(controller) {
        try {
          const reader = openaiResponse.body?.getReader();
          if (!reader) {
            throw new Error('No response body');
          }

          const decoder = new TextDecoder();

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n').filter(line => line.trim() !== '');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);

                if (data === '[DONE]') {
                  continue;
                }

                try {
                  const parsed = JSON.parse(data);
                  const content = parsed.choices[0]?.delta?.content;

                  if (content) {
                    fullResponse += content;
                    // Send content chunk to client
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'content', content })}\n\n`));
                  }
                } catch (e) {
                  // Skip parsing errors for non-JSON lines
                  continue;
                }
              }
            }
          }

          // Step 7: Save to database after streaming completes
          try {
            // Create conversation if new
            if (!currentConversationId) {
              const conversationTitle = message.slice(0, 100);
              const { data: newConversation, error: convError } = await supabase
                .from('conversations')
                .insert({ title: conversationTitle })
                .select()
                .single();

              if (convError) {
                console.error('Error creating conversation:', convError);
              } else if (newConversation) {
                currentConversationId = newConversation.id;
              }
            }

            if (currentConversationId) {
              // Save user message
              await supabase.from('messages').insert({
                conversation_id: currentConversationId,
                role: 'user',
                content: message
              });

              // Prepare sources for assistant message
              const sources: ArticleSource[] = topArticles.map(a => ({
                id: a.id,
                title: a.title,
                similarity: a.similarity || 0,
                url: a.url
              }));

              // Save assistant response
              await supabase.from('messages').insert({
                conversation_id: currentConversationId,
                role: 'assistant',
                content: fullResponse,
                sources: sources
              });

              // Send completion message with conversation ID and sources
              controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                type: 'done',
                conversationId: currentConversationId,
                sources
              })}\n\n`));
            }
          } catch (dbError) {
            console.error('Database error:', dbError);
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({
              type: 'error',
              error: 'Failed to save conversation'
            })}\n\n`));
          }

          controller.close();
        } catch (error) {
          console.error('Streaming error:', error);
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({
            type: 'error',
            error: 'Streaming failed'
          })}\n\n`));
          controller.close();
        }
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      }
    });

  } catch (error) {
    console.error('Chat API error:', error);
    return new Response(
      JSON.stringify({ error: 'Internal server error' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
