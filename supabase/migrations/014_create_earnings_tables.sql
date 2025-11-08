-- =====================================================
-- Earnings Insights - Database Schema
-- Migration: 014_create_earnings_tables.sql
-- =====================================================
--
-- This migration creates three tables for the earnings_insights program:
-- 1. earnings_companies - List of companies to track
-- 2. earnings_calls - Raw earnings call data (transcript, audio, presentation)
-- 3. earnings_insights - Processed AI insights with timestamps
--
-- Run this in Supabase SQL Editor
-- =====================================================

-- Enable vector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================
-- Table 1: earnings_companies
-- =====================================================
-- Stores the list of companies to track earnings for

CREATE TABLE earnings_companies (
  id SERIAL PRIMARY KEY,
  symbol TEXT UNIQUE NOT NULL,           -- Stock ticker (e.g., "AAPL")
  name TEXT NOT NULL,                     -- Company name (e.g., "Apple Inc.")
  sector TEXT,                            -- Industry sector (e.g., "Technology")
  investor_relations_url TEXT,            -- IR page URL
  seekingalpha_url TEXT,                  -- Seeking Alpha company page
  is_active BOOLEAN DEFAULT true,         -- Whether to track this company
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for earnings_companies
CREATE INDEX earnings_companies_symbol_idx ON earnings_companies(symbol);
CREATE INDEX earnings_companies_active_idx ON earnings_companies(is_active);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_earnings_companies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER earnings_companies_updated_at_trigger
  BEFORE UPDATE ON earnings_companies
  FOR EACH ROW
  EXECUTE FUNCTION update_earnings_companies_updated_at();

COMMENT ON TABLE earnings_companies IS 'List of companies to track earnings for';
COMMENT ON COLUMN earnings_companies.symbol IS 'Stock ticker symbol (e.g., AAPL, MSFT)';
COMMENT ON COLUMN earnings_companies.is_active IS 'Set to false to stop tracking a company';

-- =====================================================
-- Table 2: earnings_calls
-- =====================================================
-- Stores raw earnings call data (transcript, audio, presentation)

CREATE TABLE earnings_calls (
  id SERIAL PRIMARY KEY,
  company_id INTEGER REFERENCES earnings_companies(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  quarter TEXT NOT NULL,                  -- e.g., "Q1 2024"
  fiscal_year INTEGER NOT NULL,
  earnings_date DATE,                     -- Actual earnings release date
  call_date TIMESTAMP,                    -- When call occurred

  -- Transcript storage (TWO columns for flexibility)
  transcript_text TEXT,                   -- Original clean transcript (from Seeking Alpha)
  transcript_json JSONB,                  -- Aligned version with timestamps (from Deepgram)
  transcript_source TEXT,                 -- 'seekingalpha', 'investor_relations', 'deepgram'

  -- Audio
  audio_url TEXT,                         -- MP3/audio file URL
  audio_source TEXT,                      -- 'seekingalpha', 'investor_relations'
  audio_duration_seconds INTEGER,

  -- Presentation
  presentation_url TEXT,                  -- PDF/slides URL
  presentation_source TEXT,

  -- AI-generated summary (full JSON output from Claude)
  summary_json JSONB,

  -- Semantic search (for future feature: search across all earnings)
  embedding VECTOR(1536),                 -- OpenAI embedding

  -- Processing status
  processing_status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
  error_message TEXT,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Ensure unique combination of company + quarter + year
  UNIQUE(company_id, quarter, fiscal_year)
);

-- Indexes for earnings_calls
CREATE INDEX earnings_calls_company_idx ON earnings_calls(company_id);
CREATE INDEX earnings_calls_symbol_idx ON earnings_calls(symbol);
CREATE INDEX earnings_calls_quarter_idx ON earnings_calls(quarter, fiscal_year);
CREATE INDEX earnings_calls_status_idx ON earnings_calls(processing_status);
CREATE INDEX earnings_calls_date_idx ON earnings_calls(call_date DESC);
CREATE INDEX earnings_calls_embedding_idx ON earnings_calls USING ivfflat(embedding vector_cosine_ops);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_earnings_calls_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER earnings_calls_updated_at_trigger
  BEFORE UPDATE ON earnings_calls
  FOR EACH ROW
  EXECUTE FUNCTION update_earnings_calls_updated_at();

COMMENT ON TABLE earnings_calls IS 'Raw earnings call data including transcript, audio, and presentation';
COMMENT ON COLUMN earnings_calls.transcript_text IS 'Original clean transcript (human-edited, from Seeking Alpha)';
COMMENT ON COLUMN earnings_calls.transcript_json IS 'Aligned transcript with timestamps (formatted for Claude and web app)';
COMMENT ON COLUMN earnings_calls.summary_json IS 'Full Claude analysis output (raw JSON)';
COMMENT ON COLUMN earnings_calls.embedding IS 'OpenAI embedding for semantic search';

-- =====================================================
-- Table 3: earnings_insights
-- =====================================================
-- Extracted key insights for fast queries (denormalized from summary_json)

CREATE TABLE earnings_insights (
  id SERIAL PRIMARY KEY,
  earnings_call_id INTEGER REFERENCES earnings_calls(id) ON DELETE CASCADE,
  company_id INTEGER REFERENCES earnings_companies(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  quarter TEXT NOT NULL,

  -- AI-extracted insights (all include timestamps from aligned transcript)
  -- All fields are JSONB to support timestamps + speaker metadata
  key_metrics JSONB,              -- { "metric_name": { "value": "...", "timestamp": "05:30", "speaker": "CFO" } }
  business_highlights JSONB[],    -- [{ "text": "...", "timestamp": "03:20", "speaker": "CEO" }]
  guidance JSONB,                 -- { "q3_revenue": { "value": "...", "timestamp": "08:45" } }
  risks_concerns JSONB[],         -- [{ "text": "...", "timestamp": "10:30", "speaker": "CEO", "context": "concern" }]
  positives JSONB[],              -- [{ "text": "...", "timestamp": "05:30", "speaker": "CFO" }]
  notable_quotes JSONB[],         -- [{ "quote": "...", "timestamp": "15:45", "speaker": "CEO", "context": "..." }]

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for earnings_insights
CREATE INDEX earnings_insights_call_idx ON earnings_insights(earnings_call_id);
CREATE INDEX earnings_insights_company_idx ON earnings_insights(company_id);
CREATE INDEX earnings_insights_symbol_quarter_idx ON earnings_insights(symbol, quarter);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_earnings_insights_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER earnings_insights_updated_at_trigger
  BEFORE UPDATE ON earnings_insights
  FOR EACH ROW
  EXECUTE FUNCTION update_earnings_insights_updated_at();

COMMENT ON TABLE earnings_insights IS 'Processed AI insights extracted from earnings calls';
COMMENT ON COLUMN earnings_insights.key_metrics IS 'Financial highlights with timestamps (revenue growth, profitability, etc.)';
COMMENT ON COLUMN earnings_insights.business_highlights IS 'Key business updates with timestamps';
COMMENT ON COLUMN earnings_insights.guidance IS 'Forward-looking statements with timestamps';
COMMENT ON COLUMN earnings_insights.risks_concerns IS 'Concerns raised by management or analysts with timestamps';
COMMENT ON COLUMN earnings_insights.positives IS 'Positive developments with timestamps';
COMMENT ON COLUMN earnings_insights.notable_quotes IS 'Memorable quotes with timestamps';

-- =====================================================
-- Row Level Security (RLS)
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE earnings_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE earnings_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE earnings_insights ENABLE ROW LEVEL SECURITY;

-- Policies: Allow all operations for authenticated users
-- (Adjust these policies based on your authentication requirements)

-- earnings_companies policies
CREATE POLICY "Users can view all companies"
  ON earnings_companies FOR SELECT
  USING (true);

CREATE POLICY "Users can insert companies"
  ON earnings_companies FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Users can update companies"
  ON earnings_companies FOR UPDATE
  USING (true);

CREATE POLICY "Users can delete companies"
  ON earnings_companies FOR DELETE
  USING (true);

-- earnings_calls policies
CREATE POLICY "Users can view all earnings_calls"
  ON earnings_calls FOR SELECT
  USING (true);

CREATE POLICY "Users can insert earnings_calls"
  ON earnings_calls FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Users can update earnings_calls"
  ON earnings_calls FOR UPDATE
  USING (true);

CREATE POLICY "Users can delete earnings_calls"
  ON earnings_calls FOR DELETE
  USING (true);

-- earnings_insights policies
CREATE POLICY "Users can view all earnings_insights"
  ON earnings_insights FOR SELECT
  USING (true);

CREATE POLICY "Users can insert earnings_insights"
  ON earnings_insights FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Users can update earnings_insights"
  ON earnings_insights FOR UPDATE
  USING (true);

CREATE POLICY "Users can delete earnings_insights"
  ON earnings_insights FOR DELETE
  USING (true);

-- =====================================================
-- Verification Queries (Run after migration)
-- =====================================================

-- Verify tables were created
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'earnings_%';

-- Verify indexes
-- SELECT indexname FROM pg_indexes WHERE tablename IN ('earnings_companies', 'earnings_calls', 'earnings_insights');

-- Verify RLS is enabled
-- SELECT tablename, rowsecurity FROM pg_tables WHERE tablename LIKE 'earnings_%';

-- =====================================================
-- Sample Data (Optional - for testing)
-- =====================================================

-- Insert sample company
-- INSERT INTO earnings_companies (symbol, name, sector, seekingalpha_url, is_active)
-- VALUES ('AAPL', 'Apple Inc.', 'Technology', 'https://seekingalpha.com/symbol/AAPL', true);

-- =====================================================
-- Migration Complete
-- =====================================================