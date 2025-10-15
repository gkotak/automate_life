# Semantic Search Testing Guide

## Quick Test Commands

### 1. Deploy SQL Function
```bash
# Copy the SQL function from supabase/search_articles_function.sql
# Then run it in Supabase SQL Editor at:
# https://supabase.com/dashboard/project/gmwqeqlbfhxffxpsjokf/sql/new
```

### 2. Configure API Key
```bash
cd web-app
# Edit .env.local and add your OpenAI API key
# OPENAI_API_KEY=sk-...
```

### 3. Start Web App
```bash
cd web-app
npm run dev
```

### 4. Test in Browser
- Open http://localhost:3000
- Click "🧠 Semantic (AI)" button
- Try these example queries:
  - "articles about productivity and time management"
  - "what strategies help with remote work?"
  - "content about building better habits"
  - "discussions on technology trends"

## Expected Behavior

### Semantic Search (AI Mode):
- Uses natural language understanding
- Finds articles by meaning/concepts
- Returns results ranked by semantic similarity
- Example: "productivity tips" will find articles about efficiency, time management, etc.

### Keyword Search (Default):
- Traditional text matching
- Exact phrase matching
- Faster but less intelligent
- Example: "productivity tips" only finds articles with those exact words

## Files Created/Modified

### New Files:
- `web-app/src/app/api/search/route.ts` - Semantic search API endpoint
- `supabase/search_articles_function.sql` - Vector similarity search function
- `SEMANTIC_SEARCH_SETUP.md` - Setup instructions
- `SEMANTIC_SEARCH_TESTING.md` - This testing guide

### Modified Files:
- `web-app/src/components/ArticleList.tsx` - Added semantic search UI
- `web-app/.env.local` - Added OPENAI_API_KEY placeholder

## Manual Testing Checklist

- [ ] Deploy SQL function to Supabase
- [ ] Add OpenAI API key to .env.local
- [ ] Start web app (`npm run dev`)
- [ ] Verify keyword search works (default mode)
- [ ] Switch to semantic search mode
- [ ] Try natural language queries
- [ ] Verify results are relevant
- [ ] Check similarity scores (should be > 0.5)
- [ ] Test with empty query (should return all articles)
- [ ] Test error handling (invalid API key, etc.)

## API Testing (Optional)

Test the search API directly with curl:

```bash
# Make sure web app is running first
curl -X POST http://localhost:3000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "articles about artificial intelligence",
    "limit": 5
  }'
```

Expected response:
```json
{
  "results": [
    {
      "id": "uuid",
      "title": "Article Title",
      "url": "https://...",
      "author": "Author Name",
      "published_date": "2025-10-14T...",
      "summary": "Article summary...",
      "similarity": 0.85
    }
  ]
}
```

## Troubleshooting

### No Results
- Check that articles have embeddings: `SELECT COUNT(*) FROM articles WHERE embedding IS NOT NULL;`
- Lower similarity threshold in API route (default 0.5)

### API Errors
- Check browser console for error messages
- Verify OpenAI API key is valid
- Check Supabase function exists

### Performance Issues
- Add vector index if not exists: `CREATE INDEX ON articles USING ivfflat (embedding vector_cosine_ops);`
- Reduce search limit parameter

## Next Steps (Step 3)

After testing works:
- [ ] Add hybrid search (combine semantic + keyword)
- [ ] Add search filters (date range, content type)
- [ ] Show similarity scores in UI
- [ ] Add related articles suggestions
- [ ] Implement search result highlighting
