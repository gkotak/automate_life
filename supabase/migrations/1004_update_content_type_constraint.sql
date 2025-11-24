-- =====================================================
-- Migration: Update content_type CHECK constraint
-- =====================================================
-- Purpose: Allow new content_type value 'podcast/audio'
--          alongside existing 'podcast_episode' and 'article'
-- =====================================================

-- Drop the existing CHECK constraint
ALTER TABLE content_queue
DROP CONSTRAINT IF EXISTS content_queue_content_type_check;

-- Add updated CHECK constraint with all valid values
ALTER TABLE content_queue
ADD CONSTRAINT content_queue_content_type_check
CHECK (content_type IN ('podcast_episode', 'article', 'podcast/audio'));

-- Add comment explaining the values
COMMENT ON COLUMN content_queue.content_type IS
  'Type of content:
   - podcast_episode: PocketCasts history entries (hardcoded)
   - podcast/audio: RSS feed entries with audio file URLs (detected via .mp3, .m4a, etc.)
   - article: RSS feed entries with webpage URLs';
