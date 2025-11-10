-- Add support for video frame thumbnails in demo videos
-- This allows storing extracted frames from screen-share demos

-- Add video_frames JSONB column to articles table
ALTER TABLE articles ADD COLUMN IF NOT EXISTS video_frames JSONB DEFAULT '[]';

-- Create index for video_frames column for better query performance
CREATE INDEX IF NOT EXISTS articles_video_frames_idx ON articles USING gin(video_frames);

-- Add comment for documentation
COMMENT ON COLUMN articles.video_frames IS 'Array of frame objects for demo videos: [{url: string, timestamp_seconds: number, time_formatted: string, storage_path: string}]';

-- Optional: Create a separate table for video frames if we want more structure
-- This is useful if we want to query frames independently or add more metadata later
CREATE TABLE IF NOT EXISTS video_frames (
  id SERIAL PRIMARY KEY,
  article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,  -- Path in Supabase storage
  url TEXT NOT NULL,  -- Public URL to frame
  timestamp_seconds FLOAT NOT NULL,
  time_formatted TEXT NOT NULL,
  perceptual_hash TEXT,  -- Hash for deduplication
  width INTEGER,
  height INTEGER,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(article_id, timestamp_seconds)  -- Prevent duplicate frames at same timestamp
);

-- Create indexes for video_frames table
CREATE INDEX IF NOT EXISTS video_frames_article_id_idx ON video_frames(article_id);
CREATE INDEX IF NOT EXISTS video_frames_timestamp_idx ON video_frames(timestamp_seconds);

-- Enable Row Level Security
ALTER TABLE video_frames ENABLE ROW LEVEL SECURITY;

-- RLS Policies for video_frames (same as articles)
CREATE POLICY "Users can view all video frames" ON video_frames FOR SELECT USING (true);
CREATE POLICY "Users can insert video frames" ON video_frames FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update video frames" ON video_frames FOR UPDATE USING (true);
CREATE POLICY "Users can delete video frames" ON video_frames FOR DELETE USING (true);

-- Function to get frames for an article with proper formatting
CREATE OR REPLACE FUNCTION get_article_frames(article_id_param INTEGER)
RETURNS TABLE (
  id INT,
  url TEXT,
  timestamp_seconds FLOAT,
  time_formatted TEXT,
  perceptual_hash TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    vf.id,
    vf.url,
    vf.timestamp_seconds,
    vf.time_formatted,
    vf.perceptual_hash
  FROM video_frames vf
  WHERE vf.article_id = article_id_param
  ORDER BY vf.timestamp_seconds ASC;
END;
$$;
