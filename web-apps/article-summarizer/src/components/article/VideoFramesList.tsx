'use client'

import { VideoFrame } from '@/lib/supabase'
import { useState } from 'react'

interface VideoFramesListProps {
  frames: VideoFrame[]
  onTimestampClick?: (seconds: number) => void
  onTabSwitch?: (tab: string) => void
  clickedTimestamp?: number | null
}

export default function VideoFramesList(props: VideoFramesListProps) {
  const { frames, onTimestampClick, onTabSwitch, clickedTimestamp } = props
  const [selectedFrame, setSelectedFrame] = useState<VideoFrame | null>(null)
  const [isCollapsed, setIsCollapsed] = useState(true) // Collapsed by default

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
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="flex items-center justify-between w-full text-left group"
      >
        <h3 className="text-lg sm:text-xl font-semibold text-gray-900 flex items-center gap-2">
          Video Snapshots
          <span className="text-sm font-normal text-gray-500">
            ({frames.length} frame{frames.length !== 1 ? 's' : ''})
          </span>
        </h3>
        <svg
          className={`w-5 h-5 text-gray-500 transition-transform ${isCollapsed ? '' : 'rotate-180'}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {!isCollapsed && (
        <div className="space-y-6">
        {frames.map((frame, index) => {
          // Use pre-computed data from backend
          const transcriptExcerpt = frame.transcript_excerpt || ''
          const transcriptSummary = frame.transcript_summary || `Content at ${frame.time_formatted}`
          const hasTranscript = transcriptExcerpt.length > 0

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
                      {transcriptSummary}
                    </h4>

                    <p className="text-sm text-gray-700 leading-relaxed line-clamp-4">
                      {transcriptExcerpt}
                    </p>

                    {transcriptExcerpt.length > 200 && (
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
      )}

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
