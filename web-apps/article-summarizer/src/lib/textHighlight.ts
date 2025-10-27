/**
 * Text Highlighting Utilities
 *
 * Functions for highlighting search keywords in text content
 */

/**
 * Highlights search keywords in text by wrapping them in a mark element
 *
 * @param text - The text content to search and highlight
 * @param query - The search query (can be multiple words)
 * @returns HTML string with highlighted keywords wrapped in <mark> tags
 */
export function highlightKeywords(text: string, query: string): string {
  if (!text || !query || query.trim() === '') {
    return text
  }

  // Split query into individual keywords
  const keywords = query.trim().toLowerCase().split(/\s+/)

  // Escape special regex characters in keywords
  const escapeRegex = (str: string) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

  // Create regex pattern that matches any of the keywords (case insensitive)
  const pattern = keywords.map(escapeRegex).join('|')
  const regex = new RegExp(`(${pattern})`, 'gi')

  // Replace matches with highlighted version
  return text.replace(regex, '<mark class="bg-yellow-200 px-0.5 rounded">$1</mark>')
}

/**
 * Checks if text contains any of the search keywords
 *
 * @param text - The text to search
 * @param query - The search query
 * @returns true if text contains any keyword, false otherwise
 */
export function containsKeywords(text: string, query: string): boolean {
  if (!text || !query || query.trim() === '') {
    return false
  }

  const lowerText = text.toLowerCase()
  const keywords = query.trim().toLowerCase().split(/\s+/)

  return keywords.some(keyword => lowerText.includes(keyword))
}

/**
 * React component props for rendering highlighted text
 */
export interface HighlightedTextProps {
  text: string
  query?: string
  className?: string
}
