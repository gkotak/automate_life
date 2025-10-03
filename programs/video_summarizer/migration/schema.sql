-- Video Summarizer Web App Database Schema
-- Run this in your Supabase SQL editor

-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Articles table - main content storage
CREATE TABLE articles (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  summary_html TEXT,
  content_text TEXT, -- Plain text for search
  video_id TEXT,
  platform TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  tags TEXT[],

  -- Search capabilities
  search_vector tsvector, -- PostgreSQL full-text search
  embedding vector(1536)  -- OpenAI embeddings for semantic search
);

-- RSS Feeds table
CREATE TABLE rss_feeds (
  id SERIAL PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  name TEXT,
  last_checked TIMESTAMP,
  active BOOLEAN DEFAULT true
);

-- Processing Queue table
CREATE TABLE processing_queue (
  id SERIAL PRIMARY KEY,
  url TEXT NOT NULL,
  status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
  error_message TEXT,
  progress_percentage INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Search indexes
CREATE INDEX articles_search_idx ON articles USING gin(search_vector);
CREATE INDEX articles_embedding_idx ON articles USING ivfflat(embedding vector_cosine_ops);
CREATE INDEX articles_created_at_idx ON articles(created_at DESC);
CREATE INDEX articles_url_idx ON articles(url);

-- Function to update search_vector automatically
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.content_text, ''));
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update search_vector on insert/update
CREATE TRIGGER articles_search_vector_trigger
  BEFORE INSERT OR UPDATE ON articles
  FOR EACH ROW
  EXECUTE FUNCTION update_search_vector();

-- Supabase function for vector similarity search
CREATE OR REPLACE FUNCTION match_articles(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id int,
  title text,
  url text,
  summary_html text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    articles.id,
    articles.title,
    articles.url,
    articles.summary_html,
    1 - (articles.embedding <=> query_embedding) as similarity
  FROM articles
  WHERE 1 - (articles.embedding <=> query_embedding) > match_threshold
  ORDER BY articles.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Function for hybrid search (full-text + semantic)
CREATE OR REPLACE FUNCTION hybrid_search(
  search_query text,
  query_embedding vector(1536) DEFAULT NULL,
  match_count int DEFAULT 20
)
RETURNS TABLE (
  id int,
  title text,
  url text,
  summary_html text,
  content_text text,
  created_at timestamp,
  search_rank float,
  semantic_similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.id,
    a.title,
    a.url,
    a.summary_html,
    a.content_text,
    a.created_at,
    COALESCE(ts_rank(a.search_vector, plainto_tsquery('english', search_query)), 0) as search_rank,
    CASE
      WHEN query_embedding IS NOT NULL THEN 1 - (a.embedding <=> query_embedding)
      ELSE 0
    END as semantic_similarity
  FROM articles a
  WHERE
    (search_query = '' OR a.search_vector @@ plainto_tsquery('english', search_query))
    OR
    (query_embedding IS NOT NULL AND 1 - (a.embedding <=> query_embedding) > 0.7)
  ORDER BY
    (COALESCE(ts_rank(a.search_vector, plainto_tsquery('english', search_query)), 0) * 0.5) +
    (CASE WHEN query_embedding IS NOT NULL THEN (1 - (a.embedding <=> query_embedding)) * 0.5 ELSE 0 END) DESC
  LIMIT match_count;
END;
$$;

-- Enable Row Level Security
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE rss_feeds ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_queue ENABLE ROW LEVEL SECURITY;

-- Policies for authenticated users
CREATE POLICY "Users can view all articles" ON articles FOR SELECT USING (true);
CREATE POLICY "Users can insert articles" ON articles FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update articles" ON articles FOR UPDATE USING (true);
CREATE POLICY "Users can delete articles" ON articles FOR DELETE USING (true);

CREATE POLICY "Users can view all rss_feeds" ON rss_feeds FOR SELECT USING (true);
CREATE POLICY "Users can manage rss_feeds" ON rss_feeds FOR ALL USING (true);

CREATE POLICY "Users can view all processing_queue" ON processing_queue FOR SELECT USING (true);
CREATE POLICY "Users can manage processing_queue" ON processing_queue FOR ALL USING (true);