'use client'

import { VideoFrame } from '@/lib/supabase'
import { useState, useMemo } from 'react'

interface VideoFramesListProps {
  frames: VideoFrame[]
  transcript?: string | null
  onTimestampClick?: (seconds: number) => void
  onTabSwitch?: (tab: string) => void
  clickedTimestamp?: number | null
}

// Helper function to extract transcript segment between timestamps
function extractTranscriptSegment(transcript: string, startSeconds: number, endSeconds: number): string {
  // Transcript format: [MM:SS] text or [HH:MM:SS] text
  const lines = transcript.split('\n')
  let excerptLines: string[] = []

  for (const line of lines) {
    const timestampMatch = line.match(/\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]/)
    if (timestampMatch) {
      const hours = timestampMatch[3] ? parseInt(timestampMatch[1]) : 0
      const minutes = timestampMatch[3] ? parseInt(timestampMatch[2]) : parseInt(timestampMatch[1])
      const seconds = timestampMatch[3] ? parseInt(timestampMatch[3]) : parseInt(timestampMatch[2])
      const lineSeconds = hours * 3600 + minutes * 60 + seconds

      if (lineSeconds >= startSeconds && lineSeconds < endSeconds) {
        // Remove timestamp from line
        const text = line.replace(/\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]\s*/, '')
        if (text.trim()) {
          excerptLines.push(text.trim())
        }
      }
    }
  }

  return excerptLines.join(' ')
}

// Generate a brief summary title for the transcript segment
function generateSummary(excerpt: string, timestamp: string): string {
  if (!excerpt || excerpt.length < 20) {
    return 'Content at' + ' ' + timestamp
  }

  // Simple heuristic: take first meaningful sentence or ~60 chars
  const firstSentence = excerpt.match(/^[^.!?]+[.!?]/)
  if (firstSentence && firstSentence[0].length <= 80) {
    return firstSentence[0].trim()
  }

  // Fallback: truncate to ~60 chars at word boundary
  const truncated = excerpt.substring(0, 80)
  const lastSpace = truncated.lastIndexOf(' ')
  return lastSpace > 40 ? truncated.substring(0, lastSpace) + '...' : truncated + '...'
}

export default function VideoFramesList(props: VideoFramesListProps) {
  const { frames, transcript, onTimestampClick, onTabSwitch, clickedTimestamp } = props
  const [selectedFrame, setSelectedFrame] = useState<VideoFrame | null>(null)

  // Extract transcript excerpts for each frame
  const frameExcerpts = useMemo(() => {
    if (!transcript) return new Map<number, { text: string; summary: string }>()

    const excerpts = new Map<number, { text: string; summary: string }>()

    frames.forEach((frame, index) => {
      const nextFrame = frames[index + 1]
      const startTime = frame.timestamp_seconds
      const endTime = nextFrame ? nextFrame.timestamp_seconds : startTime + 120 // 2 minutes window

      // Extract text between timestamps
      const excerpt = extractTranscriptSegment(transcript, startTime, endTime)
      const summary = generateSummary(excerpt, frame.time_formatted)

      excerpts.set(frame.timestamp_seconds, { text: excerpt, summary })
    })

    return excerpts
  }, [frames, transcript])

  if (!frames || frames.length === 0) {
    return null
  }

  const handleFrameClick = (frame: VideoFrame, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedFrame(frame)
  }

  const handlePlayClick = (frame: VideoFrame, e: React.MouseEvent) => {
    e.stopPropagation()
    if (onTimestampClick) {
      onTimestampClick(frame.timestamp_seconds)
    }
  }

  const handleCloseModal = () => {
    setSelectedFrame(null)
  }

  const handleTranscriptLink = (e: React.MouseEvent) => {
    e.preventDefault()
    if (onTabSwitch) {
      onTabSwitch('transcript')
    }
  }

  return (
    <div className="space-y-3 sm:space-y-4">
      <h3 className="text-lg sm:text-xl font-semibold text-gray-900">
        Video Snapshots
        <span className="ml-2 text-sm font-normal text-gray-500">
          ({frames.length} frame{frames.length !== 1 ? 's' : ''})
        </span>
      </h3>

      <div className="space-y-6">
        {frames.map((frame, index) => {
          const excerpt = frameExcerpts.get(frame.timestamp_seconds)
          const hasTranscript = excerpt && excerpt.text.length > 0

          return (
            <div
              key={index}
              className={'flex flex-col sm:flex-row gap-4 p-4 rounded-lg border-2 transition-all ' + (clickedTimestamp === frame.timestamp_seconds ? 'border-[#077331] bg-green-50' : 'border-gray-200 hover:border-gray-300')}
            >
              <div className="flex-shrink-0 sm:w-80">
                <button
                  onClick={(e) => handleFrameClick(frame, e)}
                  className="group relative overflow-hidden rounded-lg border-2 border-gray-200 hover:border-[#077331] transition-all w-full focus:outline-none focus:ring-2 focus:ring-[#077331] focus:ring-opacity-50"
                >
                  <div className="aspect-video bg-gray-100 overflow-hidden">
                    <img
                      src={frame.url}
                      alt={'Frame at ' + frame.time_formatted}
                      className="w-full h-full object-cover transition-transform group-hover:scale-105"
                      loading="lazy"
                    />
                  </div>

                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                    </svg>
                  </div>
                </button>

                {onTimestampClick && (
                  <button
                    onClick={(e) => handlePlayClick(frame, e)}
                    className="mt-2 w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-[#077331] text-white rounded-lg text-sm font-medium hover:bg-[#055a24] transition-colors shadow-sm"
                    title="Jump to this moment"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                    Jump to {frame.time_formatted}
                  </button>
                )}
              </div>

              <div className="flex-1 min-w-0">
                {hasTranscript ? (
                  <div className="space-y-2">
                    <h4 className="text-base font-semibold text-gray-900 line-clamp-2">
                      {excerpt.summary}
                    </h4>

                    <p className="text-sm text-gray-700 leading-relaxed line-clamp-4">
                      {excerpt.text}
                    </p>

                    {excerpt.text.length > 200 && (
                      <button
                        onClick={handleTranscriptLink}
                        className="text-sm text-[#077331] hover:text-[#055a24] font-medium inline-flex items-center gap-1"
                      >
                        See full transcript
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                    No transcript available for this section
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {selectedFrame && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4" onClick={handleCloseModal}>
          <div className="relative max-w-5xl w-full">
            <button onClick={handleCloseModal} className="absolute -top-12 right-0 text-white hover:text-gray-300 transition-colors">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            <div className="bg-white rounded-lg overflow-hidden">
              <img src={selectedFrame.url} alt={'Frame at ' + selectedFrame.time_formatted} className="w-full h-auto" onClick={(e) => e.stopPropagation()} />
              <div className="p-4 bg-gray-50 border-t">
                <div className="flex items-center justify-between">
                  <span className="text-lg font-medium text-gray-900">{selectedFrame.time_formatted}</span>
                  {onTimestampClick && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onTimestampClick(selectedFrame.timestamp_seconds); handleCloseModal() }}
                      className="px-4 py-2 bg-[#077331] text-white rounded-lg hover:bg-[#055a24] transition-colors flex items-center gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Jump to timestamp
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
