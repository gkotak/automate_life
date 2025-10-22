-- Add images column to articles table for storing article image URLs
-- Run this in your Supabase SQL editor

-- Add images column (TEXT array to store image URLs)
ALTER TABLE articles ADD COLUMN IF NOT EXISTS images TEXT[] DEFAULT ARRAY[]::TEXT[];

-- Add comment for documentation
COMMENT ON COLUMN articles.images IS 'Array of image URLs found in the article';
