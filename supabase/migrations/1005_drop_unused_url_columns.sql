-- =====================================================
-- Migration: Drop unused URL columns from content_queue
-- =====================================================
-- Purpose: Remove channel_url and source_feed columns
--          These fields are not displayed in the UI and are redundant:
--          - channel_url: Podcast homepage (not used)
--          - source_feed: RSS feed URL (can be joined from content_sources if needed)
--
--          We keep:
--          - url: The actual episode/article URL (needed for processing)
--          - channel_title: Podcast/newsletter name (displayed in UI)
--          - source/platform: Discovery mechanism (used for filtering/debugging)
-- =====================================================

-- Drop channel_url column
ALTER TABLE content_queue
DROP COLUMN IF EXISTS channel_url;

-- Drop saource_feed column
ALTER TABLE content_queue
DROP COLUMN IF EXISTS source_feed;

-- Add comment explaining what we kept and why
COMMENT ON COLUMN content_queue.url IS
  'The actual episode/article URL to process. This is the primary URL for content processing.';

COMMENT ON COLUMN content_queue.channel_title IS
  'Podcast/newsletter name for display purposes. Sourced from RSS metadata or PocketCasts API.';

-- Migration complete
-- If you need to revert, run:
-- ALTER TABLE content_queue ADD COLUMN channel_url TEXT;
-- ALTER TABLE content_queue ADD COLUMN source_feed TEXT;
