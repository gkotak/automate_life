-- Fix embedding dimension from 1536 to 384 for better performance and compatibility
-- Run this in Supabase SQL editor before running migration

-- Drop existing embedding column and recreate with correct dimensions
ALTER TABLE articles DROP COLUMN IF EXISTS embedding;
ALTER TABLE articles ADD COLUMN embedding vector(384);

-- Recreate the embedding index with correct dimensions
DROP INDEX IF EXISTS articles_embedding_idx;
CREATE INDEX articles_embedding_idx ON articles USING ivfflat(embedding vector_cosine_ops);

-- Update the match_articles function for 384 dimensions
CREATE OR REPLACE FUNCTION match_articles(
  query_embedding vector(384),
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

-- Update the hybrid search function for 384 dimensions
CREATE OR REPLACE FUNCTION hybrid_search(
  search_query text,
  query_embedding vector(384) DEFAULT NULL,
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