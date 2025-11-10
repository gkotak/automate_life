-- =====================================================
-- Migration: Add source column to content_queue
-- =====================================================
-- Purpose: Track how content was discovered to separate
--          podcast_history from manually added rss_feed content
-- =====================================================

-- Add source column to content_queue
ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS source TEXT;

-- Add check constraint for valid source values
ALTER TABLE content_queue
ADD CONSTRAINT content_queue_source_check
CHECK (source IN ('podcast_history', 'rss_feed', 'manual'));

-- Backfill existing data:
-- - Rows with user_id IS NULL are from podcast_history (PocketCasts scraping)
-- - Rows with user_id are from rss_feed (manually added content sources)
UPDATE content_queue
SET source = CASE
    WHEN user_id IS NULL THEN 'podcast_history'
    ELSE 'rss_feed'
END
WHERE source IS NULL;

-- Make source column NOT NULL after backfilling
ALTER TABLE content_queue
ALTER COLUMN source SET NOT NULL;

-- Add index for faster filtering by source
CREATE INDEX IF NOT EXISTS idx_content_queue_source
ON content_queue(source);

-- Add comment
COMMENT ON COLUMN content_queue.source IS
  'How this content was discovered: podcast_history (PocketCasts scraping), rss_feed (manually added content sources), manual (user submitted)';
