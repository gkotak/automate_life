-- Create the vector similarity search function for articles
-- This function performs semantic search using pgvector cosine similarity

CREATE OR REPLACE FUNCTION search_articles(
  query_embedding vector(384),
  match_threshold float DEFAULT 0.5,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id integer,
  title text,
  url text,
  summary_text text,
  content_source text,
  platform text,
  created_at timestamp,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.id,
    a.title,
    a.url,
    a.summary_text,
    a.content_source,
    a.platform,
    a.created_at,
    1 - (a.embedding <=> query_embedding) as similarity
  FROM articles a
  WHERE a.embedding IS NOT NULL
    AND 1 - (a.embedding <=> query_embedding) > match_threshold
  ORDER BY a.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
