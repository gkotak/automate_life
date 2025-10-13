# Fix Setup Guide - Restoring Rich Summaries

## Problem Summary

The refactoring moved from storing rich HTML summaries to structured JSON data, but:
1. The database schema was missing the structured JSON columns
2. The AI prompt wasn't generating structured data in the correct format
3. The article_summarizer.py wasn't saving data to Supabase

## Solution Steps

### 1. Update Database Schema

Run this SQL in your Supabase SQL Editor:

```sql
-- Add structured JSON fields for rich article data
ALTER TABLE articles ADD COLUMN IF NOT EXISTS key_insights JSONB DEFAULT '[]';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS main_points JSONB DEFAULT '[]';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS quotes JSONB DEFAULT '[]';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS takeaways TEXT[] DEFAULT '{}';

-- Add metadata columns
ALTER TABLE articles ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS word_count INTEGER;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS topics TEXT[] DEFAULT '{}';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS sentiment TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS complexity_level TEXT;

-- Create indexes
CREATE INDEX IF NOT EXISTS articles_key_insights_idx ON articles USING gin(key_insights);
CREATE INDEX IF NOT EXISTS articles_main_points_idx ON articles USING gin(main_points);
CREATE INDEX IF NOT EXISTS articles_quotes_idx ON articles USING gin(quotes);
CREATE INDEX IF NOT EXISTS articles_topics_idx ON articles USING gin(topics);
```

Or simply run the provided migration file:
```bash
# Copy the content of migration/add_structured_fields.sql and run it in Supabase SQL Editor
```

### 2. Install Python Dependencies

```bash
cd programs/article_summarizer/scripts
pip install -r requirements.txt
```

This will install the `supabase` Python client library.

### 3. Set Up Environment Variables

Create or update your `.env` file in the `programs/article_summarizer` directory:

```bash
# Supabase credentials
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key  # Use the service_role key, not anon key

# OpenAI API (if using transcription)
OPENAI_API_KEY=your-openai-key

# Claude API (handled by claude CLI automatically)
```

**Important:**
- Use the `service_role` key (from Supabase Settings > API), NOT the `anon` key
- The service_role key has full access and bypasses Row Level Security (RLS)

### 4. Test the Fix

Process a test article to verify everything works:

```bash
cd programs/article_summarizer
python3 scripts/article_summarizer.py "https://www.lennysnewsletter.com/p/why-ai-evals-are-the-hottest-new-skill"
```

Expected output:
```
1. Extracting metadata...
   Title: Why AI evals are the hottest new skill...
2. Analyzing content with AI...
   🤖 [CLAUDE API] Sending prompt...
3. Generating HTML...
4. Saving to Supabase database...
   ✅ Saved to database (article ID: 123)
5. Updating index...
6. Committing to git...
✅ Processing complete
```

### 5. Verify in Web App

1. Start the Next.js dev server:
```bash
cd programs/article_summarizer/web-app
npm run dev
```

2. Open http://localhost:3000

3. You should see:
   - Article with proper title and metadata
   - **Article Details** section (metadata box)
   - **🔍 Key Insights** section with formatted insights
   - **📋 Main Points** section with proper styling
   - **💬 Quotes** section with speakers and context
   - **✨ Takeaways** section
   - Embedded video player (if applicable)

## What Was Fixed

### 1. Database Schema (`migration/add_structured_fields.sql`)
- Added JSONB columns for `key_insights`, `main_points`, `quotes`
- Added array columns for `takeaways` and `topics`
- Added metadata columns for `duration_minutes`, `word_count`, `sentiment`, `complexity_level`
- Created proper indexes for performance

### 2. AI Prompt (`scripts/article_summarizer.py`)
Updated the Claude API prompt to generate structured data:
```json
{
  "summary": "HTML formatted content",
  "key_insights": [{"insight": "...", "timestamp_seconds": 300, "time_formatted": "5:00"}],
  "main_points": [{"point": "...", "details": "..."}],
  "quotes": [{"quote": "...", "speaker": "...", "timestamp_seconds": 120}],
  "takeaways": ["...", "...", "..."],
  "duration_minutes": 45,
  "word_count": 5000,
  "topics": ["AI", "Product"],
  "sentiment": "positive",
  "complexity_level": "intermediate"
}
```

### 3. Database Integration (`scripts/article_summarizer.py`)
- Added Supabase client initialization
- Created `_save_to_database()` method to insert/update articles
- Uses `upsert` with `on_conflict='url'` to avoid duplicates
- Gracefully handles missing Supabase credentials

## Troubleshooting

### Issue: "Supabase not initialized"
**Solution:** Check your `.env` file has `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`

### Issue: "Database save failed: permission denied"
**Solution:** Make sure you're using the `service_role` key, not the `anon` key

### Issue: Web app still shows empty data
**Solution:**
1. Verify the article exists in Supabase (check the `articles` table)
2. Check browser console for errors
3. Verify the article has the structured fields populated
4. Try deleting and re-processing the article

### Issue: AI generates plain text instead of structured JSON
**Solution:**
1. Check the Claude API response in `logs/debug_response.txt`
2. The AI may need a follow-up prompt refinement if it's not following the format
3. Try with a different article (some articles work better than others)

## Migration Notes

If you have existing articles in the database, you may want to reprocess them to get the structured data:

```bash
# List existing articles
python3 scripts/post_manager.py list --status=completed

# Reprocess specific articles
python3 scripts/article_summarizer.py "URL"
```

The system will update existing articles (by URL) rather than creating duplicates.

## Next Steps

1. Run the SQL migration in Supabase
2. Install dependencies: `pip install -r scripts/requirements.txt`
3. Set up `.env` with Supabase credentials
4. Test with one article
5. Verify in web app
6. Process more articles as needed
