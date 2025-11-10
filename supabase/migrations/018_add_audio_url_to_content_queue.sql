-- =====================================================
-- Migration: Add audio_url column to content_queue
-- =====================================================
-- Purpose: Store direct audio file URLs for podcast episodes
--          extracted from RSS feed enclosures
-- =====================================================

-- Add audio_url column to content_queue
ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS audio_url TEXT;

-- Add index for faster lookups by audio URL
CREATE INDEX IF NOT EXISTS idx_content_queue_audio_url
ON content_queue(audio_url)
WHERE audio_url IS NOT NULL;

-- Add comment
COMMENT ON COLUMN content_queue.audio_url IS
  'Direct audio file URL from podcast RSS feed enclosure (e.g., MP3 file URL)';
