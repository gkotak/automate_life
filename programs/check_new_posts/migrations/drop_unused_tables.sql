-- Drop unused tables from database cleanup
-- These tables have been replaced by content_queue and content_sources

-- Drop processing_queue (replaced by content_queue table)
DROP TABLE IF EXISTS processing_queue;

-- Drop rss_feeds (replaced by content_sources table)
DROP TABLE IF EXISTS rss_feeds;
