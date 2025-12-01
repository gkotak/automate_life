-- =====================================================
-- Migration: Add YouTube channel support
-- =====================================================
-- Purpose: Allow users to add YouTube channels directly
--          as content sources for video discovery
-- =====================================================

-- 1. Update content_sources.source_type constraint
-- Drop the existing CHECK constraint
ALTER TABLE content_sources
DROP CONSTRAINT IF EXISTS content_sources_source_type_check;

-- Add updated CHECK constraint with youtube_channel
ALTER TABLE content_sources
ADD CONSTRAINT content_sources_source_type_check
CHECK (source_type IN ('newsletter', 'podcast', 'youtube_channel'));

-- Add comment explaining the values
COMMENT ON COLUMN content_sources.source_type IS
  'Type of content source:
   - newsletter: RSS feeds, blogs, Substack, etc.
   - podcast: Podcast RSS feeds (audio-focused)
   - youtube_channel: YouTube channels (stores RSS feed URL: https://www.youtube.com/feeds/videos.xml?channel_id=...)';

-- 2. Update content_queue.content_type constraint to include YouTube videos
-- Drop the existing CHECK constraint
ALTER TABLE content_queue
DROP CONSTRAINT IF EXISTS content_queue_content_type_check;

-- Add updated CHECK constraint with all valid values
ALTER TABLE content_queue
ADD CONSTRAINT content_queue_content_type_check
CHECK (content_type IN ('podcast_episode', 'article', 'podcast/audio', 'youtube_video'));

-- Add comment explaining the values
COMMENT ON COLUMN content_queue.content_type IS
  'Type of content:
   - podcast_episode: PocketCasts history entries (hardcoded)
   - podcast/audio: RSS feed entries with audio file URLs (detected via .mp3, .m4a, etc.)
   - article: RSS feed entries with webpage URLs (includes YouTube videos, newsletters, blog posts)
   - youtube_video: Explicit YouTube video URLs (reserved for future use)';

-- Note: Currently YouTube videos from RSS feeds are stored as content_type='article'
-- The 'youtube_video' type is added for future differentiation if needed
