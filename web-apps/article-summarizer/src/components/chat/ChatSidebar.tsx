'use client'

import { Conversation } from '@/types/chat'
import { Trash2, MessageSquare, X } from 'lucide-react'
import { useState } from 'react'

interface ChatSidebarProps {
  conversations: Conversation[]
  currentConversationId?: number
  onSelectConversation: (id: number) => void
  onDeleteConversation: (id: number) => void
  onClose?: () => void
}

export default function ChatSidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onDeleteConversation,
  onClose
}: ChatSidebarProps) {
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    if (confirm('Are you sure you want to delete this conversation?')) {
      setDeletingId(id)
      await onDeleteConversation(id)
      setDeletingId(null)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="w-64 sm:w-72 lg:w-80 bg-[#077331] text-white flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-green-600 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Chat History</h2>
        {/* Close button - only visible on mobile */}
        <button
          onClick={onClose}
          className="lg:hidden p-1.5 hover:bg-green-600 rounded-lg transition-colors"
          aria-label="Close sidebar"
        >
          <X size={20} />
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-4 text-center text-green-200 text-sm">
            <MessageSquare size={32} className="mx-auto mb-2 opacity-50" />
            No conversations yet.
            <br />
            Start a new chat!
          </div>
        ) : (
          <div className="p-2">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                className={`w-full text-left p-3 rounded-lg mb-2 transition-colors group relative cursor-pointer ${
                  currentConversationId === conversation.id
                    ? 'bg-green-600'
                    : 'hover:bg-green-600/50'
                } ${deletingId === conversation.id ? 'opacity-50' : ''}`}
                onClick={() => !deletingId && onSelectConversation(conversation.id)}
              >
                <div className="pr-8">
                  <div className="font-medium text-sm truncate mb-1">
                    {conversation.title || 'New conversation'}
                  </div>
                  <div className="text-xs text-green-200">
                    {formatDate(conversation.updated_at)}
                  </div>
                </div>

                {/* Delete Button - Now a div with onClick, not nested button */}
                <div
                  onClick={(e) => handleDelete(e, conversation.id)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500 transition-all cursor-pointer"
                  title="Delete conversation"
                >
                  <Trash2 size={14} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
