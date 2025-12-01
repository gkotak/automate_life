import { createBrowserClient } from '@supabase/ssr'

export const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabasePublishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!

export const supabase = createBrowserClient(supabaseUrl, supabasePublishableKey, {
  auth: {
    debug: true, // Enable debug logs to see what's happening
    lock: false, // Disable navigator.locks to prevent deadlocks in dev/SSR
    persistSession: true,
    detectSessionInUrl: true,
    flowType: 'pkce',
  }
})

export interface Insight {
  insight: string
  timestamp_seconds: number | null
  time_formatted: string | null
}

export interface Quote {
  quote: string
  speaker?: string
  timestamp_seconds?: number | null
  context?: string
}

export interface VideoFrame {
  url: string
  storage_path?: string
  timestamp_seconds: number
  time_formatted: string
  perceptual_hash?: string
  transcript_excerpt?: string
  transcript_summary?: string
}

export type Article = {
  id: number
  title: string
  url: string
  summary_html: string
  summary_text: string | null
  transcript_text: string | null
  original_article_text: string | null
  content_source: string | null
  video_id: string | null
  audio_url: string | null
  platform: string | null
  source: string | null
  created_at: string
  updated_at: string
  tags: string[] | null

  // Structured data fields
  key_insights: Insight[] | null
  quotes: Quote[] | null
  images: string[] | null  // Array of image URLs
  video_frames: VideoFrame[] | null  // Array of video frame thumbnails
  duration_minutes: number | null
  word_count: number | null
  topics: string[] | null
}

// Earnings insights types
export interface EarningsMetric {
  value: string
  speaker: string
  timestamp: string
}

export interface EarningsHighlight {
  text: string
  speaker: string
  timestamp: string
}

export interface EarningsRisk {
  text: string
  context: string
  speaker: string
  timestamp: string
}

export interface EarningsQuote {
  quote: string
  context: string
  speaker: string
  timestamp: string
}

export interface EarningsInsights {
  id: number
  earnings_call_id: number
  company_id: number
  symbol: string
  quarter: string
  key_metrics: Record<string, EarningsMetric>
  business_highlights: EarningsHighlight[]
  guidance: Record<string, EarningsMetric>
  risks_concerns: EarningsRisk[]
  positives: EarningsHighlight[]
  notable_quotes: EarningsQuote[]
  created_at: string
  updated_at: string
}

export interface EarningsCall {
  id: number
  company_id: number
  symbol: string
  quarter: string
  fiscal_year: number
  call_date: string | null
  earnings_url: string | null
  transcript_text: string | null
  transcript_json: any
  audio_url: string | null
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  error_message: string | null
  summary_json: any
  created_at: string
  updated_at: string
}

export interface EarningsCompany {
  id: number
  symbol: string
  name: string
  sector: string | null
  industry: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}