# content_queue Table Design Documentation

## Overview

The `content_queue` table is a central discovery queue that aggregates content from **multiple sources**:
1. **RSS Feed Checking** - Posts/episodes discovered from subscribed RSS feeds
2. **PocketCasts Listening History** - Episodes discovered from your listening history

This multi-source design requires certain fields to be duplicated (denormalized) rather than normalized via foreign keys.

---

## Why Denormalization Is Necessary

### Problem: Not All Content Has a Source
- **RSS entries**: Have a corresponding entry in `content_sources` table
- **PocketCasts entries**: Do NOT have a corresponding entry in `content_sources` table
  - They're discovered from listening history, not from subscribed feeds
  - No RSS feed URL, no source to reference

### Solution: Duplicate Metadata
Store channel information (`channel_title`, `channel_url`, `source_feed`) directly in `content_queue` rather than referencing a source, because:
- We can't use a foreign key (some entries have no source)
- Different discovery mechanisms provide different metadata
- We need to preserve the discovery context independently

---

## Field Reference

### Core Fields (Common to All Sources)

| Field | Type | Description |
|-------|------|-------------|
| `url` | String | The actual article/episode URL to process |
| `title` | String | Episode/article title |
| `user_id` | UUID | User who discovered this content |
| `organization_id` | UUID | Organization for multi-tenancy |
| `found_at` | Timestamp | When this content was discovered |
| `published_date` | Timestamp | When the content was originally published |
| `status` | String | Processing status: 'discovered', 'processing', 'completed', 'failed' |

### Discovery Context Fields (Why These Exist)

| Field | RSS Flow | PocketCasts Flow | Why Both? |
|-------|----------|------------------|-----------|
| `content_type` | 'podcast/audio' or 'article' (dynamic based on URL) | 'podcast_episode' (hardcoded) | Different detection logic per source |
| `source` | 'rss_feed' | 'podcast_history' | Identifies which discovery mechanism found this |
| `platform` | 'podcast_rss' or 'rss_feed' | 'pocketcasts' | More granular platform tracking |
| `channel_title` | From RSS feed metadata | From PocketCasts API | Different data sources, can't normalize |
| `channel_url` | Podcast/newsletter homepage | PocketCasts podcast page URL | Different canonical URLs per platform |
| `source_feed` | RSS feed URL | `NULL` | Only RSS has a feed; PocketCasts doesn't |

### Media-Specific Fields

| Field | Description |
|-------|-------------|
| `audio_url` | Direct audio file URL (from RSS enclosure or PocketCasts) |
| `duration_seconds` | Episode/audio duration in seconds |

### PocketCasts-Specific Fields

| Field | Description |
|-------|-------------|
| `podcast_uuid` | PocketCasts podcast identifier |
| `episode_uuid` | PocketCasts episode identifier |
| `played_up_to` | Playback position (seconds) |
| `progress_percent` | Playback progress (0-100) |
| `playing_status` | Playback state from PocketCasts |

---

## Discovery Flow Comparison

### RSS Feed Discovery Flow

```
User adds source → content_sources table
                ↓
Check for new posts → Parse RSS feed
                ↓
Extract posts → content_queue
                ↓
Fields populated:
- content_type: Determined by URL extension (.mp3 → 'podcast/audio')
- source: 'rss_feed'
- platform: 'podcast_rss' or 'rss_feed' (from source_type)
- channel_title: From feed.feed.title
- channel_url: From feed.feed.link (podcast homepage)
- source_feed: The RSS feed URL (from content_sources.url)
```

### PocketCasts History Flow

```
Check listening history → PocketCasts API
                       ↓
Extract episodes → content_queue
                       ↓
NO entry in content_sources!
                       ↓
Fields populated:
- content_type: 'podcast_episode' (hardcoded)
- source: 'podcast_history'
- platform: 'pocketcasts'
- channel_title: From PocketCasts API or scraped
- channel_url: pocketcasts.com/podcast/{uuid}
- source_feed: NULL (no RSS feed involved)
```

---

## Example Records

### RSS-Discovered Podcast Episode

```json
{
  "url": "https://traffic.libsyn.com/.../episode.mp3?dest-id=240976",
  "title": "20VC: The Future of AI | Episode 1234",
  "content_type": "podcast/audio",
  "source": "rss_feed",
  "platform": "podcast_rss",
  "channel_title": "The Twenty Minute VC (20VC)",
  "channel_url": "https://www.thetwentyminutevc.com/",
  "source_feed": "https://feeds.simplecast.com/6TLpeXeh",
  "audio_url": "https://traffic.libsyn.com/.../episode.mp3?dest-id=240976",
  "podcast_uuid": null,
  "episode_uuid": null
}
```

### PocketCasts-Discovered Episode

```json
{
  "url": "https://chrt.fm/track/.../episode.mp3",
  "title": "20VC: The Future of AI | Episode 1234",
  "content_type": "podcast_episode",
  "source": "podcast_history",
  "platform": "pocketcasts",
  "channel_title": "The Twenty Minute VC (20VC)",
  "channel_url": "https://pocketcasts.com/podcast/abc123",
  "source_feed": null,
  "audio_url": null,
  "podcast_uuid": "abc123",
  "episode_uuid": "xyz789",
  "played_up_to": 1234,
  "progress_percent": 45,
  "playing_status": "in_progress"
}
```

### RSS-Discovered Newsletter Article

```json
{
  "url": "https://example.com/article-slug",
  "title": "My Latest Blog Post",
  "content_type": "article",
  "source": "rss_feed",
  "platform": "rss_feed",
  "channel_title": "John's Newsletter",
  "channel_url": "https://example.com/",
  "source_feed": "https://example.com/feed.xml",
  "audio_url": null,
  "podcast_uuid": null,
  "episode_uuid": null
}
```

---

## Key Design Decisions

### 1. Why Not Use a Foreign Key to content_sources?

**Problem**: Not all content in `content_queue` comes from `content_sources`
- RSS entries → Have a source
- PocketCasts entries → No source (discovered from listening history)

**Solution**: Store metadata directly in `content_queue` (denormalized)

### 2. Why Both `source` and `platform`?

**source**: High-level discovery mechanism
- `'rss_feed'` - Any RSS-based discovery
- `'podcast_history'` - PocketCasts listening history

**platform**: More granular platform tracking
- `'podcast_rss'` - RSS feed explicitly added as podcast
- `'rss_feed'` - RSS feed added as newsletter
- `'pocketcasts'` - PocketCasts listening history
- Future: `'spotify_history'`, `'youtube_subscriptions'`, etc.

### 3. Why Both `content_type` and `platform`?

**content_type**: What the URL actually points to
- Determined by inspecting the URL
- `'podcast/audio'` - URL ends with .mp3, .m4a, etc.
- `'article'` - URL points to a webpage
- `'podcast_episode'` - PocketCasts (hardcoded)

**platform**: How we discovered it
- Multiple platforms can provide the same content type
- Needed for metrics and debugging

### 4. Why is `source_feed` Nullable?

**RSS entries**: Contains the RSS feed URL
**PocketCasts entries**: `NULL` (no RSS feed involved)

This field is nullable by design to support multiple discovery mechanisms.

---

## Implementation Files

- **RSS Discovery**: `programs/content_checker_backend/app/services/post_checker.py`
  - `_save_post_to_queue()` method (lines ~690-720)

- **PocketCasts Discovery**: `programs/content_checker_backend/app/services/podcast_history_checker.py`
  - `_save_episode_to_queue()` method (lines ~460-490)

---

## Future Extensibility

This design supports adding new discovery sources without schema changes:

- Spotify listening history → `source: 'spotify_history'`, `platform: 'spotify'`
- YouTube subscriptions → `source: 'youtube_subscriptions'`, `platform: 'youtube'`
- Manual user submissions → `source: 'manual'`, `platform: 'web_ui'`

Each new source can provide its own metadata while sharing the common `content_queue` schema.
