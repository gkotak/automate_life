/**
 * Parse timestamp string to seconds
 * Supports formats: "MM:SS", "HH:MM:SS", "M:SS", "H:MM:SS"
 *
 * @param timestamp - Timestamp string (e.g., "05:30", "1:23:45")
 * @returns Seconds as number
 */
export function parseTimestamp(timestamp: string): number {
  const parts = timestamp.split(':').map(p => parseInt(p, 10))

  if (parts.length === 2) {
    // MM:SS format
    const [minutes, seconds] = parts
    return minutes * 60 + seconds
  } else if (parts.length === 3) {
    // HH:MM:SS format
    const [hours, minutes, seconds] = parts
    return hours * 3600 + minutes * 60 + seconds
  }

  return 0
}

/**
 * Format seconds to timestamp string
 *
 * @param seconds - Time in seconds
 * @returns Formatted timestamp (e.g., "05:30" or "1:23:45")
 */
export function formatTimestamp(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  } else {
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
}

/**
 * Create a clickable timestamp element handler
 *
 * @param timestamp - Timestamp string
 * @param onTimestampClick - Callback function to jump to time
 * @returns Click handler function
 */
export function createTimestampClickHandler(
  timestamp: string,
  onTimestampClick?: (seconds: number) => void
) {
  return (e: React.MouseEvent) => {
    e.preventDefault()
    if (onTimestampClick) {
      const seconds = parseTimestamp(timestamp)
      onTimestampClick(seconds)
    }
  }
}
