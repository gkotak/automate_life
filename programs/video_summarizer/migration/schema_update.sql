-- Enhanced schema for comprehensive search functionality
-- Run this to update your existing articles table

-- Add new columns for different content types
ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary_text TEXT; -- Plain text from Claude summary
ALTER TABLE articles ADD COLUMN IF NOT EXISTS transcript_text TEXT; -- Video/audio transcript
ALTER TABLE articles ADD COLUMN IF NOT EXISTS original_article_text TEXT; -- Full article content
ALTER TABLE articles ADD COLUMN IF NOT EXISTS content_source TEXT; -- 'video', 'audio', 'article', 'mixed'

-- Update the search vector function to include all text sources
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english',
    COALESCE(NEW.title, '') || ' ' ||
    COALESCE(NEW.summary_text, '') || ' ' ||
    COALESCE(NEW.transcript_text, '') || ' ' ||
    COALESCE(NEW.original_article_text, '')
  );
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Enhanced hybrid search function
CREATE OR REPLACE FUNCTION hybrid_search(
  search_query text,
  query_embedding vector(1536) DEFAULT NULL,
  content_filter text DEFAULT NULL, -- 'summary', 'transcript', 'article', 'all'
  match_count int DEFAULT 20
)
RETURNS TABLE (
  id int,
  title text,
  url text,
  summary_html text,
  content_source text,
  created_at timestamp,
  search_rank float,
  semantic_similarity float,
  match_type text -- 'summary', 'transcript', 'article'
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
    a.content_source,
    a.created_at,
    GREATEST(
      CASE WHEN content_filter IN ('summary', 'all') OR content_filter IS NULL
           THEN ts_rank(to_tsvector('english', COALESCE(a.summary_text, '')), plainto_tsquery('english', search_query))
           ELSE 0 END,
      CASE WHEN content_filter IN ('transcript', 'all') OR content_filter IS NULL
           THEN ts_rank(to_tsvector('english', COALESCE(a.transcript_text, '')), plainto_tsquery('english', search_query))
           ELSE 0 END,
      CASE WHEN content_filter IN ('article', 'all') OR content_filter IS NULL
           THEN ts_rank(to_tsvector('english', COALESCE(a.original_article_text, '')), plainto_tsquery('english', search_query))
           ELSE 0 END
    ) as search_rank,
    CASE
      WHEN query_embedding IS NOT NULL THEN 1 - (a.embedding <=> query_embedding)
      ELSE 0
    END as semantic_similarity,
    CASE
      WHEN ts_rank(to_tsvector('english', COALESCE(a.summary_text, '')), plainto_tsquery('english', search_query)) > 0 THEN 'summary'
      WHEN ts_rank(to_tsvector('english', COALESCE(a.transcript_text, '')), plainto_tsquery('english', search_query)) > 0 THEN 'transcript'
      WHEN ts_rank(to_tsvector('english', COALESCE(a.original_article_text, '')), plainto_tsquery('english', search_query)) > 0 THEN 'article'
      ELSE 'semantic'
    END as match_type
  FROM articles a
  WHERE
    (search_query = '' OR a.search_vector @@ plainto_tsquery('english', search_query))
    OR
    (query_embedding IS NOT NULL AND 1 - (a.embedding <=> query_embedding) > 0.7)
  ORDER BY
    (GREATEST(
      CASE WHEN content_filter IN ('summary', 'all') OR content_filter IS NULL
           THEN ts_rank(to_tsvector('english', COALESCE(a.summary_text, '')), plainto_tsquery('english', search_query))
           ELSE 0 END,
      CASE WHEN content_filter IN ('transcript', 'all') OR content_filter IS NULL
           THEN ts_rank(to_tsvector('english', COALESCE(a.transcript_text, '')), plainto_tsquery('english', search_query))
           ELSE 0 END,
      CASE WHEN content_filter IN ('article', 'all') OR content_filter IS NULL
           THEN ts_rank(to_tsvector('english', COALESCE(a.original_article_text, '')), plainto_tsquery('english', search_query))
           ELSE 0 END
    ) * 0.5) +
    (CASE WHEN query_embedding IS NOT NULL THEN (1 - (a.embedding <=> query_embedding)) * 0.5 ELSE 0 END) DESC
  LIMIT match_count;
END;
$$;