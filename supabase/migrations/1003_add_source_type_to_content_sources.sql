-- Migration: Add source_type column to content_sources table
-- Purpose: Store whether a source was added as a 'newsletter' or 'podcast'
--          This determines whether to prefer webpage links or audio URLs when checking for new posts

-- Add source_type column with default 'newsletter'
ALTER TABLE content_sources
ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'newsletter' CHECK (source_type IN ('newsletter', 'podcast'));

-- Update existing rows to default to 'newsletter'
UPDATE content_sources
SET source_type = 'newsletter'
WHERE source_type IS NULL;

-- Add NOT NULL constraint after updating existing rows
ALTER TABLE content_sources
ALTER COLUMN source_type SET NOT NULL;

-- Add comment to document the column
COMMENT ON COLUMN content_sources.source_type IS 'Type of source: newsletter (prefer webpage links) or podcast (prefer audio URLs)';
