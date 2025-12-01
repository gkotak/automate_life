/**
 * Type definitions for the chat interface
 */

/**
 * Represents a conversation/chat session
 */
export interface Conversation {
  id: number
  title: string | null
  created_at: string
  updated_at: string
}

/**
 * Message role types
 */
export type MessageRole = 'user' | 'assistant' | 'system'

/**
 * Article source information included in assistant messages
 */
export interface ArticleSource {
  id: number
  title: string
  similarity: number
  url: string
  type?: 'public' | 'private'  // Distinguishes between public and private articles
}

/**
 * Represents a single message in a conversation
 */
export interface Message {
  id: number
  conversation_id: number
  role: MessageRole
  content: string
  sources?: ArticleSource[]
  created_at: string
}

/**
 * Request payload for sending a chat message
 */
export interface ChatRequest {
  message: string
  conversationId?: number
  articleIds?: number[] // Optional: constrain search to specific articles
}

/**
 * Response from chat API (non-streaming)
 */
export interface ChatResponse {
  conversationId: number
  message: Message
  sources: ArticleSource[]
}

/**
 * Request payload for creating a new conversation
 */
export interface CreateConversationRequest {
  title?: string
}

/**
 * Response from conversation list endpoint
 */
export interface ConversationsResponse {
  conversations: Conversation[]
  count: number
}

/**
 * Response from single conversation endpoint
 */
export interface ConversationDetailResponse {
  conversation: Conversation
  messages: Message[]
}

/**
 * Streaming chunk from chat API
 */
export interface StreamChunk {
  type: 'content' | 'done' | 'error'
  content?: string
  conversationId?: number
  messageId?: number
  sources?: ArticleSource[]
  error?: string
}
