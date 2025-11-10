# Podcast & Post Checker Improvements

## Summary

Enhanced the `post_checker` service to support podcast RSS feeds, PocketCasts channels, and YouTube URL discovery for all content types (not just podcasts).

## Changes Made

### 1. Podcast RSS Feed Detection (`post_checker.py`)

**Added podcast-specific RSS parsing:**
- Detects audio enclosures in RSS feeds (`<enclosure type="audio/...">`)
- Extracts podcast metadata:
  - Audio file URL (direct MP3/audio link)
  - Episode duration (from `itunes:duration`)
  - Channel title and URL from feed metadata
- Sets `content_type` to `'podcast_episode'` vs `'article'`
- Sets `platform` to `'podcast_rss'` for podcast feeds

**Supported podcast RSS feeds:**
- Megaphone feeds (e.g., `https://feeds.megaphone.fm/...`)
- Apple Podcasts RSS
- Any standard podcast RSS feed with audio enclosures

### 2. PocketCasts Channel Scraping (`post_checker.py`)

**Added `_extract_episodes_from_pocketcasts()` method:**
- Scrapes PocketCasts podcast pages (`https://pocketcasts.com/podcast/...`)
- Extracts episodes from embedded JSON data
- Captures episode metadata:
  - Episode title, UUID, slug
  - Published date
  - Duration
  - Episode URL

**Usage:**
```python
# Add PocketCasts channel URL to content_sources table
url = "https://pocketcasts.com/podcast/exchanges/febb7320-62c0-0132-d60f-5f4c86fd3263"
```

### 3. YouTube URL Discovery for All Content (`youtube_discovery.py`)

**Created shared `YouTubeDiscoveryService` module:**
- Used by both `post_checker` and `podcast_checker`
- Discovers YouTube URLs from any web page (articles, podcast episodes)
- Three-strategy approach:
  1. **HTML Links**: Searches `<a href="">` tags for YouTube URLs
  2. **Embedded iframes**: Extracts from `<iframe src="">` embeds
  3. **Text Patterns**: Regex matching in page content

**Integration in `post_checker`:**
- Added `_discover_youtube_url_for_post()` method
- Automatically runs for ALL content (podcasts + articles)
- Checks `known_channels` table first (if exists)
- Falls back to web scraping

**Use cases:**
- Substack articles with embedded YouTube videos
- Podcast episodes with video versions
- Newsletter posts linking to YouTube content

### 4. Renamed `known_podcasts` → `known_channels`

**Database changes:**
- Table: `known_podcasts` → `known_channels`
- Column: `podcast_title` → `channel_name`
- Updated indexes, functions, triggers, policies

**Purpose:**
- More generic naming for all content types
- Supports podcasts, newsletters, blogs, etc.
- Single source of truth for YouTube channel mappings

**Files updated:**
- `supabase/migrations/016_rename_known_podcasts_to_known_channels.sql`
- `supabase/schemas/known_channels.sql` (renamed from `known_podcasts.sql`)
- `podcast_checker.py` (uses `known_channels` table)
- `post_checker.py` (uses `known_channels` table)

### 5. Enhanced `content_queue` Schema

**New fields saved by `post_checker`:**
- `audio_url`: Direct audio file URL (from podcast RSS)
- `video_url`: YouTube URL (from discovery service)
- `duration_seconds`: Episode duration
- `content_type`: `'podcast_episode'` or `'article'`

## Testing

### Test Cases

#### 1. Podcast RSS Feed (Megaphone)
```bash
# Add to content_sources table with user_id
{
  "url": "https://feeds.megaphone.fm/WMHY7703459968",
  "user_id": "<your-user-id>",
  "is_active": true
}

# Run post checker
python3 scripts/check_posts.py
```

**Expected Result:**
- Detects as podcast RSS feed
- Extracts audio URLs from enclosures
- Saves episodes to `content_queue` as `podcast_episode`
- Includes duration and channel metadata

#### 2. PocketCasts Channel URL
```bash
# Add to content_sources table
{
  "url": "https://pocketcasts.com/podcast/exchanges/febb7320-62c0-0132-d60f-5f4c86fd3263",
  "user_id": "<your-user-id>",
  "is_active": true
}

# Run post checker
python3 scripts/check_posts.py
```

**Expected Result:**
- Scrapes PocketCasts page JSON
- Extracts episode list
- Saves to `content_queue` as `podcast_episode`

#### 3. Substack with YouTube Video
```bash
# Add Substack URL to content_sources
{
  "url": "https://stratechery.com",
  "user_id": "<your-user-id>",
  "is_active": true
}

# Run post checker
python3 scripts/check_posts.py
```

**Expected Result:**
- Finds articles from Substack
- Scrapes each article page for YouTube links
- Saves `video_url` if YouTube content found

## Architecture

### Before
```
post_checker → Only handles articles (no podcasts)
               No YouTube discovery for articles

podcast_checker → Handles podcasts via PocketCasts history only
                  YouTube discovery only for podcasts
```

### After
```
post_checker → Handles articles AND podcasts
            → RSS feeds (articles + podcasts)
            → PocketCasts channels
            → YouTube discovery for ALL content
            → Uses shared youtube_discovery module

podcast_checker → Handles PocketCasts history (authenticated)
               → YouTube discovery for podcasts
               → Uses known_channels table
```

## Benefits

1. **Unified Content Discovery**: One service (`post_checker`) can handle:
   - Newsletter/blog articles
   - Podcast RSS feeds
   - PocketCasts channel pages

2. **YouTube for Everything**: YouTube URL discovery works for:
   - Podcast episodes (video podcasts)
   - Articles (embedded YouTube videos)
   - Any content with YouTube links

3. **Flexible Sources**: Users can add:
   - RSS feeds (podcasts or articles)
   - PocketCasts channel URLs (without authentication)
   - Regular web pages (Substack, Medium, etc.)

4. **Better Metadata**: Captures:
   - Direct audio URLs (for podcast RSS)
   - YouTube URLs (for video content)
   - Duration, published dates
   - Channel information

## Migration Notes

### Database Migration

Run the migration to rename the table:

```bash
# Apply migration
psql -h <supabase-host> -U postgres -d postgres -f supabase/migrations/016_rename_known_podcasts_to_known_channels.sql
```

### Known Channels Table

Populate with your favorite channels:

```sql
-- Example: Add podcast with YouTube channel
INSERT INTO known_channels (channel_name, youtube_url, notes)
VALUES (
  'Fareed Zakaria GPS',
  'https://www.youtube.com/@FareedZakariaGPS',
  'CNN podcast with video versions on YouTube'
);

-- Example: Add newsletter with occasional YouTube videos
INSERT INTO known_channels (channel_name, youtube_url, notes)
VALUES (
  'Stratechery',
  'https://www.youtube.com/@Stratechery',
  'Tech newsletter, occasional video interviews'
);
```

## Files Changed

### Modified
- `programs/content_checker_backend/app/services/post_checker.py` - Main changes
- `programs/content_checker_backend/app/services/podcast_checker.py` - Use known_channels table

### Created
- `programs/content_checker_backend/core/youtube_discovery.py` - Shared YouTube discovery service
- `supabase/migrations/016_rename_known_podcasts_to_known_channels.sql` - Database migration

### Renamed
- `supabase/schemas/known_podcasts.sql` → `supabase/schemas/known_channels.sql`

## Future Enhancements

1. **Automatic YouTube Matching**: For podcasts without YouTube URLs, use fuzzy matching (like podcast_checker does)
2. **Video Frame Extraction**: Extract key frames from discovered YouTube videos
3. **Audio Transcription**: Automatically transcribe podcast audio URLs
4. **Channel Auto-Discovery**: Automatically populate known_channels from discovered patterns
