import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

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
  duration_minutes: number | null
  word_count: number | null
  topics: string[] | null
}