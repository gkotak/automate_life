'use client'

import { useMemo } from 'react'
import { highlightKeywords } from '@/lib/textHighlight'

interface HighlightedTextProps {
  text: string
  query?: string
  className?: string
}

/**
 * Component that highlights search keywords in text
 *
 * @param text - The text content to display
 * @param query - The search query to highlight
 * @param className - Optional CSS classes
 */
export default function HighlightedText({ text, query, className = '' }: HighlightedTextProps) {
  const highlightedHtml = useMemo(() => {
    if (!query) return text
    return highlightKeywords(text, query)
  }, [text, query])

  if (!query) {
    return <span className={className}>{text}</span>
  }

  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: highlightedHtml }}
    />
  )
}
