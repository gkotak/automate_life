-- =====================================================
-- Table: known_podcasts
-- =====================================================
-- Purpose: Maps podcast titles to their YouTube channels/playlists
--          for reliable video discovery without needing to scrape
--          PocketCasts pages.
--
-- Usage: When podcast_checker finds a new episode, it checks this
--        table first for a known YouTube URL before falling back
--        to scraping the PocketCasts episode page.
-- =====================================================

CREATE TABLE IF NOT EXISTS known_podcasts (
  -- Primary key
  id SERIAL PRIMARY KEY,

  -- Podcast identification (must match PocketCasts API title exactly)
  podcast_title TEXT UNIQUE NOT NULL,

  -- YouTube URL (channel or playlist)
  -- Can be channel: https://www.youtube.com/@username
  -- Or playlist: https://www.youtube.com/playlist?list=...
  youtube_url TEXT NOT NULL,

  -- Metadata
  notes TEXT,                    -- Optional notes about the podcast/channel
  is_active BOOLEAN DEFAULT TRUE NOT NULL,

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_known_podcasts_title
  ON known_podcasts(podcast_title);

CREATE INDEX IF NOT EXISTS idx_known_podcasts_active
  ON known_podcasts(is_active)
  WHERE is_active = TRUE;

-- Row Level Security (RLS)
ALTER TABLE known_podcasts ENABLE ROW LEVEL SECURITY;

-- Policies: Allow authenticated users to read/write
CREATE POLICY "Allow authenticated read"
  ON known_podcasts
  FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow authenticated insert/update/delete"
  ON known_podcasts
  FOR ALL
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_known_podcasts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to call the function
CREATE TRIGGER known_podcasts_updated_at
  BEFORE UPDATE ON known_podcasts
  FOR EACH ROW
  EXECUTE FUNCTION update_known_podcasts_updated_at();

-- Comments for documentation
COMMENT ON TABLE known_podcasts IS
  'Maps podcast titles to YouTube channels/playlists for reliable video discovery';

COMMENT ON COLUMN known_podcasts.podcast_title IS
  'Exact podcast title as it appears in PocketCasts API';

COMMENT ON COLUMN known_podcasts.youtube_url IS
  'YouTube channel or playlist URL - existing Step 1b logic determines type and scrapes accordingly';
