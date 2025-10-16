'use client'

import { useState, useRef, KeyboardEvent } from 'react'
import { Send, Square } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  isStreaming?: boolean
  onStop?: () => void
  placeholder?: string
}

export default function ChatInput({
  onSend,
  disabled = false,
  isStreaming = false,
  onStop,
  placeholder = "Ask a question about your articles..."
}: ChatInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim())
      setMessage('')
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value)
    // Auto-resize textarea
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px'
  }

  return (
    <div className="border-t bg-white p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-[#077331] focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              style={{ minHeight: '48px', maxHeight: '200px' }}
            />
            <div className="absolute right-2 bottom-2 text-xs text-gray-400">
              {message.length > 0 && `${message.length} chars`}
            </div>
          </div>

          {isStreaming ? (
            <button
              onClick={onStop}
              className="px-4 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center gap-2 flex-shrink-0"
              title="Stop generating"
            >
              <Square size={18} fill="currentColor" />
              <span className="hidden sm:inline">Stop</span>
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!message.trim() || disabled}
              className="px-4 py-3 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2 flex-shrink-0"
              title="Send message (Enter)"
            >
              <Send size={18} />
              <span className="hidden sm:inline">Send</span>
            </button>
          )}
        </div>

        <div className="mt-2 text-xs text-gray-500 text-center">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  )
}
