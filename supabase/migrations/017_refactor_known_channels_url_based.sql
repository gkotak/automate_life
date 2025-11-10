-- =====================================================
-- Migration: Refactor known_channels to URL-based lookup
-- =====================================================
-- Purpose: Use source_url as primary lookup key instead of
--          channel_name to avoid naming mismatches
-- =====================================================

-- Add source_url column (this is the RSS feed URL or content source URL)
ALTER TABLE known_channels
ADD COLUMN IF NOT EXISTS source_url TEXT;

-- Make channel_name optional (it's now just a label)
ALTER TABLE known_channels
ALTER COLUMN channel_name DROP NOT NULL;

-- Add unique constraint on source_url
CREATE UNIQUE INDEX IF NOT EXISTS idx_known_channels_source_url
ON known_channels(source_url)
WHERE is_active = TRUE;

-- Drop old unique constraint on channel_name (allow duplicates now)
DROP INDEX IF EXISTS known_channels_channel_name_key;

-- Add index for faster URL lookups
CREATE INDEX IF NOT EXISTS idx_known_channels_source_url_lookup
ON known_channels(source_url)
WHERE is_active = TRUE AND source_url IS NOT NULL;

-- Update comments
COMMENT ON TABLE known_channels IS
  'Maps content source URLs (RSS feeds, etc.) to YouTube channels/playlists for reliable video discovery';

COMMENT ON COLUMN known_channels.source_url IS
  'Content source URL (RSS feed, PocketCasts channel, etc.) - primary lookup key';

COMMENT ON COLUMN known_channels.channel_name IS
  'Optional human-readable channel name (e.g., "All-In Podcast", "Stratechery")';

COMMENT ON COLUMN known_channels.youtube_url IS
  'YouTube channel or playlist URL - discovery service determines type and scrapes accordingly';

-- Migration note: Existing rows will have NULL source_url
-- You'll need to populate these manually after migration
