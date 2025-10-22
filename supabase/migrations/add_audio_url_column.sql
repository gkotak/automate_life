-- Add audio_url column to articles table
ALTER TABLE articles ADD COLUMN IF NOT EXISTS audio_url TEXT;

-- Add comment explaining the column
COMMENT ON COLUMN articles.audio_url IS 'URL to embedded audio file (MP3, etc.) for audio content';

-- Update existing audio articles (if any)
-- This will need to be run manually or articles will need to be reprocessed
