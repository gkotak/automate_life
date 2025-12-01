-- Fix private_articles embedding dimension to match code (384 instead of 1536)
-- The embedding generation code uses text-embedding-3-small with 384 dimensions

ALTER TABLE private_articles
ALTER COLUMN embedding TYPE vector(384);

COMMENT ON COLUMN private_articles.embedding IS 'OpenAI text-embedding-3-small vector (384 dimensions)';
