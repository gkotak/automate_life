'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { supabase, Article } from '@/lib/supabase'
import { ArrowLeft, ExternalLink, Calendar, Tag, Play, FileText, Headphones } from 'lucide-react'
import ArticleSummary from '@/components/article/ArticleSummary'

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

  // Set up YouTube video speed and enhance functionality
  useEffect(() => {
    if (article && contentRef.current && activeTab === 'summary') {
      let player: any = null

      const setupYouTubePlayer = () => {
        // Find YouTube iframe
        const iframe = contentRef.current?.querySelector('iframe[src*="youtube.com"]') as HTMLIFrameElement
        if (!iframe) return

        // Extract video ID from iframe src
        const src = iframe.src
        const videoIdMatch = src.match(/embed\/([^?&]+)/)
        if (!videoIdMatch) return

        const videoId = videoIdMatch[1]

        // Replace iframe with div for YouTube player
        const playerDiv = document.createElement('div')
        playerDiv.id = `youtube-player-${videoId}`
        playerDiv.style.width = '100%'
        playerDiv.style.height = '800px'
        iframe.parentNode?.replaceChild(playerDiv, iframe)

        // Initialize YouTube player
        if (window.YT && window.YT.Player) {
          player = new window.YT.Player(playerDiv.id, {
            height: '800',
            width: '100%',
            videoId: videoId,
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
              },
              onStateChange: (event: any) => {
                // Ensure 2x speed is maintained
                if (event.data === window.YT.PlayerState.PLAYING) {
                  event.target.setPlaybackRate(2)
                }
              }
            }
          })
        }
      }

      // Function to jump to specific time in video
      const jumpToTime = (seconds: number) => {
        if (player && player.seekTo) {
          player.seekTo(seconds)
          player.setPlaybackRate(2)
        }
      }

      // Add jumpToTime to global scope for timestamp buttons
      ;(window as any).jumpToTime = jumpToTime

      // Store jumpToTime function in component state for new components
      setJumpToTimeFunc(() => jumpToTime)

      // Set up timestamp click handlers
      const timestampButtons = contentRef.current?.querySelectorAll('.insight-timestamp[onclick]')
      timestampButtons?.forEach((button: any) => {
        const originalOnclick = button.getAttribute('onclick')
        button.removeAttribute('onclick')
        button.addEventListener('click', () => {
          // Extract time from onclick attribute
          const timeMatch = originalOnclick?.match(/jumpToTime\((\d+)\)/)
          if (timeMatch) {
            jumpToTime(parseInt(timeMatch[1]))
          }
        })
      })

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
      }
    }
  }, [article, activeTab])

  const fetchArticle = async (id: number) => {
    try {
      setLoading(true)
      const { data, error } = await supabase
        .from('articles')
        .select('*, key_insights, main_points, quotes, takeaways, duration_minutes, word_count, topics')
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
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.push('/')}
          className="flex items-center text-blue-600 hover:text-blue-700 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Articles
        </button>

        <div className="bg-white rounded-lg shadow-md p-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">{article.title}</h1>

          {/* Metadata */}
          <div className="flex flex-wrap gap-3 mb-4">
            {article.content_source && (
              <span className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${getContentTypeColor(article.content_source)}`}>
                {getContentTypeIcon(article.content_source)}
                <span className="ml-1 capitalize">{article.content_source}</span>
              </span>
            )}
            {article.platform && (
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getPlatformColor(article.platform)}`}>
                {article.platform}
              </span>
            )}
            {article.tags?.map((tag, index) => (
              <span key={index} className="flex items-center px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                <Tag className="h-3 w-3 mr-1" />
                {tag}
              </span>
            ))}
          </div>

          <div className="flex items-center justify-between text-sm text-gray-500 mb-6">
            <div className="flex items-center">
              <Calendar className="h-4 w-4 mr-1" />
              {formatDate(article.created_at)}
            </div>
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center text-blue-600 hover:text-blue-700"
            >
              <ExternalLink className="h-4 w-4 mr-1" />
              View Original
            </a>
          </div>

          {/* Content Tabs */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('summary')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
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
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'transcript'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Transcript
                </button>
              )}
              {article.original_article_text && (
                <button
                  onClick={() => setActiveTab('original')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'original'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Original Article
                </button>
              )}
            </nav>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="bg-white rounded-lg shadow-md p-6">
        {activeTab === 'summary' && (
          <div ref={contentRef}>
            <ArticleSummary
              article={article}
              onTimestampClick={jumpToTimeFunc || undefined}
            />
          </div>
        )}

        {activeTab === 'transcript' && article.transcript_text && (
          <div className="prose prose-lg max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-gray-700 leading-relaxed">
              {article.transcript_text}
            </pre>
          </div>
        )}

        {activeTab === 'original' && article.original_article_text && (
          <div className="prose prose-lg max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-gray-700 leading-relaxed">
              {article.original_article_text}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}