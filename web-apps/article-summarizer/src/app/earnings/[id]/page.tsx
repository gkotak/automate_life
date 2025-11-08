'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { supabase, EarningsInsights, EarningsCall } from '@/lib/supabase'
import { ArrowLeft, TrendingUp, Building2, Calendar, AlertTriangle, Sparkles, Quote, ExternalLink } from 'lucide-react'
import AudioPlayer from '@/components/AudioPlayer'
import { parseTimestamp } from '@/lib/timestamps'

export default function EarningsDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [insights, setInsights] = useState<EarningsInsights | null>(null)
  const [call, setCall] = useState<EarningsCall | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'insights' | 'transcript'>('insights')
  const [jumpToTimeFunc, setJumpToTimeFunc] = useState<((seconds: number) => void) | null>(null)

  useEffect(() => {
    if (params.id) {
      fetchEarningsData(parseInt(params.id as string))
    }
  }, [params.id])

  const fetchEarningsData = async (callId: number) => {
    try {
      // Fetch earnings call
      const { data: callData, error: callError } = await supabase
        .from('earnings_calls')
        .select('*')
        .eq('id', callId)
        .single()

      if (callError) throw callError
      setCall(callData)

      // Fetch insights
      const { data: insightsData, error: insightsError } = await supabase
        .from('earnings_insights')
        .select('*')
        .eq('earnings_call_id', callId)
        .single()

      if (insightsError) throw insightsError
      setInsights(insightsData)
    } catch (error) {
      console.error('Error fetching earnings data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const handleTimestampClick = (timestamp: string) => {
    if (jumpToTimeFunc) {
      const seconds = parseTimestamp(timestamp)
      jumpToTimeFunc(seconds)
    }
  }

  const renderTimestampButton = (timestamp: string, speaker?: string) => {
    if (!timestamp) return null

    return (
      <button
        onClick={() => handleTimestampClick(timestamp)}
        className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
        title={`Jump to ${timestamp}${speaker ? ` - ${speaker}` : ''}`}
      >
        [{timestamp}]
      </button>
    )
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading earnings insights...</p>
        </div>
      </div>
    )
  }

  if (!insights || !call) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <p className="text-gray-600 mb-4">Earnings call not found</p>
          <button
            onClick={() => router.push('/earnings')}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Back to Earnings
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
          onClick={() => router.push('/earnings')}
          className="flex items-center text-blue-600 hover:text-blue-700 mb-3 sm:mb-4 text-sm sm:text-base"
        >
          <ArrowLeft className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1.5 sm:mr-2" />
          Back to Earnings
        </button>

        <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900 mb-3 sm:mb-4 leading-tight">
            {insights.symbol} {insights.quarter} Earnings Call
          </h1>

          {/* Metadata */}
          <div className="flex flex-wrap gap-2 sm:gap-3 mb-3 sm:mb-4">
            <span className="flex items-center px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs sm:text-sm font-medium bg-blue-100 text-blue-800">
              <TrendingUp className="h-3 w-3 mr-1" />
              Earnings Call
            </span>
            <span className="px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs sm:text-sm font-medium bg-green-100 text-green-800">
              {insights.symbol}
            </span>
            <span className="px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs sm:text-sm font-medium bg-purple-100 text-purple-800">
              {insights.quarter}
            </span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0 text-xs sm:text-sm text-gray-500">
            <div className="flex items-center">
              <Calendar className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 flex-shrink-0" />
              <span className="truncate">Processed {formatDate(call.created_at)}</span>
            </div>
            {call.earnings_url && (
              <a
                href={call.earnings_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-blue-600 hover:text-blue-700 w-fit"
              >
                <ExternalLink className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1 flex-shrink-0" />
                View on Seeking Alpha
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Audio Player */}
      {call.audio_url && (
        <AudioPlayer
          audioUrl={call.audio_url}
          onPlayerReady={(jumpFn) => setJumpToTimeFunc(() => jumpFn)}
          title="🎧 Listen to Earnings Call"
          className="mb-6 sm:mb-8"
        />
      )}

      {/* Content Tabs */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="border-b border-gray-200 px-4 sm:px-6 pt-3 sm:pt-4 overflow-x-auto">
          <nav className="-mb-px flex space-x-4 sm:space-x-8">
            <button
              onClick={() => setActiveTab('insights')}
              className={`py-2 px-1 border-b-2 font-medium text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'insights'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Insights
            </button>
            {call.transcript_text && (
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
        <div className="p-4 sm:p-6">
          {activeTab === 'insights' && (
            <div className="space-y-6 sm:space-y-8">
              {/* Key Metrics */}
              {Object.keys(insights.key_metrics || {}).length > 0 && (
                <section>
                  <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-3 sm:mb-4 flex items-center gap-2">
                    <Building2 className="h-5 w-5 text-blue-600" />
                    Key Metrics
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
                    {Object.entries(insights.key_metrics).map(([key, metric]: [string, any]) => (
                      <div key={key} className="bg-gray-50 border border-gray-200 rounded-lg p-3 sm:p-4">
                        <div className="text-xs sm:text-sm font-medium text-gray-600 mb-1 capitalize">
                          {key.replace(/_/g, ' ')}
                        </div>
                        <div className="text-base sm:text-lg font-semibold text-gray-900 mb-2">
                          {metric.value}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span>{metric.speaker}</span>
                          {metric.timestamp && (
                            <>
                              <span>•</span>
                              {renderTimestampButton(metric.timestamp, metric.speaker)}
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Business Highlights */}
              {(insights.business_highlights || []).length > 0 && (
                <section>
                  <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-3 sm:mb-4 flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-blue-600" />
                    Business Highlights
                  </h2>
                  <div className="space-y-2 sm:space-y-3">
                    {insights.business_highlights.map((highlight: any, idx: number) => (
                      <div key={idx} className="bg-gray-50 border border-gray-200 rounded-lg p-3 sm:p-4">
                        <p className="text-sm sm:text-base text-gray-900 mb-2">{highlight.text}</p>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <span>{highlight.speaker}</span>
                          {highlight.timestamp && (
                            <>
                              <span>•</span>
                              {renderTimestampButton(highlight.timestamp, highlight.speaker)}
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Forward Guidance */}
              {Object.keys(insights.guidance || {}).length > 0 && (
                <section>
                  <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-3 sm:mb-4 flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-blue-600" />
                    Forward Guidance
                  </h2>
                  <div className="space-y-2 sm:space-y-3">
                    {Object.entries(insights.guidance).map(([key, metric]: [string, any]) => (
                      <div key={key} className="bg-blue-50 border border-blue-200 rounded-lg p-3 sm:p-4">
                        <div className="text-xs sm:text-sm font-medium text-blue-900 mb-1 capitalize">
                          {key.replace(/_/g, ' ')}
                        </div>
                        <p className="text-sm sm:text-base text-gray-900 mb-2">{metric.value}</p>
                        <div className="flex items-center gap-2 text-xs text-gray-600">
                          <span>{metric.speaker}</span>
                          {metric.timestamp && (
                            <>
                              <span>•</span>
                              {renderTimestampButton(metric.timestamp, metric.speaker)}
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8">
                {/* Positives */}
                {(insights.positives || []).length > 0 && (
                  <section>
                    <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-3 sm:mb-4 flex items-center gap-2">
                      <Sparkles className="h-5 w-5 text-green-600" />
                      Positives
                    </h2>
                    <div className="space-y-2 sm:space-y-3">
                      {insights.positives.map((positive: any, idx: number) => (
                        <div key={idx} className="bg-green-50 border border-green-200 rounded-lg p-3 sm:p-4">
                          <p className="text-sm sm:text-base text-gray-900 mb-2">{positive.text}</p>
                          <div className="flex items-center gap-2 text-xs text-gray-600">
                            <span>{positive.speaker}</span>
                            {positive.timestamp && (
                              <>
                                <span>•</span>
                                {renderTimestampButton(positive.timestamp, positive.speaker)}
                              </>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* Risks & Concerns */}
                {(insights.risks_concerns || []).length > 0 && (
                  <section>
                    <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-3 sm:mb-4 flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-red-600" />
                      Risks & Concerns
                    </h2>
                    <div className="space-y-2 sm:space-y-3">
                      {insights.risks_concerns.map((risk: any, idx: number) => (
                        <div key={idx} className="bg-red-50 border border-red-200 rounded-lg p-3 sm:p-4">
                          <p className="text-sm sm:text-base text-gray-900 mb-2">{risk.text}</p>
                          <div className="flex items-center gap-2 text-xs text-gray-600">
                            <span className="text-red-600 capitalize">{risk.context.replace(/_/g, ' ')}</span>
                            <span>•</span>
                            <span>{risk.speaker}</span>
                            {risk.timestamp && (
                              <>
                                <span>•</span>
                                {renderTimestampButton(risk.timestamp, risk.speaker)}
                              </>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>

              {/* Notable Quotes */}
              {(insights.notable_quotes || []).length > 0 && (
                <section>
                  <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-3 sm:mb-4 flex items-center gap-2">
                    <Quote className="h-5 w-5 text-blue-600" />
                    Notable Quotes
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
                    {insights.notable_quotes.map((quote: any, idx: number) => (
                      <div key={idx} className="bg-gray-50 border border-gray-200 rounded-lg p-3 sm:p-4">
                        <Quote className="h-4 w-4 text-gray-400 mb-2" />
                        <p className="text-sm sm:text-base text-gray-900 mb-3 italic">&ldquo;{quote.quote}&rdquo;</p>
                        <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                          <span>{quote.speaker}</span>
                          {quote.timestamp && (
                            <>
                              <span>•</span>
                              {renderTimestampButton(quote.timestamp, quote.speaker)}
                            </>
                          )}
                        </div>
                        <div className="text-xs text-gray-500 capitalize">
                          {quote.context.replace(/_/g, ' ')}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}

          {activeTab === 'transcript' && call.transcript_text && (
            <div className="space-y-4">
              <div className="prose prose-sm sm:prose max-w-none">
                <p className="text-gray-600 text-sm mb-4">
                  Full transcript of the earnings call. Click timestamps to jump to that moment in the audio.
                </p>
                <div className="whitespace-pre-wrap text-sm text-gray-800">
                  {call.transcript_text}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
