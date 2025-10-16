'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import ChatSidebar from '@/components/chat/ChatSidebar'
import ChatMessages from '@/components/chat/ChatMessages'
import ChatInput from '@/components/chat/ChatInput'
import { useChat } from '@/hooks/useChat'
import { Conversation } from '@/types/chat'
import { ArrowLeft } from 'lucide-react'

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const {
    messages,
    isStreaming,
    streamingContent,
    conversationId,
    sendMessage,
    stopStreaming,
    clearMessages,
    loadConversation
  } = useChat({
    onConversationCreated: (newConvId) => {
      // Refresh conversations list when a new one is created
      fetchConversations()
    },
    onError: (errorMsg) => {
      setError(errorMsg)
      setTimeout(() => setError(null), 5000)
    }
  })

  // Fetch conversations on mount
  useEffect(() => {
    fetchConversations()
  }, [])

  const fetchConversations = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/conversations')
      if (!response.ok) throw new Error('Failed to fetch conversations')

      const data = await response.json()
      setConversations(data.conversations || [])
    } catch (error) {
      console.error('Error fetching conversations:', error)
      setError('Failed to load conversations')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectConversation = async (id: number) => {
    await loadConversation(id)
  }

  const handleNewChat = () => {
    clearMessages()
  }

  const handleDeleteConversation = async (id: number) => {
    try {
      const response = await fetch(`/api/conversations/${id}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('Failed to delete conversation')

      // Remove from local state
      setConversations(prev => prev.filter(c => c.id !== id))

      // If we deleted the current conversation, clear messages
      if (conversationId === id) {
        clearMessages()
      }
    } catch (error) {
      console.error('Error deleting conversation:', error)
      setError('Failed to delete conversation')
      setTimeout(() => setError(null), 5000)
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        currentConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-white border-b px-4 py-3 flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft size={20} />
            <span className="hidden sm:inline text-sm font-medium">Back to Articles</span>
          </Link>
          <div className="flex-1"></div>
          <div className="text-sm text-gray-600">
            <span className="hidden sm:inline">AI-powered chat with your articles</span>
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 m-4 rounded">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Messages */}
        <ChatMessages
          messages={messages}
          isStreaming={isStreaming}
          streamingContent={streamingContent}
        />

        {/* Input */}
        <ChatInput
          onSend={sendMessage}
          disabled={loading}
          isStreaming={isStreaming}
          onStop={stopStreaming}
        />
      </div>
    </div>
  )
}
