-- Create content_queue table
-- Unified table for discovered content (podcasts, articles, videos) awaiting processing

CREATE TABLE IF NOT EXISTS content_queue (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core content identification
    url TEXT NOT NULL UNIQUE,  -- Episode URL, Article URL, or YouTube URL
    title TEXT NOT NULL,  -- Episode title, Article title, or Video title
    content_type TEXT NOT NULL CHECK (content_type IN ('podcast_episode', 'article', 'youtube_video')),

    -- Channel/Source (parent container)
    channel_title TEXT,  -- Podcast name, Newsletter/Blog name, or YouTube channel
    channel_url TEXT,    -- Podcast channel URL, Newsletter homepage, or YouTube channel URL

    -- Media (YouTube video for podcasts and articles)
    video_url TEXT,  -- Full YouTube URL (if content has associated video)

    -- Discovery metadata
    platform TEXT NOT NULL,  -- 'pocketcasts', 'rss_feed', 'generic', 'youtube', etc.
    source_feed TEXT,  -- RSS feed URL that discovered this
    found_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_date TIMESTAMPTZ,

    -- Processing status
    status TEXT NOT NULL DEFAULT 'discovered' CHECK (status IN ('discovered', 'processing', 'processed', 'failed', 'skipped')),
    article_id INTEGER REFERENCES articles(id),  -- Link to processed article in articles table
    processed_at TIMESTAMPTZ,
    processing_error TEXT,

    -- Podcast-specific metadata (nullable, only for podcast_episode type)
    podcast_uuid TEXT,  -- PocketCasts podcast UUID
    episode_uuid TEXT,  -- PocketCasts episode UUID
    duration_seconds INTEGER,  -- Episode duration
    played_up_to INTEGER,  -- Seconds played (PocketCasts)
    progress_percent DECIMAL(5,2),  -- Playback progress 0-100
    playing_status INTEGER,  -- 1=unplayed, 2=in_progress, 3=played

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_content_queue_status ON content_queue(status);
CREATE INDEX IF NOT EXISTS idx_content_queue_found_at ON content_queue(found_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_queue_platform ON content_queue(platform);
CREATE INDEX IF NOT EXISTS idx_content_queue_content_type ON content_queue(content_type);
CREATE INDEX IF NOT EXISTS idx_content_queue_channel ON content_queue(channel_title);
CREATE INDEX IF NOT EXISTS idx_content_queue_unprocessed ON content_queue(status, found_at DESC)
    WHERE status IN ('discovered', 'failed');
CREATE INDEX IF NOT EXISTS idx_content_queue_article_id ON content_queue(article_id)
    WHERE article_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_content_queue_video ON content_queue(video_url)
    WHERE video_url IS NOT NULL;

-- Trigger for updated_at (reuses existing function)
CREATE TRIGGER update_content_queue_updated_at
    BEFORE UPDATE ON content_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Table and column comments
COMMENT ON TABLE content_queue IS 'Unified queue of discovered content (podcasts, articles, videos) to process with article_summarizer';
COMMENT ON COLUMN content_queue.url IS 'The content URL (PocketCasts episode URL, article URL, or YouTube URL)';
COMMENT ON COLUMN content_queue.title IS 'Episode title, Article title, or Video title';
COMMENT ON COLUMN content_queue.content_type IS 'Type of content: podcast_episode, article, or youtube_video';
COMMENT ON COLUMN content_queue.channel_title IS 'Podcast name, Newsletter/Blog name, or YouTube channel (parent container)';
COMMENT ON COLUMN content_queue.channel_url IS 'Podcast channel URL, Newsletter homepage, or YouTube channel URL';
COMMENT ON COLUMN content_queue.video_url IS 'Associated YouTube video URL (for podcasts/articles with embedded video)';
COMMENT ON COLUMN content_queue.platform IS 'Discovery platform: pocketcasts, rss_feed, generic, youtube, etc.';
COMMENT ON COLUMN content_queue.source_feed IS 'RSS feed URL or source that discovered this content';
COMMENT ON COLUMN content_queue.status IS 'Processing status: discovered, processing, processed, failed, skipped';
COMMENT ON COLUMN content_queue.article_id IS 'Foreign key to articles table after successful processing';
COMMENT ON COLUMN content_queue.podcast_uuid IS 'PocketCasts podcast UUID (podcast_episode only)';
COMMENT ON COLUMN content_queue.episode_uuid IS 'PocketCasts episode UUID (podcast_episode only)';
COMMENT ON COLUMN content_queue.duration_seconds IS 'Episode or video duration in seconds';
COMMENT ON COLUMN content_queue.playing_status IS 'PocketCasts playback status: 1=unplayed, 2=in_progress, 3=played';
