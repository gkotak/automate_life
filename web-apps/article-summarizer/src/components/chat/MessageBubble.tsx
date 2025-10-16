'use client'

import { Message } from '@/types/chat'
import { User, Bot, ExternalLink, Copy, Check } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
}

export default function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={`flex gap-3 sm:gap-4 ${isUser ? 'flex-row-reverse' : ''} mb-6`}>
      {/* Avatar */}
      <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-[#077331]' : 'bg-gray-600'
      }`}>
        {isUser ? (
          <User size={18} className="text-white" />
        ) : (
          <Bot size={18} className="text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'text-right' : ''}`}>
        <div className="group relative">
          <div className={`inline-block p-3 sm:p-4 rounded-lg ${
            isUser
              ? 'bg-[#077331] text-white'
              : 'bg-gray-100 text-gray-900'
          } whitespace-pre-wrap break-words`}>
            {message.content}
            {isStreaming && <span className="animate-pulse ml-1">▋</span>}
          </div>

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className={`absolute ${isUser ? 'left-0' : 'right-0'} top-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-gray-200`}
            title="Copy message"
          >
            {copied ? (
              <Check size={14} className="text-green-600" />
            ) : (
              <Copy size={14} className="text-gray-600" />
            )}
          </button>
        </div>

        {/* Source Citations (only for assistant) */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            <div className="text-xs text-gray-500 w-full mb-1">Sources:</div>
            {message.sources.map(source => (
              <Link
                key={source.id}
                href={`/article/${source.id}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-300 rounded-full text-xs sm:text-sm hover:bg-gray-50 hover:border-[#077331] transition-colors"
                target="_blank"
              >
                <span className="truncate max-w-[150px] sm:max-w-[200px]">
                  {source.title}
                </span>
                <span className="text-xs text-gray-500 flex-shrink-0">
                  ({Math.round(source.similarity * 100)}%)
                </span>
                <ExternalLink size={12} className="flex-shrink-0" />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
