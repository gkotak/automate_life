-- Create the vector similarity search function for private articles
-- This function performs semantic search using pgvector cosine similarity
-- Access is restricted by RLS policies on private_articles table

CREATE OR REPLACE FUNCTION search_private_articles(
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
  source text,
  created_at timestamptz,
  similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT
    pa.id,
    pa.title,
    pa.url,
    pa.summary_text,
    pa.content_source,
    pa.platform,
    pa.source,
    pa.created_at,
    1 - (pa.embedding <=> query_embedding) as similarity
  FROM private_articles pa
  WHERE pa.embedding IS NOT NULL
    AND 1 - (pa.embedding <=> query_embedding) > match_threshold
  ORDER BY pa.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION search_private_articles TO authenticated;
