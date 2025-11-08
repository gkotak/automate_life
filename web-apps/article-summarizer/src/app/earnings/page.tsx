'use client'

import { useState, useEffect } from 'react'
import { supabase, EarningsInsights, EarningsCall } from '@/lib/supabase'
import Link from 'next/link'
import { TrendingUp, Calendar, Building2, ChevronRight, CheckCircle, Clock, XCircle } from 'lucide-react'

interface EarningsWithCall extends EarningsInsights {
  earnings_calls?: EarningsCall
}

export default function EarningsPage() {
  const [earnings, setEarnings] = useState<EarningsWithCall[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchEarnings()
  }, [])

  const fetchEarnings = async () => {
    try {
      const { data, error } = await supabase
        .from('earnings_insights')
        .select(`
          *,
          earnings_calls (
            id,
            symbol,
            quarter,
            fiscal_year,
            call_date,
            audio_url,
            processing_status,
            created_at
          )
        `)
        .order('created_at', { ascending: false })

      if (error) throw error
      setEarnings(data || [])
    } catch (error) {
      console.error('Error fetching earnings:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-900/30 text-green-400 border border-green-800">
            <CheckCircle className="w-3 h-3" />
            Completed
          </span>
        )
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-900/30 text-yellow-400 border border-yellow-800">
            <Clock className="w-3 h-3" />
            Processing
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-900/30 text-red-400 border border-red-800">
            <XCircle className="w-3 h-3" />
            Failed
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
            <Clock className="w-3 h-3" />
            Pending
          </span>
        )
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-slate-400">Loading earnings...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-8 h-8 text-primary-green" />
            <h1 className="text-3xl font-bold text-white">Earnings Insights</h1>
          </div>
          <p className="text-slate-400">
            AI-analyzed earnings call transcripts with key metrics, highlights, and guidance
          </p>
        </div>

        {/* Earnings List */}
        {earnings.length === 0 ? (
          <div className="text-center py-12">
            <TrendingUp className="w-16 h-16 text-slate-700 mx-auto mb-4" />
            <p className="text-slate-400 text-lg mb-2">No earnings insights yet</p>
            <p className="text-slate-500 text-sm">
              Earnings call transcripts will appear here once processed
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {earnings.map((earning) => {
              const call = Array.isArray(earning.earnings_calls)
                ? earning.earnings_calls[0]
                : earning.earnings_calls

              const metricsCount = Object.keys(earning.key_metrics || {}).length
              const highlightsCount = (earning.business_highlights || []).length
              const guidanceCount = Object.keys(earning.guidance || {}).length
              const risksCount = (earning.risks_concerns || []).length

              return (
                <Link
                  key={earning.id}
                  href={`/earnings/${earning.earnings_call_id}`}
                  className="block bg-slate-900 border border-slate-800 rounded-lg p-6 hover:border-primary-green transition-colors group"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {/* Symbol and Quarter */}
                      <div className="flex items-center gap-3 mb-2">
                        <h2 className="text-2xl font-bold text-white group-hover:text-primary-green transition-colors">
                          {earning.symbol}
                        </h2>
                        <span className="text-lg text-slate-400">{earning.quarter}</span>
                        {call && getStatusBadge(call.processing_status)}
                      </div>

                      {/* Stats */}
                      <div className="flex flex-wrap gap-4 mt-4 text-sm text-slate-400">
                        <div className="flex items-center gap-2">
                          <Building2 className="w-4 h-4" />
                          <span>{metricsCount} metrics</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <TrendingUp className="w-4 h-4" />
                          <span>{highlightsCount} highlights</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4" />
                          <span>{guidanceCount} guidance items</span>
                        </div>
                        {risksCount > 0 && (
                          <div className="flex items-center gap-2 text-red-400">
                            <span>{risksCount} risks</span>
                          </div>
                        )}
                      </div>

                      {/* Date */}
                      {call && (
                        <div className="mt-4 text-xs text-slate-500">
                          Processed {formatDate(call.created_at)}
                        </div>
                      )}
                    </div>

                    <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-primary-green transition-colors flex-shrink-0 mt-1" />
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
