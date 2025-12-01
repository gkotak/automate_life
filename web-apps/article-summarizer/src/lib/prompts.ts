/**
 * Braintrust-managed prompts for chat assistant
 *
 * This module contains all AI prompts used by the frontend chat interface.
 * These prompts are version-controlled in Git and automatically synced to Braintrust
 * for observability and debugging.
 *
 * Workflow:
 * 1. Edit prompts in this file
 * 2. Commit to Git
 * 3. CI/CD automatically syncs to Braintrust via `npx braintrust push`
 * 4. Braintrust links all traces to prompt versions
 */

/**
 * Chat Assistant Prompt
 *
 * RAG (Retrieval Augmented Generation) prompt for answering questions
 * based on article summaries and transcripts.
 *
 * Flow:
 * 1. User asks a question
 * 2. Semantic search finds relevant articles
 * 3. Build context from top 5 articles
 * 4. Answer question using context
 */

// Braintrust metadata
export const CHAT_ASSISTANT_METADATA = {
  slug: 'chat-assistant',
  name: 'Chat Assistant',
  model: 'gpt-4-turbo-preview',
  temperature: 0.7,
  maxTokens: 1500,
} as const;

/**
 * Article context interface for type safety
 */
export interface ArticleContext {
  title: string;
  source?: string | null;
  summary: string;
  key_insights?: any[];
  url: string;
  similarity?: number;
  type?: 'public' | 'private';  // Distinguishes between public and private articles
  id?: number;  // Article ID for generating correct links
}

/**
 * Build system message for chat assistant
 *
 * @param context - Array of relevant articles with summaries
 * @returns System message string for OpenAI
 */
export function buildChatSystemPrompt(context: ArticleContext[]): string {
  return `You are a helpful AI assistant that answers questions based on article summaries and transcripts.

Context from relevant articles:
${JSON.stringify(context, null, 2)}

Guidelines:
- Answer questions based on the provided context from articles
- Cite articles by their title when referencing specific information
- If the context doesn't contain relevant information to answer the question, politely say so
- Be conversational, helpful, and concise
- Use markdown formatting for better readability
- If asked about sources, refer to the article titles provided in context`;
}

/**
 * Build complete messages array for OpenAI chat completion
 *
 * @param context - Array of relevant articles
 * @param conversationHistory - Previous messages in conversation
 * @param userMessage - Current user message
 * @returns Messages array ready for OpenAI API
 */
export function buildChatMessages(
  context: ArticleContext[],
  conversationHistory: Array<{ role: string; content: string }>,
  userMessage: string
): Array<{ role: 'system' | 'user' | 'assistant'; content: string }> {
  return [
    { role: 'system' as const, content: buildChatSystemPrompt(context) },
    ...conversationHistory.slice(-10).map(msg => ({
      role: msg.role as 'user' | 'assistant',
      content: msg.content
    })),
    { role: 'user' as const, content: userMessage }
  ];
}
