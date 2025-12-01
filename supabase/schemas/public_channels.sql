-- =====================================================
-- Table: public_channels
-- =====================================================
-- Purpose: Defines known public content channels (podcasts, newsletters,
--          blogs, YouTube) used to determine if content should be public
--          vs private. If a URL matches any column, content is public.
--
-- Usage: When article_processor processes content, it checks this table
--        to determine if the source is a known public channel. If found,
--        the article is saved to the public articles table; otherwise
--        it's saved as a private article.
-- =====================================================

CREATE TABLE IF NOT EXISTS public_channels (
  -- Primary key
  id SERIAL PRIMARY KEY,

  -- Channel identification
  channel_name TEXT UNIQUE NOT NULL,

  -- URL columns (all nullable, but at least one required via check constraint)
  pocketcasts_channel_url TEXT,    -- PocketCasts channel page URL
  youtube_channel_url TEXT,         -- YouTube channel or playlist URL
  podcast_feed_url TEXT,            -- Podcast RSS feed URL
  rss_feed_url TEXT,                -- Generic RSS/Atom feed URL for blogs
  newsletter_url TEXT,              -- Newsletter URL (Substack, Beehiiv, etc.)

  -- Metadata
  notes TEXT,                       -- Optional notes about the channel
  is_active BOOLEAN DEFAULT TRUE NOT NULL,

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

  -- At least one URL must be provided
  CONSTRAINT public_channels_at_least_one_url CHECK (
    pocketcasts_channel_url IS NOT NULL OR
    youtube_channel_url IS NOT NULL OR
    podcast_feed_url IS NOT NULL OR
    rss_feed_url IS NOT NULL OR
    newsletter_url IS NOT NULL
  )
);

-- Indexes for efficient lookups on all URL columns
CREATE INDEX IF NOT EXISTS idx_public_channels_pocketcasts_url
  ON public_channels(pocketcasts_channel_url)
  WHERE pocketcasts_channel_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_public_channels_youtube_url
  ON public_channels(youtube_channel_url)
  WHERE youtube_channel_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_public_channels_podcast_feed_url
  ON public_channels(podcast_feed_url)
  WHERE podcast_feed_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_public_channels_rss_feed_url
  ON public_channels(rss_feed_url)
  WHERE rss_feed_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_public_channels_newsletter_url
  ON public_channels(newsletter_url)
  WHERE newsletter_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_public_channels_active
  ON public_channels(is_active)
  WHERE is_active = TRUE;

-- Row Level Security (RLS)
ALTER TABLE public_channels ENABLE ROW LEVEL SECURITY;

-- Policies: Allow authenticated users to read/write
CREATE POLICY "Allow authenticated read"
  ON public_channels
  FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow authenticated insert/update/delete"
  ON public_channels
  FOR ALL
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_public_channels_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to call the function
CREATE TRIGGER public_channels_updated_at
  BEFORE UPDATE ON public_channels
  FOR EACH ROW
  EXECUTE FUNCTION update_public_channels_updated_at();

-- Comments for documentation
COMMENT ON TABLE public_channels IS
  'Public channels (podcasts, newsletters, blogs, YouTube) used to determine if content should be public vs private';

COMMENT ON COLUMN public_channels.channel_name IS
  'Channel/podcast/newsletter name (e.g., "All-In Podcast", "Stratechery")';

COMMENT ON COLUMN public_channels.pocketcasts_channel_url IS
  'PocketCasts channel page URL (e.g., https://pca.st/podcast/...)';

COMMENT ON COLUMN public_channels.youtube_channel_url IS
  'YouTube channel or playlist URL (e.g., https://www.youtube.com/@channelname)';

COMMENT ON COLUMN public_channels.podcast_feed_url IS
  'Podcast RSS feed URL (e.g., https://feeds.example.com/podcast.xml)';

COMMENT ON COLUMN public_channels.rss_feed_url IS
  'Generic RSS/Atom feed URL for blogs (e.g., https://blog.example.com/feed)';

COMMENT ON COLUMN public_channels.newsletter_url IS
  'Newsletter URL (e.g., https://example.substack.com)';
