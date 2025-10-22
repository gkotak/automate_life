-- Optimize vector index for semantic search performance
-- This migration improves the IVFFlat index configuration for better query performance
--
-- Background: IVFFlat is an approximate nearest neighbor search algorithm that divides
-- the vector space into clusters (lists). The optimal number of lists depends on dataset size:
-- - Small datasets (<1000 rows): lists = rows / 10
-- - Medium datasets (1000-100k rows): lists = sqrt(rows)
-- - Large datasets (>100k rows): lists = 4 * sqrt(rows)
--
-- Run this in Supabase SQL editor

-- Step 1: Drop existing index to recreate with optimal parameters
DROP INDEX IF EXISTS articles_embedding_idx;

-- Step 2: Create optimized IVFFlat index
-- Using lists=20 for small datasets (good for ~400 articles)
-- As your dataset grows, consider increasing this value:
-- - For ~1000 articles: lists=32
-- - For ~10000 articles: lists=100
-- - For ~100000 articles: lists=400
CREATE INDEX articles_embedding_idx
ON articles
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 20);

-- Step 3: Update index statistics to help query planner
-- This ensures PostgreSQL can make optimal query execution decisions
ANALYZE articles;

-- Step 4: Create a partial index for non-null embeddings only (optimization)
-- This makes the index smaller and faster for queries that filter on embedding existence
DROP INDEX IF EXISTS articles_embedding_nonnull_idx;
CREATE INDEX articles_embedding_nonnull_idx
ON articles
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 20)
WHERE embedding IS NOT NULL;

-- Step 5: Set optimal query parameters for vector search
-- These settings improve the speed/accuracy tradeoff for IVFFlat searches
-- You can adjust these in your queries as needed:
--
-- For fast but less accurate searches:
--   SET ivfflat.probes = 1;
--
-- For balanced performance (recommended):
--   SET ivfflat.probes = 5;
--
-- For slower but more accurate searches:
--   SET ivfflat.probes = 10;
--
-- Default setting (balanced):
ALTER DATABASE postgres SET ivfflat.probes = 5;

-- Verification query - check index is being used:
-- EXPLAIN ANALYZE
-- SELECT id, title, 1 - (embedding <=> '[...]') as similarity
-- FROM articles
-- WHERE embedding IS NOT NULL
-- ORDER BY embedding <=> '[...]'
-- LIMIT 10;

-- Performance tips:
-- 1. The partial index (articles_embedding_nonnull_idx) should be used by queries
--    that filter on "WHERE embedding IS NOT NULL"
-- 2. Monitor query performance and adjust lists parameter as dataset grows
-- 3. Periodically run ANALYZE to update statistics
-- 4. Consider increasing lists parameter when articles table exceeds 1000 rows
