'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { supabase, Article } from '@/lib/supabase'
import { ArrowLeft, ExternalLink, Calendar, Tag, Play, FileText, Headphones } from 'lucide-react'
import ArticleSummary from '@/components/article/ArticleSummary'
import ImageGallery from '@/components/article/ImageGallery'
import RelatedArticles from '@/components/RelatedArticles'
import HighlightedText from '@/components/HighlightedText'
import ShareButton from '@/components/ShareButton'

// YouTube API type declarations
declare global {
  interface Window {
    YT: any
    onYouTubeIframeAPIReady: () => void
    jumpToTime: (seconds: number) => void
  }
}

interface ArticlePageContentProps {
  isPrivate: boolean
}

export default function ArticlePageContent({ isPrivate }: ArticlePageContentProps) {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const searchQuery = searchParams.get('q') || ''
  const searchMode = searchParams.get('mode') || 'keyword'
  const termsParam = searchParams.get('terms') || ''
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'summary' | 'transcript' | 'original'>('summary')
  const [jumpToTimeFunc, setJumpToTimeFunc] = useState<((seconds: number) => void) | null>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const [highlightTerms, setHighlightTerms] = useState<string>('')
  const [clickedTimestamp, setClickedTimestamp] = useState<number | null>(null)

  // Use extracted terms from URL (passed from search results)
  useEffect(() => {
    if (termsParam) {
      // Terms were extracted at search time and passed via URL
      const terms = termsParam.split(',').map(t => t.trim()).filter(t => t.length > 0)
      setHighlightTerms(terms.join(' '))
      console.log('Using pre-extracted terms from URL:', terms)
    } else if (searchQuery) {
      // Fallback: use the search query directly (for keyword search or direct navigation)
      setHighlightTerms(searchQuery)
    }
  }, [searchQuery, termsParam])

  // Handle timestamp URL parameter - jump to specific time on page load
  useEffect(() => {
    const timestampParam = searchParams.get('timestamp')
    if (timestampParam && jumpToTimeFunc && article) {
      const seconds = parseInt(timestampParam, 10)
      if (!isNaN(seconds) && seconds >= 0) {
        // Wait a bit for player to be ready, then jump to timestamp
        const timer = setTimeout(() => {
          console.log(`Jumping to timestamp from URL: ${seconds}s`)
          jumpToTimeFunc(seconds)
        }, 2000) // Give player 2 seconds to initialize

        return () => clearTimeout(timer)
      }
    }
  }, [searchParams, jumpToTimeFunc, article])

  useEffect(() => {
    if (params.id) {
      fetchArticle(parseInt(params.id as string))
    }
  }, [params.id])

  // Set up video player (YouTube, Loom, Wistia, etc.) with 2x speed where supported
  useEffect(() => {
    if (article && article.video_id && contentRef.current) {
      let player: any = null
      const platform = article.platform || 'youtube'

      const setupYouTubePlayer = () => {
        const playerContainer = document.getElementById('video-player-container')
        if (!playerContainer) {
          console.warn('Video player container not found')
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

      const setupDirectFilePlayer = () => {
        const playerContainer = document.getElementById('video-player-container')
        if (!playerContainer || !article.audio_url) {
          console.warn('Video player container not found or no audio_url')
          return
        }

        // Clear existing content
        playerContainer.innerHTML = ''

        // Create HTML5 video element for direct MP4/media files
        const video = document.createElement('video')
        video.style.width = '100%'
        video.style.height = '100%'
        video.controls = true
        video.id = 'direct-video-player'
        video.src = article.audio_url
        video.playbackRate = 2.0  // Set to 2x speed by default

        // Store video reference for timestamp jumping
        ;(window as any).directVideoPlayer = video

        playerContainer.appendChild(video)
        console.log('Direct file video player embedded')
      }

      const setupGenericPlayer = () => {
        const playerContainer = document.getElementById('video-player-container')
        if (!playerContainer) {
          console.warn('Video player container not found')
          return
        }

        // Clear existing content
        playerContainer.innerHTML = ''

        // Create iframe for generic video embed (Loom, Wistia, etc.)
        const iframe = document.createElement('iframe')
        iframe.style.width = '100%'
        iframe.style.height = '100%'
        iframe.style.border = 'none'
        iframe.allowFullscreen = true
        iframe.id = 'generic-video-player'
        // Allow autoplay for timestamp jumping
        iframe.setAttribute('allow', 'autoplay; fullscreen')

        // Platform-specific embed URLs
        const embedUrls: { [key: string]: string } = {
          'loom': `https://www.loom.com/embed/${article.video_id}`,
          'wistia': `https://fast.wistia.net/embed/iframe/${article.video_id}`,
          'vimeo': `https://player.vimeo.com/video/${article.video_id}`,
          'dailymotion': `https://www.dailymotion.com/embed/video/${article.video_id}`
        }

        const embedUrl = embedUrls[platform.toLowerCase()] || `https://${platform}.com/embed/${article.video_id}`
        iframe.src = embedUrl

        playerContainer.appendChild(iframe)

        // For Vimeo, set playback speed to 2x when player is ready
        if (platform === 'vimeo') {
          iframe.onload = () => {
            // Wait a bit for the Vimeo player to initialize
            setTimeout(() => {
              if (iframe.contentWindow) {
                const speedMessage = {
                  method: 'setPlaybackRate',
                  value: 2
                }
                iframe.contentWindow.postMessage(JSON.stringify(speedMessage), 'https://player.vimeo.com')
                console.log('Vimeo player ready - set to 2x speed')
              }
            }, 1000)
          }
        }

        console.log(`${platform} player embedded`)
      }

      // Function to jump to specific time in video
      const jumpToTime = (seconds: number) => {
        if (platform === 'youtube') {
          const player = (window as any).youtubePlayer
          if (player && player.seekTo) {
            player.seekTo(seconds, true)
            // Don't auto-play to avoid browser restrictions
            // Ensure 2x speed is set
            setTimeout(() => {
              player.setPlaybackRate(2)
            }, 100)
          }
        } else if (platform === 'direct_file' || article.video_id === 'direct_file') {
          // HTML5 video player for direct files
          const video = document.getElementById('direct-video-player') as HTMLVideoElement
          if (video) {
            video.currentTime = seconds
            // Don't auto-play to avoid browser restrictions
            // Ensure 2x speed
            video.playbackRate = 2.0

            // Track which timestamp was clicked
            setClickedTimestamp(seconds)
            setTimeout(() => setClickedTimestamp(null), 5000)
          }
        } else if (platform === 'loom') {
          // Loom supports postMessage API (player.js) for timestamp jumping
          const iframe = document.getElementById('generic-video-player') as HTMLIFrameElement
          if (iframe && iframe.contentWindow) {
            // Use Loom Player API to seek to timestamp
            iframe.contentWindow.postMessage(
              {
                method: 'setCurrentTime',
                value: seconds,
                context: 'player.js'
              },
              '*'
            )

            // Track which timestamp was clicked
            setClickedTimestamp(seconds)

            // Clear after 5 seconds
            setTimeout(() => {
              setClickedTimestamp(null)
            }, 5000)
          }
        } else if (platform === 'vimeo') {
          // Vimeo Player API: use postMessage to control the player
          const iframe = document.getElementById('generic-video-player') as HTMLIFrameElement
          if (iframe && iframe.contentWindow) {
            // Use Vimeo Player API to seek to timestamp
            const message = {
              method: 'setCurrentTime',
              value: seconds
            }
            iframe.contentWindow.postMessage(JSON.stringify(message), 'https://player.vimeo.com')

            // Set playback speed to 2x
            setTimeout(() => {
              const speedMessage = {
                method: 'setPlaybackRate',
                value: 2
              }
              iframe.contentWindow?.postMessage(JSON.stringify(speedMessage), 'https://player.vimeo.com')
            }, 100)

            // Don't auto-play to avoid browser restrictions

            // Track which timestamp was clicked
            setClickedTimestamp(seconds)

            // Clear after 5 seconds
            setTimeout(() => {
              setClickedTimestamp(null)
            }, 5000)
          }
        } else {
          console.warn(`Timestamp jumping not supported for ${platform} videos.`)
        }
      }

      // Add jumpToTime to global scope
      ;(window as any).jumpToTime = jumpToTime
      setJumpToTimeFunc(() => jumpToTime)

      // Set up player based on platform
      if (article.video_id === 'direct_file') {
        // Use HTML5 video player for direct media files
        setupDirectFilePlayer()
      } else if (platform === 'youtube') {
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
      } else {
        // Use generic iframe embed for other platforms
        setupGenericPlayer()
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
          // Don't auto-play to avoid browser restrictions
          // Ensure 2x speed
          audioPlayer.playbackRate = 2.0
          console.log(`Jumped to ${seconds}s (ready at 2x speed)`)
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

      // Choose table based on isPrivate prop
      const tableName = isPrivate ? 'private_articles' : 'articles'

      // Add timeout to prevent hanging on corrupted Supabase session
      const fetchPromise = supabase
        .from(tableName)
        .select('*')
        .eq('id', id)
        .single()

      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout - please refresh the page')), 10000)
      )

      const { data, error } = await Promise.race([fetchPromise, timeoutPromise])

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

  // Get current playback time for video
  const getCurrentVideoTime = (): number => {
    if (!article) return 0
    const platform = article.platform || 'youtube'

    if (platform === 'youtube') {
      const player = (window as any).youtubePlayer
      if (player && player.getCurrentTime) {
        return player.getCurrentTime()
      }
    } else if (platform === 'direct_file' || article.video_id === 'direct_file') {
      const video = document.getElementById('direct-video-player') as HTMLVideoElement
      if (video) {
        return video.currentTime
      }
    } else {
      // For Loom, Vimeo, and other platforms, we can't easily get current time
      // Return 0 for now (could be enhanced with platform-specific APIs)
      console.warn(`Getting current time not supported for ${platform}`)
    }
    return 0
  }

  // Get current playback time for audio
  const getCurrentAudioTime = (): number => {
    const audioPlayer = document.getElementById('audio-player') as HTMLAudioElement
    if (audioPlayer) {
      return audioPlayer.currentTime
    }
    return 0
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
            <div className="flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-gray-900">Video</h3>
              <ShareButton
                articleId={params.id as string}
                getCurrentTime={getCurrentVideoTime}
              />
            </div>
            {article.platform === 'youtube' && (
              <p className="text-xs sm:text-sm text-gray-600">
                ⚡ Video automatically plays at 2x speed for efficient watching. Use player controls to adjust.
              </p>
            )}
            <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
              <div id="video-player-container" className="absolute top-0 left-0 w-full h-full">
                {/* Video player (YouTube, Loom, Wistia, etc.) will be injected here */}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Audio Player - Shared across all tabs */}
      {article.content_source === 'audio' && article.audio_url && (
        <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 mb-6 sm:mb-8">
          <div className="space-y-2 sm:space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-gray-900">🎧 Listen to Audio</h3>
              <ShareButton
                articleId={params.id as string}
                getCurrentTime={getCurrentAudioTime}
              />
            </div>
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

      {/* PDF Viewer - for PDF documents */}
      {article.url?.toLowerCase().endsWith('.pdf') && (
        <div className="bg-white rounded-lg shadow-md p-4 sm:p-6 mb-6 sm:mb-8">
          <div className="space-y-2 sm:space-y-3">
            <h3 className="text-lg sm:text-xl font-semibold text-gray-900">📄 Document</h3>
            <div className="relative w-full" style={{ height: '600px' }}>
              <iframe
                src={article.url}
                className="absolute top-0 left-0 w-full h-full border-0 rounded-lg"
                title="PDF Document"
              />
            </div>
            <p className="text-xs text-gray-500">
              <strong>Note:</strong> If the PDF doesn't display, you can{' '}
              <a href={article.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                open it directly
              </a>.
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
            {/* Hide transcript tab for PDFs - the extracted text isn't well formatted */}
            {article.transcript_text && !article.url?.toLowerCase().endsWith('.pdf') && (
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
                onTabSwitch={setActiveTab}
                searchQuery={highlightTerms}
                clickedTimestamp={clickedTimestamp}
                isPrivate={isPrivate}
              />
              {/* Image Gallery - show extracted images (skip for video content) */}
              {article.images && article.images.length > 0 && article.content_source !== 'video' && (
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
                      <div key={index} className="p-2">
                        <div className="flex gap-3">
                          <button
                            onClick={() => jumpToTimeFunc?.(totalSeconds)}
                            className="text-blue-600 hover:text-blue-800 hover:underline font-mono text-sm flex-shrink-0 cursor-pointer"
                          >
                            [{timeDisplay}]
                          </button>
                          <span className="text-gray-700 leading-relaxed">
                            <HighlightedText text={text} query={highlightTerms} />
                          </span>
                        </div>
                        {clickedTimestamp === totalSeconds && (
                          <div className="ml-16 mt-1 text-blue-600 text-sm italic">
                            We've moved the video to this point, however, you'll need to scroll up and hit play.
                          </div>
                        )}
                      </div>
                    )
                  }

                  return (
                    <div key={index} className="text-gray-700 leading-relaxed">
                      <HighlightedText text={line} query={highlightTerms} />
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
