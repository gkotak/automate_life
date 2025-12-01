-- Migration: Add media persistence columns for Phase 2 reprocessing
-- Purpose: Enable video frame re-extraction and transcript regeneration without re-downloading media
--
-- Key design decisions:
-- 1. Single column set for all media types (system-downloaded with TTL, or user-uploaded permanent)
-- 2. Using media_uploaded_at instead of expires_at to allow flexible TTL changes via env var
-- 3. Cleanup script calculates expiry from MEDIA_RETENTION_DAYS env var
-- 4. For direct uploads, media_storage_bucket = 'uploaded-media' and cleanup script skips these

-- Add media storage fields to articles
ALTER TABLE articles ADD COLUMN IF NOT EXISTS media_storage_path TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS media_storage_bucket TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS media_uploaded_at TIMESTAMPTZ;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS media_content_type TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS media_size_bytes BIGINT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS media_duration_seconds FLOAT;

-- Add media storage fields to private_articles
ALTER TABLE private_articles ADD COLUMN IF NOT EXISTS media_storage_path TEXT;
ALTER TABLE private_articles ADD COLUMN IF NOT EXISTS media_storage_bucket TEXT;
ALTER TABLE private_articles ADD COLUMN IF NOT EXISTS media_uploaded_at TIMESTAMPTZ;
ALTER TABLE private_articles ADD COLUMN IF NOT EXISTS media_content_type TEXT;
ALTER TABLE private_articles ADD COLUMN IF NOT EXISTS media_size_bytes BIGINT;
ALTER TABLE private_articles ADD COLUMN IF NOT EXISTS media_duration_seconds FLOAT;

-- Create index for cleanup job (find media to potentially expire)
-- The cleanup script will filter by bucket and calculate TTL dynamically
CREATE INDEX IF NOT EXISTS idx_articles_media_uploaded ON articles(media_uploaded_at)
  WHERE media_storage_path IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_private_articles_media_uploaded ON private_articles(media_uploaded_at)
  WHERE media_storage_path IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN articles.media_storage_path IS 'Path within the storage bucket (e.g., public/123/media.mp4)';
COMMENT ON COLUMN articles.media_storage_bucket IS 'Supabase storage bucket name (article-media for downloaded, uploaded-media for direct uploads)';
COMMENT ON COLUMN articles.media_uploaded_at IS 'When media was uploaded to storage; used with MEDIA_RETENTION_DAYS env var for TTL calculation';
COMMENT ON COLUMN articles.media_content_type IS 'MIME type of the stored media (e.g., video/mp4, audio/mpeg)';
COMMENT ON COLUMN articles.media_size_bytes IS 'Size of the stored media file in bytes';
COMMENT ON COLUMN articles.media_duration_seconds IS 'Duration of the media in seconds';

COMMENT ON COLUMN private_articles.media_storage_path IS 'Path within the storage bucket (e.g., private/123/media.mp4)';
COMMENT ON COLUMN private_articles.media_storage_bucket IS 'Supabase storage bucket name (article-media for downloaded, uploaded-media for direct uploads)';
COMMENT ON COLUMN private_articles.media_uploaded_at IS 'When media was uploaded to storage; used with MEDIA_RETENTION_DAYS env var for TTL calculation';
COMMENT ON COLUMN private_articles.media_content_type IS 'MIME type of the stored media (e.g., video/mp4, audio/mpeg)';
COMMENT ON COLUMN private_articles.media_size_bytes IS 'Size of the stored media file in bytes';
COMMENT ON COLUMN private_articles.media_duration_seconds IS 'Duration of the media in seconds';
