# Content Sources Migration to Supabase

This directory contains SQL migrations to move content source management from the markdown file (`newsletter_podcast_links.md`) to a Supabase database table.

## Migration Steps

### 1. Run the SQL Migration

Execute the migration SQL in your Supabase SQL editor:

```bash
# Copy the SQL file content
cat create_content_sources_table.sql

# Then paste and run it in Supabase SQL Editor at:
# https://supabase.com/dashboard/project/YOUR_PROJECT/sql
```

Or use the Supabase CLI:

```bash
supabase db push
```

### 2. Verify the Migration

Check that the table was created and initial data loaded:

```sql
SELECT * FROM content_sources;
```

You should see 4 rows:
- Stratechery RSS feed
- Lenny's Newsletter
- Creator Economy blog
- Akash Bajwa blog

### 3. Add New Content Sources

You can now manage sources via SQL or build a UI:

```sql
-- Add a new newsletter
INSERT INTO content_sources (url, source_type, title, notes)
VALUES (
    'https://newsletter.example.com',
    'newsletter',
    'Example Newsletter',
    'Daily tech newsletter'
);

-- Deactivate a source without deleting
UPDATE content_sources
SET is_active = false
WHERE url = 'https://creatoreconomy.so/';

-- Change check frequency
UPDATE content_sources
SET check_frequency = 'hourly'
WHERE url LIKE '%stratechery%';
```

## Schema

```sql
CREATE TABLE content_sources (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,              -- The URL to check
    source_type TEXT NOT NULL,              -- 'rss_feed', 'newsletter', 'podcast', 'blog'
    title TEXT,                             -- Display name
    notes TEXT,                             -- Special instructions/auth notes
    is_active BOOLEAN DEFAULT true,         -- Enable/disable checking
    check_frequency TEXT DEFAULT 'daily',   -- 'hourly', 'daily', 'weekly'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Code Changes

The `post_checker.py` has been updated to:

1. **Try Supabase first**: Read from `content_sources` table
2. **Fallback to markdown**: If Supabase unavailable, read from `newsletter_podcast_links.md`
3. **Graceful degradation**: System continues working even if Supabase is down

## Benefits

### Before (Markdown File)
- ❌ Manual file editing required
- ❌ No versioning or history
- ❌ Can't disable sources without deleting
- ❌ No metadata (source type, check frequency)
- ❌ Hard to manage programmatically

### After (Supabase Table)
- ✅ Easy to add/edit via SQL or UI
- ✅ Full audit trail (created_at, updated_at)
- ✅ Soft delete with is_active flag
- ✅ Rich metadata and categorization
- ✅ Programmatic access via API
- ✅ Can build admin UI later
- ✅ Query by source type, filter inactive sources

## Future Enhancements

Once the table is populated, you can:

1. **Build an admin UI** to manage sources without editing SQL
2. **Add authentication metadata** (API keys, session tokens) securely
3. **Track check history** (last_checked_at, last_success_at)
4. **Add rate limiting** per source
5. **Implement priority levels** for important sources
6. **Add source health monitoring** (consecutive failures, uptime)

## Rollback

If you need to roll back to the markdown file:

1. The code already has fallback logic built-in
2. Simply remove Supabase credentials from environment
3. Or set `is_active = false` for all sources to effectively disable

```sql
-- Emergency disable all Supabase sources
UPDATE content_sources SET is_active = false;
```

The system will automatically fall back to reading from `newsletter_podcast_links.md`.
