'use client'

import { Message } from '@/types/chat'
import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import { Loader2 } from 'lucide-react'

interface ChatMessagesProps {
  messages: Message[]
  isStreaming?: boolean
  streamingContent?: string
}

export default function ChatMessages({
  messages,
  isStreaming,
  streamingContent
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50">
      <div className="max-w-4xl mx-auto p-4 sm:p-6">
        {messages.length === 0 && !isStreaming ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-16 h-16 bg-gradient-to-br from-[#077331] to-green-700 rounded-full flex items-center justify-center mb-5">
              <svg
                className="w-8 h-8 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 mb-2">
              Start a Conversation
            </h2>
            <p className="text-gray-600 mb-6 max-w-md">
              Ask me anything about your articles. I can help you find insights,
              summarize content, and answer questions based on your collection.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
              <div className="p-4 bg-white rounded-lg border border-gray-200 text-left">
                <div className="text-sm font-medium text-gray-900 mb-1">
                  📊 Find Insights
                </div>
                <div className="text-xs text-gray-600">
                  "What are the key insights about AI safety?"
                </div>
              </div>
              <div className="p-4 bg-white rounded-lg border border-gray-200 text-left">
                <div className="text-sm font-medium text-gray-900 mb-1">
                  🎙️ Explore Topics
                </div>
                <div className="text-xs text-gray-600">
                  "Which podcasts discuss productivity?"
                </div>
              </div>
              <div className="p-4 bg-white rounded-lg border border-gray-200 text-left">
                <div className="text-sm font-medium text-gray-900 mb-1">
                  💡 Compare Views
                </div>
                <div className="text-xs text-gray-600">
                  "Compare viewpoints on remote work"
                </div>
              </div>
              <div className="p-4 bg-white rounded-lg border border-gray-200 text-left">
                <div className="text-sm font-medium text-gray-900 mb-1">
                  🔍 Deep Dive
                </div>
                <div className="text-xs text-gray-600">
                  "Tell me more about the latest on LLMs"
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
              />
            ))}

            {/* Streaming message */}
            {isStreaming && streamingContent && (
              <MessageBubble
                message={{
                  id: -1,
                  conversation_id: 0,
                  role: 'assistant',
                  content: streamingContent,
                  created_at: new Date().toISOString()
                }}
                isStreaming={true}
              />
            )}

            {/* Loading indicator when starting to stream */}
            {isStreaming && !streamingContent && (
              <div className="flex gap-4 mb-6">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-gray-600">
                  <Loader2 size={18} className="text-white animate-spin" />
                </div>
                <div className="flex-1">
                  <div className="inline-block p-3 sm:p-4 rounded-lg bg-gray-100">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}
