# Schema Cleanup Summary

## Changes Made

Removed two unused columns from `content_queue` table:
- `channel_url` - Podcast/newsletter homepage URLs (not displayed in UI)
- `source_feed` - RSS feed URLs (redundant with `content_sources.url`)

## What We Kept

| Column | Purpose | Why Necessary |
|--------|---------|---------------|
| `url` | Episode/article URL | Required for content processing |
| `channel_title` | Podcast/newsletter name | Displayed in UI |
| `source` | Discovery mechanism | Distinguishes 'rss_feed' vs 'podcast_history' |
| `platform` | Discovery platform | More granular tracking ('podcast_rss', 'pocketcasts', etc.) |
| `content_type` | Content format | 'podcast/audio', 'article', or 'podcast_episode' |

## Files Modified

### Database
- `supabase/migrations/1005_drop_unused_url_columns.sql` - Migration to drop columns

### Backend
- `programs/content_checker_backend/app/services/post_checker.py` - Removed channel_url and source_feed population
- `programs/content_checker_backend/app/services/podcast_history_checker.py` - Removed channel_url and source_feed population

### Frontend
- `web-apps/article-summarizer/src/lib/api-client.ts` - Removed from Post interface
- `web-apps/article-summarizer/src/app/new/posts/page.tsx` - Removed from Post interface and mapping

## To Apply Changes

1. **Run the database migration:**
   ```bash
   # Using Supabase CLI
   supabase db push

   # OR manually via psql
   psql $DATABASE_URL -f supabase/migrations/1005_drop_unused_url_columns.sql
   ```

2. **Restart backend services:**
   ```bash
   # Content checker backend
   cd programs/content_checker_backend
   uvicorn app.main:app --reload --port 8001
   ```

3. **Rebuild frontend:**
   ```bash
   cd web-apps/article-summarizer
   npm run dev
   ```

## Rollback Plan

If something breaks, the migration includes rollback instructions:
```sql
ALTER TABLE content_queue ADD COLUMN channel_url TEXT;
ALTER TABLE content_queue ADD COLUMN source_feed TEXT;
```

Then revert the code changes from this commit.

## Impact Assessment

**Low risk** because:
- These fields were never displayed in the UI
- No backend logic depended on them
- Data is still available via joins if needed later
- Reduces storage and improves query performance

## Why This Cleanup?

Original design duplicated metadata for multi-source support, but analysis showed:
- `channel_url`: Nice-to-have but unused (homepage URLs)
- `source_feed`: Redundant (already in `content_sources.url` for RSS entries, NULL for PocketCasts)
- Both increased storage without providing value

The simplified schema keeps only what's actually used.
