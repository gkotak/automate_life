'use client'

import { useState, useEffect } from 'react'
import ChatSidebar from '@/components/chat/ChatSidebar'
import ChatMessages from '@/components/chat/ChatMessages'
import ChatInput from '@/components/chat/ChatInput'
import { useChat } from '@/hooks/useChat'
import { Conversation } from '@/types/chat'
import { Menu } from 'lucide-react'

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

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
    setIsSidebarOpen(false) // Close sidebar on mobile after selecting
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
    <div className="flex h-full overflow-hidden">
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar - Hidden on mobile unless open, always visible on lg+ */}
      <div className={`
        fixed lg:relative inset-y-0 left-0 z-50 lg:z-auto
        transform transition-transform duration-300 ease-in-out
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <ChatSidebar
          conversations={conversations}
          currentConversationId={conversationId}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          onClose={() => setIsSidebarOpen(false)}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile Hamburger - Only visible on mobile, integrated with chat area */}
        <div className="lg:hidden bg-gray-50 border-b px-4 py-3 flex items-center justify-between">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Toggle sidebar"
          >
            <Menu size={20} className="text-gray-600" />
          </button>
          <span className="text-sm text-gray-600">Chat History</span>
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
