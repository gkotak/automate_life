/**
 * Custom hook for chat functionality
 * Handles message sending, streaming, and conversation state
 */

import { useState, useCallback } from 'react';
import { Message, ArticleSource } from '@/types/chat';

export interface UseChatOptions {
  conversationId?: number;
  onConversationCreated?: (conversationId: number) => void;
  onError?: (error: string) => void;
}

export function useChat(options: UseChatOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [sources, setSources] = useState<ArticleSource[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<number | undefined>(
    options.conversationId
  );

  const sendMessage = useCallback(async (content: string, articleIds?: number[]) => {
    if (!content.trim()) return;

    // Add user message immediately
    const userMessage: Message = {
      id: Date.now(),
      conversation_id: currentConversationId || 0,
      role: 'user',
      content,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    // Reset streaming state
    setIsStreaming(true);
    setStreamingContent('');
    setSources([]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          conversationId: currentConversationId,
          articleIds
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === 'content') {
                fullContent += parsed.content;
                setStreamingContent(fullContent);
              } else if (parsed.type === 'done') {
                // Streaming complete
                if (parsed.conversationId && !currentConversationId) {
                  setCurrentConversationId(parsed.conversationId);
                  options.onConversationCreated?.(parsed.conversationId);
                }
                if (parsed.sources) {
                  setSources(parsed.sources);
                }

                // Add assistant message
                const assistantMessage: Message = {
                  id: Date.now() + 1,
                  conversation_id: parsed.conversationId || currentConversationId || 0,
                  role: 'assistant',
                  content: fullContent,
                  sources: parsed.sources,
                  created_at: new Date().toISOString()
                };
                setMessages(prev => [...prev, assistantMessage]);
              } else if (parsed.type === 'error') {
                throw new Error(parsed.error || 'Unknown error');
              }
            } catch (e) {
              console.error('Error parsing stream data:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      options.onError?.(errorMessage);

      // Remove the user message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsStreaming(false);
      setStreamingContent('');
    }
  }, [currentConversationId, options]);

  const stopStreaming = useCallback(() => {
    setIsStreaming(false);
    setStreamingContent('');
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentConversationId(undefined);
    setStreamingContent('');
    setSources([]);
  }, []);

  const loadConversation = useCallback(async (conversationId: number) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`);
      if (!response.ok) {
        throw new Error('Failed to load conversation');
      }

      const data = await response.json();
      setMessages(data.messages || []);
      setCurrentConversationId(conversationId);
    } catch (error) {
      console.error('Error loading conversation:', error);
      options.onError?.('Failed to load conversation');
    }
  }, [options]);

  return {
    messages,
    isStreaming,
    streamingContent,
    sources,
    conversationId: currentConversationId,
    sendMessage,
    stopStreaming,
    clearMessages,
    loadConversation
  };
}
