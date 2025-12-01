import { createClient } from '@/lib/supabase-server';
import { NextRequest } from 'next/server';
import { searchArticlesBySemantic } from '@/lib/search';
import { Message, ArticleSource } from '@/types/chat';
import { wrapOpenAI, initLogger } from 'braintrust';
import OpenAI from 'openai';
import { buildChatSystemPrompt, CHAT_ASSISTANT_METADATA, ArticleContext } from '@/lib/prompts';

// Initialize Braintrust logger once
let braintrustLogger: ReturnType<typeof initLogger> | null = null;

function getBraintrustLogger() {
  if (!braintrustLogger && process.env.BRAINTRUST_API_KEY) {
    try {
      braintrustLogger = initLogger({
        apiKey: process.env.BRAINTRUST_API_KEY,
        projectName: 'automate-life',
      });
      console.log('✅ [BRAINTRUST] Logger initialized for chat');
    } catch (error) {
      console.warn('⚠️ [BRAINTRUST] Failed to initialize logger:', error);
    }
  }
  return braintrustLogger;
}

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
    const supabase = await createClient();

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

    // Step 2: Build context from articles (now includes both public and private)
    const context: ArticleContext[] = topArticles.map(article => ({
      title: article.title,
      source: article.source || article.platform,
      summary: article.summary_text,
      key_insights: article.key_insights,
      url: article.url,
      similarity: article.similarity,
      type: article.type,
      id: article.id
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

    // Step 4: Build messages array for OpenAI (using prompt from prompts.ts)
    const systemPrompt = buildChatSystemPrompt(context);

    // Fix type error by ensuring role is strictly typed
    const formattedHistory = conversationHistory.map(msg => ({
      role: msg.role as 'user' | 'assistant' | 'system',
      content: msg.content
    }));

    const messages = [
      { role: 'system' as const, content: systemPrompt },
      ...formattedHistory.slice(-10), // Last 10 messages to avoid token limits
      { role: 'user' as const, content: message }
    ];

    // Step 5: Call OpenAI Chat API with streaming (using Braintrust wrapper)
    getBraintrustLogger();

    const client = wrapOpenAI(new OpenAI({
      apiKey: openaiApiKey,
    }));

    const stream = await client.chat.completions.create({
      model: CHAT_ASSISTANT_METADATA.model,
      messages,
      stream: true,
      temperature: CHAT_ASSISTANT_METADATA.temperature,
      max_tokens: CHAT_ASSISTANT_METADATA.maxTokens
    });

    // Step 6: Create a streaming response
    const encoder = new TextEncoder();
    let fullResponse = '';
    let currentConversationId = conversationId;

    const responseStream = new ReadableStream({
      async start(controller) {
        try {
          // OpenAI SDK returns an async iterable for streaming
          for await (const chunk of stream) {
            const content = chunk.choices[0]?.delta?.content;

            if (content) {
              fullResponse += content;
              // Send content chunk to client
              controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'content', content })}\n\n`));
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

              // Prepare sources for assistant message (includes type for correct URL generation)
              const sources: ArticleSource[] = topArticles.map(a => ({
                id: a.id,
                title: a.title,
                similarity: a.similarity || 0,
                url: a.url,
                type: a.type
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

    return new Response(responseStream, {
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
