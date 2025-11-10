-- =====================================================
-- Migration: Rename known_podcasts to known_channels
-- =====================================================
-- Purpose: Make the table more generic to support YouTube
--          discovery for all content types, not just podcasts
-- =====================================================

-- Rename the table
ALTER TABLE IF EXISTS known_podcasts RENAME TO known_channels;

-- Rename the podcast_title column to channel_name
ALTER TABLE IF EXISTS known_channels RENAME COLUMN podcast_title TO channel_name;

-- Update index names
DROP INDEX IF EXISTS idx_known_podcasts_title;
DROP INDEX IF EXISTS idx_known_podcasts_active;

CREATE INDEX IF NOT EXISTS idx_known_channels_name
  ON known_channels(channel_name);

CREATE INDEX IF NOT EXISTS idx_known_channels_active
  ON known_channels(is_active)
  WHERE is_active = TRUE;

-- Update function and trigger names
DROP TRIGGER IF EXISTS known_podcasts_updated_at ON known_channels;
DROP FUNCTION IF EXISTS update_known_podcasts_updated_at();

CREATE OR REPLACE FUNCTION update_known_channels_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER known_channels_updated_at
  BEFORE UPDATE ON known_channels
  FOR EACH ROW
  EXECUTE FUNCTION update_known_channels_updated_at();

-- Update table and column comments
COMMENT ON TABLE known_channels IS
  'Maps channel names (podcasts, newsletters, etc.) to YouTube channels/playlists for reliable video discovery';

COMMENT ON COLUMN known_channels.channel_name IS
  'Channel/podcast name (e.g., "All-In Podcast", "Stratechery")';

COMMENT ON COLUMN known_channels.youtube_url IS
  'YouTube channel or playlist URL - discovery service determines type and scrapes accordingly';

COMMENT ON COLUMN known_channels.notes IS
  'Optional notes about the channel and its YouTube presence';
