-- Add structured JSON fields for rich article data
-- Run this in Supabase SQL editor to add new columns

-- Add structured data columns
ALTER TABLE articles ADD COLUMN IF NOT EXISTS key_insights JSONB DEFAULT '[]';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS main_points JSONB DEFAULT '[]';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS quotes JSONB DEFAULT '[]';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS takeaways TEXT[] DEFAULT '{}';

-- Add metadata columns
ALTER TABLE articles ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS word_count INTEGER;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS topics TEXT[] DEFAULT '{}';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS sentiment TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS complexity_level TEXT;

-- Create indexes for JSON columns for better query performance
CREATE INDEX IF NOT EXISTS articles_key_insights_idx ON articles USING gin(key_insights);
CREATE INDEX IF NOT EXISTS articles_main_points_idx ON articles USING gin(main_points);
CREATE INDEX IF NOT EXISTS articles_quotes_idx ON articles USING gin(quotes);
CREATE INDEX IF NOT EXISTS articles_topics_idx ON articles USING gin(topics);

-- Add comments for documentation
COMMENT ON COLUMN articles.key_insights IS 'Array of insight objects: [{insight: string, timestamp_seconds: number, time_formatted: string}]';
COMMENT ON COLUMN articles.main_points IS 'Array of main point objects: [{point: string, details: string}]';
COMMENT ON COLUMN articles.quotes IS 'Array of quote objects: [{quote: string, speaker: string, timestamp_seconds: number, context: string}]';
COMMENT ON COLUMN articles.takeaways IS 'Array of key takeaway strings';
COMMENT ON COLUMN articles.duration_minutes IS 'Video/audio duration in minutes';
COMMENT ON COLUMN articles.word_count IS 'Approximate word count of content';
COMMENT ON COLUMN articles.topics IS 'Array of topic tags extracted from content';
COMMENT ON COLUMN articles.sentiment IS 'Overall sentiment: positive, negative, neutral, mixed';
COMMENT ON COLUMN articles.complexity_level IS 'Content complexity: beginner, intermediate, advanced';
