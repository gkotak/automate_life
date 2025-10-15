'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { supabase, Article } from '@/lib/supabase'
import { ArrowLeft, ExternalLink, Calendar, Tag, Play, FileText, Headphones } from 'lucide-react'
import ArticleSummary from '@/components/article/ArticleSummary'
import ImageGallery from '@/components/article/ImageGallery'
import RelatedArticles from '@/components/RelatedArticles'

// YouTube API type declarations
declare global {
  interface Window {
    YT: any
    onYouTubeIframeAPIReady: () => void
    jumpToTime: (seconds: number) => void
  }
}

export default function ArticlePage() {
  const params = useParams()
  const router = useRouter()
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'summary' | 'transcript' | 'original'>('summary')
  const [jumpToTimeFunc, setJumpToTimeFunc] = useState<((seconds: number) => void) | null>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (params.id) {
      fetchArticle(parseInt(params.id as string))
    }
  }, [params.id])

  // Set up YouTube video player with 2x speed
  useEffect(() => {
    if (article && article.video_id && contentRef.current) {
      let player: any = null

      const setupYouTubePlayer = () => {
        const playerContainer = document.getElementById('youtube-player-container')
        if (!playerContainer) {
          console.warn('YouTube player container not found')
          return
        }

        // Clear existing content
        playerContainer.innerHTML = ''

        // Create player div
        const playerDiv = document.createElement('div')
        playerDiv.id = 'youtube-player'
        playerContainer.appendChild(playerDiv)

        // Initialize YouTube player with responsive sizing
        if (window.YT && window.YT.Player) {
          player = new window.YT.Player('youtube-player', {
            height: '100%',
            width: '100%',
            videoId: article.video_id,
            playerVars: {
              autoplay: 0,
              controls: 1,
              enablejsapi: 1,
              modestbranding: 1,
              rel: 0
            },
            events: {
              onReady: (event: any) => {
                // Set to 2x speed when ready
                event.target.setPlaybackRate(2)
                console.log('YouTube player ready - set to 2x speed')
              },
              onStateChange: (event: any) => {
                // Ensure 2x speed is maintained when playing
                if (event.data === window.YT.PlayerState.PLAYING) {
                  const currentRate = event.target.getPlaybackRate()
                  if (currentRate !== 2) {
                    event.target.setPlaybackRate(2)
                    console.log('Playback rate corrected to 2x')
                  }
                }
              }
            }
          })

          // Store player reference for timestamp jumping
          ;(window as any).youtubePlayer = player
        }
      }

      // Function to jump to specific time in video
      const jumpToTime = (seconds: number) => {
        const player = (window as any).youtubePlayer
        if (player && player.seekTo) {
          player.seekTo(seconds, true)
          player.playVideo()
          // Ensure 2x speed after seeking
          setTimeout(() => {
            player.setPlaybackRate(2)
          }, 100)
          console.log(`Jumped to ${seconds}s at 2x speed`)
        }
      }

      // Add jumpToTime to global scope
      ;(window as any).jumpToTime = jumpToTime
      setJumpToTimeFunc(() => jumpToTime)

      // Load YouTube API if not already loaded
      if (!window.YT) {
        const script = document.createElement('script')
        script.src = 'https://www.youtube.com/iframe_api'
        script.async = true
        document.head.appendChild(script)

        ;(window as any).onYouTubeIframeAPIReady = () => {
          setupYouTubePlayer()
        }
      } else {
        setupYouTubePlayer()
      }

      // Cleanup function
      return () => {
        if (player && player.destroy) {
          player.destroy()
        }
        delete (window as any).youtubePlayer
      }
    }
  }, [article])

  // Set up Audio player with 2x speed and timestamp jumping
  useEffect(() => {
    if (article && article.content_source === 'audio' && article.audio_url) {
      // Function to jump to specific time in audio
      const jumpToAudioTime = (seconds: number) => {
        const audioPlayer = document.getElementById('audio-player') as HTMLAudioElement
        if (audioPlayer) {
          audioPlayer.currentTime = seconds
          audioPlayer.play()
          // Ensure 2x speed after seeking
          setTimeout(() => {
            audioPlayer.playbackRate = 2.0
          }, 100)
          console.log(`Jumped to ${seconds}s at 2x speed in audio`)
        } else {
          console.warn('Audio player not found')
        }
      }

      // Add jumpToAudioTime to global scope for transcript tab
      ;(window as any).jumpToAudioTime = jumpToAudioTime
      setJumpToTimeFunc(() => jumpToAudioTime)

      // Store audio element reference for easy access
      const audioElement = document.getElementById('audio-player') as HTMLAudioElement
      if (audioElement) {
        ;(window as any).audioPlayer = audioElement
      }

      return () => {
        delete (window as any).audioPlayer
        delete (window as any).jumpToAudioTime
      }
    }
  }, [article])

  const fetchArticle = async (id: number) => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('articles')
        .select('*, key_insights, quotes, duration_minutes, word_count, topics')
        .eq('id', id)
        .single()

      if (error) throw error
      setArticle(data)
    } catch (error) {
      console.error('Error fetching article:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getContentTypeIcon = (contentSource: string | null) => {
    switch (contentSource) {
      case 'video': return <Play className="h-4 w-4" />
      case 'audio': return <Headphones className="h-4 w-4" />
      case 'article': return <FileText className="h-4 w-4" />
      default: return <FileText className="h-4 w-4" />
    }
  }

  const getContentTypeColor = (contentSource: string | null) => {
    switch (contentSource) {
      case 'video': return 'bg-red-100 text-red-800'
      case 'audio': return 'bg-blue-100 text-blue-800'
      case 'article': return 'bg-green-100 text-green-800'
      case 'mixed': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getPlatformColor = (platform: string | null) => {
    switch (platform) {
      case 'youtube': return 'bg-red-100 text-red-800'
      case 'substack': return 'bg-orange-100 text-orange-800'
      case 'stratechery': return 'bg-blue-100 text-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading article...</p>
        </div>
      </div>
    )
  }

  if (!article) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <p className="text-gray-600">Article not found</p>
          <button
            onClick={() => router.push('/')}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Go Back Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8 max-w-4xl">
      {/* Header */}
      <div className="mb-6 sm:mb-8">
        <button
          onClick={() => router.push('/')}
          className="flex items-center text-blue-600 hover:text-blue-700 mb-3 sm:mb-4 text-sm sm:text-base"
        >
          <ArrowLeft className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1.5 sm:mr-2" />
          Back to Articles
        </button>

        <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900 mb-3 sm:mb-4 leading-tight">{article.title}</h1>

          {/* Metadata */}
          <div className="flex flex-wrap gap-2 sm:gap-3 mb-3 sm:mb-4">
            {article.content_source && (
              <span className={`flex items-center px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs sm:text-sm font-medium ${getContentTypeColor(article.content_source)}`}>
                {getContentTypeIcon(article.content_source)}
                <span className="ml-1 capitalize">{article.content_source}</span>
              </span>
            )}
            {article.source && (
              <span className={`px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs sm:text-sm font-medium ${getPlatformColor(article.source)}`}>
                {article.source}
              </span>
            )}
            {article.tags?.map((tag, index) => (
              <span key={index} className="flex items-center px-2 sm:px-3 py-0.5 sm:py-1 bg-gray-100 text-gray-700 rounded-full text-xs sm:text-sm">
                <Tag className="h-3 w-3 mr-1" />
                {tag}
              </span>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0 text-xs sm:text-sm text-gray-500 mb-4 sm:mb-6">
            <div className="flex items-center">
              <Calendar className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 flex-shrink-0" />
              <span className="truncate">{formatDate(article.created_at)}</span>
            </div>
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center text-blue-600 hover:text-blue-700 w-fit"
            >
              <ExternalLink className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 flex-shrink-0" />
              View Original
            </a>
          </div>
        </div>
      </div>

      {/* Video Player - Shared across all tabs */}
      {article.content_source === 'video' && article.video_id && (
        <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 mb-6 sm:mb-8">
          <div className="space-y-2">
            <h3 className="text-lg sm:text-xl font-semibold text-gray-900">Video</h3>
            <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
              <div id="youtube-player-container" className="absolute top-0 left-0 w-full h-full">
                {/* YouTube player will be injected here */}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Audio Player - Shared across all tabs */}
      {article.content_source === 'audio' && article.audio_url && (
        <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 mb-6 sm:mb-8">
          <div className="space-y-2 sm:space-y-3">
            <h3 className="text-lg sm:text-xl font-semibold text-gray-900">🎧 Listen to Audio</h3>
            <p className="text-xs sm:text-sm text-gray-600">
              ⚡ Audio automatically plays at 2x speed for efficient listening. You can adjust speed in player controls.
            </p>
            <audio
              id="audio-player"
              controls
              controlsList="nodownload"
              className="w-full max-w-full sm:max-w-[600px]"
              onLoadedMetadata={(e) => {
                const audioEl = e.target as HTMLAudioElement
                audioEl.playbackRate = 2.0
              }}
            >
              <source src={article.audio_url} type="audio/mpeg" />
              Your browser does not support the audio element.
            </audio>
            <p className="text-xs text-gray-500">
              <strong>Note:</strong> Audio content embedded from original article.
            </p>
          </div>
        </div>
      )}

      {/* Content Tabs */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="border-b border-gray-200 px-4 sm:px-6 pt-3 sm:pt-4 overflow-x-auto">
          <nav className="-mb-px flex space-x-4 sm:space-x-8">
            <button
              onClick={() => setActiveTab('summary')}
              className={`py-2 px-1 border-b-2 font-medium text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'summary'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Summary
            </button>
            {article.transcript_text && (
              <button
                onClick={() => setActiveTab('transcript')}
                className={`py-2 px-1 border-b-2 font-medium text-xs sm:text-sm whitespace-nowrap ${
                  activeTab === 'transcript'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Transcript
              </button>
            )}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-4 sm:p-6" ref={contentRef}>
          {activeTab === 'summary' && (
            <>
              <ArticleSummary
                article={article}
                onTimestampClick={jumpToTimeFunc || undefined}
              />
              {/* Image Gallery - show extracted images */}
              {article.images && article.images.length > 0 && (
                <ImageGallery images={article.images} />
              )}
            </>
          )}

          {activeTab === 'transcript' && article.transcript_text && (
            <div className="space-y-6">
              {/* Article metadata */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                  {article.duration_minutes && (
                    <div className="flex items-center gap-1">
                      🕐 Duration: {article.duration_minutes} minutes
                    </div>
                  )}
                  {article.word_count && (
                    <div className="flex items-center gap-1">
                      📝 ~{article.word_count} words
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                {article.transcript_text.split('\n').map((line, index) => {
                  // Parse timestamp format: [MM:SS] or [H:MM:SS]
                  const timestampMatch = line.match(/^\[(\d+):(\d+)(?::(\d+))?\](.*)$/)

                  if (timestampMatch) {
                    const hours = timestampMatch[3] ? parseInt(timestampMatch[1]) : 0
                    const minutes = timestampMatch[3] ? parseInt(timestampMatch[2]) : parseInt(timestampMatch[1])
                    const seconds = timestampMatch[3] ? parseInt(timestampMatch[3]) : parseInt(timestampMatch[2])
                    const text = timestampMatch[4].trim()
                    const totalSeconds = hours * 3600 + minutes * 60 + seconds
                    const timeDisplay = timestampMatch[3]
                      ? `${timestampMatch[1]}:${timestampMatch[2]}:${timestampMatch[3]}`
                      : `${timestampMatch[1]}:${timestampMatch[2]}`

                    return (
                      <div key={index} className="flex gap-3">
                        <button
                          onClick={() => jumpToTimeFunc?.(totalSeconds)}
                          className="text-blue-600 hover:text-blue-800 hover:underline font-mono text-sm flex-shrink-0 cursor-pointer"
                        >
                          [{timeDisplay}]
                        </button>
                        <span className="text-gray-700 leading-relaxed">{text}</span>
                      </div>
                    )
                  }

                  return (
                    <div key={index} className="text-gray-700 leading-relaxed">
                      {line}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Related Articles Section */}
          {article && <RelatedArticles articleId={article.id} />}
        </div>
      </div>
    </div>
  )
}