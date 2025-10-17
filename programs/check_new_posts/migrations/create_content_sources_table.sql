-- Migration: Create content_sources table
-- Purpose: Store newsletter, RSS feed, and podcast URLs to check for new content
-- Replaces: newsletter_podcast_links.md file

CREATE TABLE IF NOT EXISTS content_sources (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL CHECK (source_type IN ('rss_feed', 'newsletter', 'podcast', 'blog')),
    title TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    check_frequency TEXT DEFAULT 'daily' CHECK (check_frequency IN ('hourly', 'daily', 'weekly')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for active sources (most common query)
CREATE INDEX IF NOT EXISTS idx_content_sources_active ON content_sources(is_active, source_type);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_content_sources_updated_at BEFORE UPDATE
    ON content_sources FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Migrate existing data from newsletter_podcast_links.md
INSERT INTO content_sources (url, source_type, notes) VALUES
    ('https://stratechery.passport.online/feed/rss/2veiQRnCGxpwgPx1N8i91Q', 'rss_feed', 'RSS feed with auth tokens to access main pages. Ignore URLs to other platforms'),
    ('https://www.lennysnewsletter.com/', 'newsletter', 'Blog posts with video embeddings, typically YouTube'),
    ('https://creatoreconomy.so/', 'blog', 'Blog posts with video embeddings'),
    ('https://www.akashbajwa.co/', 'blog', 'Blog posts with video embeddings')
ON CONFLICT (url) DO NOTHING;

COMMENT ON TABLE content_sources IS 'Stores URLs for newsletters, RSS feeds, podcasts, and blogs to monitor for new content';
COMMENT ON COLUMN content_sources.url IS 'The URL to check for new content';
COMMENT ON COLUMN content_sources.source_type IS 'Type of content source: rss_feed, newsletter, podcast, or blog';
COMMENT ON COLUMN content_sources.title IS 'Display name for the source';
COMMENT ON COLUMN content_sources.notes IS 'Additional notes about this source (auth requirements, special handling, etc.)';
COMMENT ON COLUMN content_sources.is_active IS 'Whether to actively check this source for new content';
COMMENT ON COLUMN content_sources.check_frequency IS 'How often to check this source: hourly, daily, or weekly';
