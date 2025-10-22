# Vector Index Optimization Guide

## Overview

This guide explains the vector index optimization for semantic search in the article summarizer. The optimization improves query performance using pgvector's IVFFlat (Inverted File with Flat compression) index.

## Current Performance

Based on testing with 8 articles:
- **Vector search time**: 45-62ms (Excellent)
- **Embedding generation**: 330-1240ms (depends on query length)
- **Total query time**: ~400-1300ms

## What's Been Done

### 1. Index Configuration

The existing index uses IVFFlat, which is an approximate nearest neighbor (ANN) algorithm that:
- Divides the vector space into clusters (called "lists")
- Performs fast approximate searches instead of exact brute-force searches
- Provides excellent performance for large datasets

### 2. Optimization Migration

**File**: `optimize_vector_index.sql`

Key improvements:
- **Optimized lists parameter**: Set to 20 for small datasets (~400 articles)
- **Partial index**: Created a specialized index for non-null embeddings
- **Query planner statistics**: Updated with ANALYZE command
- **Probe configuration**: Set ivfflat.probes = 5 for balanced performance

### 3. Performance Testing

**File**: `test_vector_search_performance.py`

Test script that:
- Generates embeddings for test queries
- Measures search performance
- Provides optimization recommendations

## How to Apply the Optimization

### Step 1: Run the Migration

1. Open Supabase SQL Editor
2. Copy the contents of `optimize_vector_index.sql`
3. Execute the migration

```sql
-- Or run directly if you have psql access
psql -h <supabase-host> -U postgres -d postgres -f optimize_vector_index.sql
```

### Step 2: Test Performance

```bash
cd programs/article_summarizer
python3 migration/test_vector_search_performance.py
```

### Step 3: Monitor and Adjust

As your dataset grows, adjust the `lists` parameter:

| Dataset Size | Recommended Lists | Command |
|--------------|------------------|---------|
| < 400 articles | 20 | `WITH (lists = 20)` |
| ~1,000 articles | 32 | `WITH (lists = 32)` |
| ~10,000 articles | 100 | `WITH (lists = 100)` |
| ~100,000 articles | 400 | `WITH (lists = 400)` |

## Understanding IVFFlat Parameters

### Lists Parameter

The `lists` parameter determines how many clusters the vector space is divided into:
- **Too few lists**: Slower searches (more vectors to check per cluster)
- **Too many lists**: Less accurate results (vectors may be clustered poorly)
- **Optimal**: Balance between speed and accuracy

**Formula**:
- Small datasets (<1000): `lists = rows / 10`
- Medium datasets (1000-100k): `lists = sqrt(rows)`
- Large datasets (>100k): `lists = 4 * sqrt(rows)`

### Probes Parameter

The `probes` parameter controls how many clusters are searched:
- **probes = 1**: Fastest, least accurate
- **probes = 5**: Balanced (recommended)
- **probes = 10**: Slower, most accurate

Set per-session in your queries:
```sql
SET ivfflat.probes = 5;
```

## Performance Benchmarks

### Current (8 articles)
- Vector search: **50ms average** ✅ Excellent

### Expected (1000 articles, optimized)
- Vector search: **100-200ms** ✅ Good
- Without index: **5-10 seconds** ❌ Poor

### Expected (10,000 articles, optimized)
- Vector search: **200-500ms** ✅ Acceptable
- Without index: **50-100 seconds** ❌ Very Poor

## Monitoring Performance

### Check if Index is Being Used

```sql
EXPLAIN ANALYZE
SELECT id, title, 1 - (embedding <=> '[your_embedding_vector]') as similarity
FROM articles
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[your_embedding_vector]'
LIMIT 10;
```

Look for:
- `Index Scan using articles_embedding_nonnull_idx` ✅ Good
- `Seq Scan on articles` ❌ Index not being used

### Update Statistics Regularly

After adding many new articles:
```sql
ANALYZE articles;
```

## Troubleshooting

### Slow Queries

**Problem**: Search takes > 500ms

**Solutions**:
1. Increase lists parameter (recreate index)
2. Decrease probes parameter (faster but less accurate)
3. Ensure index is being used (check EXPLAIN ANALYZE)
4. Run ANALYZE to update statistics

### Low Accuracy

**Problem**: Search returns irrelevant results

**Solutions**:
1. Increase probes parameter
2. Decrease lists parameter (recreate index)
3. Check embedding generation quality
4. Verify match_threshold in search function

### Index Not Being Used

**Problem**: EXPLAIN shows sequential scan instead of index scan

**Solutions**:
1. Ensure embedding column is NOT NULL in WHERE clause
2. Run ANALYZE to update statistics
3. Check PostgreSQL configuration (enable_seqscan, random_page_cost)
4. Verify index exists: `\di articles_embedding*`

## Best Practices

1. **Periodic Maintenance**
   - Run `ANALYZE articles` weekly or after bulk inserts
   - Monitor query performance metrics
   - Adjust index parameters as dataset grows

2. **Query Optimization**
   - Always include `WHERE embedding IS NOT NULL`
   - Use appropriate match_threshold (0.3-0.7)
   - Limit results to reasonable count (10-50)

3. **Scaling Strategy**
   - Start with lists=20 for small datasets
   - Monitor search time as data grows
   - Recreate index with higher lists when search time exceeds 200ms
   - Consider HNSW index for very large datasets (>100k articles)

## Alternative: HNSW Index

For very large datasets (>100k articles), consider HNSW (Hierarchical Navigable Small World):

```sql
CREATE INDEX articles_embedding_hnsw_idx
ON articles
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**HNSW Advantages**:
- Better accuracy for large datasets
- More consistent query times
- No need to tune lists parameter

**HNSW Disadvantages**:
- Slower index creation
- Larger index size
- Higher memory usage

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [PostgreSQL Index Tuning](https://www.postgresql.org/docs/current/indexes.html)

## Files in This Migration

1. `optimize_vector_index.sql` - Index optimization migration
2. `test_vector_search_performance.py` - Performance testing script
3. `VECTOR_INDEX_OPTIMIZATION.md` - This documentation
