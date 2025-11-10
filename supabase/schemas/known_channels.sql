-- =====================================================
-- Table: known_channels
-- =====================================================
-- Purpose: Maps channel names (podcasts, newsletters, blogs) to their
--          YouTube channels/playlists for reliable video discovery
--          without needing to scrape content pages.
--
-- Usage: When post_checker or podcast_checker finds new content, it
--        checks this table first for a known YouTube URL before
--        falling back to scraping the content page.
-- =====================================================

CREATE TABLE IF NOT EXISTS known_channels (
  -- Primary key
  id SERIAL PRIMARY KEY,

  -- Channel identification (podcast name, newsletter name, etc.)
  channel_name TEXT UNIQUE NOT NULL,

  -- YouTube URL (channel or playlist)
  -- Can be channel: https://www.youtube.com/@username
  -- Or playlist: https://www.youtube.com/playlist?list=...
  youtube_url TEXT NOT NULL,

  -- Metadata
  notes TEXT,                    -- Optional notes about the channel's YouTube presence
  is_active BOOLEAN DEFAULT TRUE NOT NULL,

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_known_channels_name
  ON known_channels(channel_name);

CREATE INDEX IF NOT EXISTS idx_known_channels_active
  ON known_channels(is_active)
  WHERE is_active = TRUE;

-- Row Level Security (RLS)
ALTER TABLE known_channels ENABLE ROW LEVEL SECURITY;

-- Policies: Allow authenticated users to read/write
CREATE POLICY "Allow authenticated read"
  ON known_channels
  FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow authenticated insert/update/delete"
  ON known_channels
  FOR ALL
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_known_channels_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to call the function
CREATE TRIGGER known_channels_updated_at
  BEFORE UPDATE ON known_channels
  FOR EACH ROW
  EXECUTE FUNCTION update_known_channels_updated_at();

-- Comments for documentation
COMMENT ON TABLE known_channels IS
  'Maps channel names (podcasts, newsletters, etc.) to YouTube channels/playlists for reliable video discovery';

COMMENT ON COLUMN known_channels.channel_name IS
  'Channel/podcast/newsletter name (e.g., "All-In Podcast", "Stratechery")';

COMMENT ON COLUMN known_channels.youtube_url IS
  'YouTube channel or playlist URL - discovery service determines type and scrapes accordingly';
