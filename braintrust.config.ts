/**
 * Braintrust Configuration
 *
 * This file defines how prompts from code are pushed to Braintrust.
 * Run: npx braintrust push
 */

import { initLogger } from 'braintrust';
import { CHAT_ASSISTANT_METADATA, buildChatSystemPrompt } from './web-apps/article-summarizer/src/lib/prompts';

// Initialize Braintrust
const logger = initLogger({
  projectName: 'automate-life',
  apiKey: process.env.BRAINTRUST_API_KEY,
});

/**
 * Define prompts to be synced to Braintrust
 *
 * Note: Python prompts (article-analysis) are handled separately via Python SDK
 * This file handles TypeScript/JavaScript prompts only
 */

// Export configuration for Braintrust CLI
export const prompts = {
  /**
   * Chat Assistant Prompt
   *
   * Used by the frontend chat interface to answer questions about articles
   */
  'chat-assistant': {
    slug: CHAT_ASSISTANT_METADATA.slug,
    name: CHAT_ASSISTANT_METADATA.name,
    model: CHAT_ASSISTANT_METADATA.model,
    temperature: CHAT_ASSISTANT_METADATA.temperature,
    max_tokens: CHAT_ASSISTANT_METADATA.maxTokens,

    // Template with variables
    // When used, replace {{context}} with actual article data
    messages: [
      {
        role: 'system',
        content: `You are a helpful AI assistant that answers questions based on article summaries and transcripts.

Context from relevant articles:
{{context}}

Guidelines:
- Answer questions based on the provided context from articles
- Cite articles by their title when referencing specific information
- If the context doesn't contain relevant information to answer the question, politely say so
- Be conversational, helpful, and concise
- Use markdown formatting for better readability
- If asked about sources, refer to the article titles provided in context`
      }
    ],

    // Metadata for tracking
    metadata: {
      purpose: 'RAG chat assistant for article Q&A',
      version: '1.0.0',
      lastUpdated: new Date().toISOString(),
    }
  }
};

// Export for Braintrust push command
export default {
  projectName: 'automate-life',
  prompts,
};
