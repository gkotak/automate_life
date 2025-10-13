-- Remove redundant columns: main_points, takeaways, sentiment, complexity_level
-- These fields have been consolidated into key_insights
-- Run this in Supabase SQL editor

-- Drop indexes first (if they exist)
DROP INDEX IF EXISTS articles_main_points_idx;

-- Drop columns
ALTER TABLE articles DROP COLUMN IF EXISTS main_points;
ALTER TABLE articles DROP COLUMN IF EXISTS takeaways;
ALTER TABLE articles DROP COLUMN IF EXISTS sentiment;
ALTER TABLE articles DROP COLUMN IF EXISTS complexity_level;

-- Update comment for key_insights to reflect new consolidated structure
COMMENT ON COLUMN articles.key_insights IS 'Array of insight objects combining key learnings, main points, and actionable takeaways: [{insight: string, timestamp_seconds: number, time_formatted: string}]';
