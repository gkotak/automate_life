-- =====================================================
-- Migration: Rename known_channels to public_channels
-- =====================================================
-- Purpose: Rename table and add columns to support multiple URL types
--          for determining if content is from a "public" channel
--
-- The existing table has source_url as primary key. We need to:
--   1. Create a new table with proper structure
--   2. Migrate data
--   3. Drop old table
-- =====================================================

-- Step 1: Create the new public_channels table
CREATE TABLE public_channels (
  id SERIAL PRIMARY KEY,
  channel_name TEXT NOT NULL,

  -- URL columns (all nullable, but at least one required via check constraint)
  pocketcasts_channel_url TEXT,
  youtube_channel_url TEXT,
  podcast_feed_url TEXT,
  rss_feed_url TEXT,
  newsletter_url TEXT,

  -- Metadata
  notes TEXT,
  is_active BOOLEAN DEFAULT TRUE NOT NULL,

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Step 2: Copy existing data from old table
INSERT INTO public_channels (
  channel_name,
  pocketcasts_channel_url,
  youtube_channel_url,
  notes,
  is_active,
  created_at,
  updated_at
)
SELECT
  channel_name,
  source_url,
  youtube_url,
  notes,
  COALESCE(is_active, TRUE),
  COALESCE(created_at, NOW()),
  COALESCE(updated_at, NOW())
FROM known_channels;

-- Step 3: Drop old table
DROP TABLE known_channels;

-- Step 4: Add unique constraint on channel_name
ALTER TABLE public_channels ADD CONSTRAINT public_channels_channel_name_key UNIQUE (channel_name);

-- Step 5: Create indexes for efficient lookups on all URL columns
CREATE INDEX idx_public_channels_pocketcasts_url
  ON public_channels(pocketcasts_channel_url)
  WHERE pocketcasts_channel_url IS NOT NULL;

CREATE INDEX idx_public_channels_youtube_url
  ON public_channels(youtube_channel_url)
  WHERE youtube_channel_url IS NOT NULL;

CREATE INDEX idx_public_channels_podcast_feed_url
  ON public_channels(podcast_feed_url)
  WHERE podcast_feed_url IS NOT NULL;

CREATE INDEX idx_public_channels_rss_feed_url
  ON public_channels(rss_feed_url)
  WHERE rss_feed_url IS NOT NULL;

CREATE INDEX idx_public_channels_newsletter_url
  ON public_channels(newsletter_url)
  WHERE newsletter_url IS NOT NULL;

CREATE INDEX idx_public_channels_active
  ON public_channels(is_active)
  WHERE is_active = TRUE;

-- Step 6: Add check constraint to ensure at least one URL is provided
ALTER TABLE public_channels
  ADD CONSTRAINT public_channels_at_least_one_url CHECK (
    pocketcasts_channel_url IS NOT NULL OR
    youtube_channel_url IS NOT NULL OR
    podcast_feed_url IS NOT NULL OR
    rss_feed_url IS NOT NULL OR
    newsletter_url IS NOT NULL
  );

-- Step 7: Enable RLS
ALTER TABLE public_channels ENABLE ROW LEVEL SECURITY;

-- Step 8: Create RLS policies
CREATE POLICY "Allow authenticated read"
  ON public_channels
  FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow authenticated insert/update/delete"
  ON public_channels
  FOR ALL
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- Step 9: Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_public_channels_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER public_channels_updated_at
  BEFORE UPDATE ON public_channels
  FOR EACH ROW
  EXECUTE FUNCTION update_public_channels_updated_at();

-- Step 10: Add comments
COMMENT ON TABLE public_channels IS
  'Public channels (podcasts, newsletters, blogs, YouTube) used to determine if content should be public vs private. If a URL matches any column, the content is considered public.';

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
