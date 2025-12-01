# Article Reprocessing Feature Plan

**Created**: 2024-12-01
**Updated**: 2024-12-01
**Status**: Phase 1 Complete ✅ | Phase 2 Planned

## Overview

This document outlines the plan for implementing partial article reprocessing, which allows regenerating specific parts of an article (AI summary, themed insights, video frames, embeddings) without re-downloading content.

## Background

### Current Architecture Issues

1. **Duplicate code paths**: The CLI `process_article()` method and API `/process-direct` route have diverged
2. **API route is source of truth**: Has privacy auto-detection, duplicate handling, demo video frames, library management
3. **CLI method is outdated**: Missing features that were added to API route
4. **No partial reprocessing**: Must reprocess entire article even for small changes

### Decision: Low-Risk Approach

Instead of a risky refactor, we're taking a phased approach:
- Keep API route as-is (it works)
- Deprecate CLI `process_article()` method
- Add CLI wrapper that calls the API
- Build new reprocessing feature separately

---

## Phase 1: Core Reprocessing (Current)

### 1.1 Deprecate CLI `process_article()` Method

**File**: `programs/article_summarizer_backend/app/services/article_processor.py`

Add deprecation warning to the method at line 122:

```python
async def process_article(self, url: str, user_id: Optional[str] = None, is_private: bool = False) -> str:
    """
    DEPRECATED: Use the /api/article/process-direct endpoint instead.

    This method is kept for backwards compatibility but lacks features:
    - No privacy auto-detection
    - No duplicate handling
    - No demo video frame support
    - No library management

    For CLI usage, use scripts/process_article_cli.py which calls the API.
    """
    import warnings
    warnings.warn(
        "process_article() is deprecated. Use /api/article/process-direct endpoint instead.",
        DeprecationWarning
    )
    # ... existing implementation continues
```

### 1.2 Create CLI Wrapper Script

**New File**: `programs/article_summarizer_backend/scripts/process_article_cli.py`

A CLI script that calls the API endpoint (same behavior as web UI).

### 1.3 Reprocessing API Endpoint

**New File**: `programs/article_summarizer_backend/app/routes/reprocess.py`

```python
@router.get("/api/article/reprocess")
async def reprocess_article(
    article_id: int,
    article_type: str,  # 'public' or 'private'
    steps: str,         # Comma-separated: 'ai_summary,themed_insights,embedding'
    token: str
):
    """
    Partial reprocessing of an existing article via SSE streaming.

    Steps available:
    - ai_summary: Regenerate summary, insights, quotes from existing transcript
    - themed_insights: Regenerate themed insights (private articles only)
    - embedding: Regenerate vector embedding

    Note: video_frames requires Phase 2 (media persistence)
    """
```

### 1.4 Add `reprocess_article()` Method to ArticleProcessor

**File**: `programs/article_summarizer_backend/app/services/article_processor.py`

New method to support partial reprocessing:

```python
async def reprocess_article(
    self,
    article_id: int,
    article_type: str,
    steps: List[str],
    user_id: Optional[str] = None,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Partial reprocessing of an existing article.
    """
```

### 1.5 Create Admin Reprocess Page

**New Files**:
- `web-apps/article-summarizer/src/app/admin/reprocess/page.tsx`
- `web-apps/article-summarizer/src/app/admin/reprocess/ReprocessPageClient.tsx`

UI for selecting article and reprocessing steps.

---

## Reprocessing Operations Detail

### AI Summary Regeneration

| Aspect | Details |
|--------|---------|
| **Method** | `_generate_summary_async(url, metadata)` |
| **Input from DB** | `transcript_text`, `original_article_text`, `video_frames`, `content_source`, `platform` |
| **Output Updated** | `summary_text`, `key_insights`, `quotes`, `topics`, `word_count`, `duration_minutes` |
| **Re-downloads?** | No |
| **API Cost** | Yes (Claude) |

**Important Logic**:
- If `content_source` is `video` or `audio` AND `transcript_text` is empty → Error: "Transcribe first"
- If `content_source` is `article` → Uses `original_article_text`
- If `video_frames` exist → Enriches with transcript excerpts before AI call

### Themed Insights Generation

| Aspect | Details |
|--------|---------|
| **Method** | `_generate_themed_insights_async(user_id, metadata, ai_summary)` |
| **Input from DB** | `transcript_text`, `summary_text`, `key_insights`, org's themes |
| **Output Updated** | `private_article_themed_insights` table |
| **Re-downloads?** | No |
| **API Cost** | Yes (Claude) |

**Constraints**:
- Only available for private articles
- Requires user_id to look up organization's themes
- If no themes defined for org → Returns empty

### Embedding Regeneration

| Aspect | Details |
|--------|---------|
| **Method** | `_generate_embedding(text)` |
| **Input from DB** | `title`, `summary_text`, `key_insights` |
| **Output Updated** | `embedding` vector field |
| **Re-downloads?** | No |
| **API Cost** | Yes (OpenAI embeddings) |

### Video Frame Extraction (Phase 2)

| Aspect | Details |
|--------|---------|
| **Method** | `_extract_and_upload_frames(video_path, url, article_id)` |
| **Input** | Downloaded video file OR `media_storage_path` |
| **Output Updated** | `video_frames` JSONB array |
| **Re-downloads?** | Yes (unless media persisted) |
| **API Cost** | No (local processing) |

---

## Database Schema for Reprocessing

### Existing Fields Used

```sql
-- articles / private_articles tables
id                    -- Primary key
title                 -- For embedding text
url                   -- For logging, reference
content_source        -- 'video', 'audio', 'article', 'mixed'
transcript_text       -- Formatted transcript with timestamps
original_article_text -- Raw article content
summary_text          -- AI-generated summary
key_insights          -- JSONB array
quotes                -- JSONB array
video_frames          -- JSONB array of frame objects
video_id              -- Platform video ID (for re-fetching)
platform              -- youtube, loom, vimeo, etc.
audio_url             -- Direct audio/video URL
embedding             -- Vector for semantic search
```

### Themed Insights Table

```sql
private_article_themed_insights (
    id SERIAL PRIMARY KEY,
    private_article_id INTEGER REFERENCES private_articles(id),
    theme_id INTEGER REFERENCES themes(id),
    insight_text TEXT,
    timestamp_seconds FLOAT,
    time_formatted TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
```

---

## Phase 2: Media Persistence (Detailed Plan)

**Goal**: Enable video frame re-extraction and transcript regeneration without re-downloading media by persisting downloaded media to Supabase Storage with a 30-day TTL.

---

### 2.1 Database Schema Changes

**Migration File**: `supabase/migrations/XXXX_add_media_persistence.sql`

```sql
-- Add media storage fields to articles
ALTER TABLE articles ADD COLUMN media_storage_path TEXT;
ALTER TABLE articles ADD COLUMN media_storage_expires_at TIMESTAMPTZ;
ALTER TABLE articles ADD COLUMN media_content_type TEXT;  -- 'video/mp4', 'audio/mpeg', etc.
ALTER TABLE articles ADD COLUMN media_size_bytes BIGINT;
ALTER TABLE articles ADD COLUMN media_duration_seconds FLOAT;

-- Add media storage fields to private_articles
ALTER TABLE private_articles ADD COLUMN media_storage_path TEXT;
ALTER TABLE private_articles ADD COLUMN media_storage_expires_at TIMESTAMPTZ;
ALTER TABLE private_articles ADD COLUMN media_content_type TEXT;
ALTER TABLE private_articles ADD COLUMN media_size_bytes BIGINT;
ALTER TABLE private_articles ADD COLUMN media_duration_seconds FLOAT;

-- Create index for cleanup job (find expired media)
CREATE INDEX idx_articles_media_expires ON articles(media_storage_expires_at)
  WHERE media_storage_path IS NOT NULL;
CREATE INDEX idx_private_articles_media_expires ON private_articles(media_storage_expires_at)
  WHERE media_storage_path IS NOT NULL;

-- Optional: Create a view for articles with active media
CREATE VIEW articles_with_media AS
SELECT id, title, url, media_storage_path, media_storage_expires_at, media_content_type
FROM articles
WHERE media_storage_path IS NOT NULL
  AND media_storage_expires_at > NOW();
```

---

### 2.2 Storage Structure

**Bucket Name**: `article-media` (new bucket, separate from `video-frames` and `uploaded-media`)

```
supabase-storage/
└── article-media/
    ├── public/
    │   └── {article_id}/
    │       ├── media.mp4          # Downloaded video
    │       └── metadata.json      # Optional: duration, resolution, etc.
    └── private/
        └── {article_id}/
            ├── media.mp4
            └── metadata.json
```

**Bucket Configuration**:
```python
{
    "public": False,  # Private bucket - access via signed URLs
    "file_size_limit": 5368709120,  # 5GB (Pro tier)
    "allowed_mime_types": [
        "video/mp4", "video/webm", "video/quicktime", "video/x-matroska",
        "audio/mpeg", "audio/wav", "audio/mp4", "audio/ogg", "audio/flac"
    ]
}
```

---

### 2.3 Modified Download Flow

#### Current Flow (Phase 1)
```
1. Download video → /tmp/{uuid}/video.mp4
2. Extract frames (if demo_video=true)
3. Get transcript (YouTube API or Deepgram)
4. Delete temp directory
```

#### New Flow (Phase 2)
```
1. Download video → /tmp/{uuid}/video.mp4
2. Upload to Supabase Storage → article-media/{type}/{article_id}/media.mp4
3. Store path + expiry in database
4. Extract frames (if demo_video=true)
5. Get transcript
6. Delete temp directory (storage has copy now)
```

**Key Decision Point**: Upload to storage AFTER download but BEFORE processing. This ensures:
- If processing fails, we still have the media
- User can re-run processing without re-download
- 30-day window to experiment with different processing options

---

### 2.4 Code Changes

#### 2.4.1 New StorageManager Methods

**File**: `programs/article_summarizer_backend/core/storage_manager.py`

```python
ARTICLE_MEDIA_BUCKET = "article-media"

def upload_article_media(
    self,
    file_path: str,
    article_id: int,
    article_type: str,  # 'public' or 'private'
    content_type: str
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Upload downloaded media to persistent storage.

    Args:
        file_path: Local path to downloaded media
        article_id: Article ID
        article_type: 'public' or 'private'
        content_type: MIME type

    Returns:
        (success, storage_path, signed_url)
    """
    pass

def get_article_media_url(
    self,
    storage_path: str,
    expiry_seconds: int = 3600
) -> Optional[str]:
    """
    Get a signed URL for accessing stored media.

    Args:
        storage_path: Path in storage bucket
        expiry_seconds: URL expiry time

    Returns:
        Signed URL or None
    """
    pass

def download_article_media(
    self,
    storage_path: str,
    destination_path: str
) -> bool:
    """
    Download media from storage to local temp file.

    Args:
        storage_path: Path in storage bucket
        destination_path: Local destination path

    Returns:
        True if successful
    """
    pass

def delete_article_media(
    self,
    article_id: int,
    article_type: str
) -> bool:
    """
    Delete stored media for an article.
    """
    pass
```

#### 2.4.2 Modify ArticleProcessor Download Logic

**File**: `programs/article_summarizer_backend/app/services/article_processor.py`

Changes to `_download_video()` and `_download_audio()`:

```python
async def _download_video(self, video_url: str, video_id: str, ...) -> Tuple[str, dict]:
    """
    Download video and optionally persist to storage.

    Returns:
        (local_path, media_info)
    """
    # Existing download logic...
    local_path = self._download_with_ytdlp(...)

    # NEW: Persist to storage if article_id is available
    if self.persist_media and article_id:
        from core.storage_manager import StorageManager
        storage = StorageManager(bucket_name=StorageManager.ARTICLE_MEDIA_BUCKET)

        success, storage_path, _ = storage.upload_article_media(
            file_path=local_path,
            article_id=article_id,
            article_type=article_type,
            content_type=self._detect_content_type(local_path)
        )

        if success:
            # Update article with storage info
            self._update_media_storage_info(
                article_id=article_id,
                article_type=article_type,
                storage_path=storage_path,
                expires_at=datetime.now() + timedelta(days=30),
                size_bytes=os.path.getsize(local_path),
                duration_seconds=media_info.get('duration')
            )

    return local_path, media_info
```

#### 2.4.3 New Reprocessing Methods

**File**: `programs/article_summarizer_backend/app/services/article_processor.py`

```python
async def _reprocess_video_frames(
    self,
    article: Dict,
    article_id: int,
    article_type: str,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Re-extract video frames from stored media.

    Steps:
    1. Check if media_storage_path exists and not expired
    2. Download from storage to temp
    3. Run frame extraction
    4. Update video_frames in database
    5. Clean up temp

    Returns:
        {'success': True, 'frame_count': 12} or {'success': False, 'error': '...'}
    """
    # Check for stored media
    storage_path = article.get('media_storage_path')
    expires_at = article.get('media_storage_expires_at')

    if not storage_path:
        return {
            'success': False,
            'error': 'No stored media available. Process article with media persistence enabled.'
        }

    if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
        return {
            'success': False,
            'error': f'Stored media expired on {expires_at}. Re-process article to download again.'
        }

    # Download from storage
    temp_dir = tempfile.mkdtemp()
    local_path = os.path.join(temp_dir, 'media.mp4')

    storage = StorageManager(bucket_name=StorageManager.ARTICLE_MEDIA_BUCKET)
    if not storage.download_article_media(storage_path, local_path):
        return {'success': False, 'error': 'Failed to download from storage'}

    try:
        # Extract frames
        frames = self._extract_and_upload_frames(local_path, article['url'], article_id)

        # Update database
        table = 'private_articles' if article_type == 'private' else 'articles'
        self.supabase.table(table).update({
            'video_frames': frames
        }).eq('id', article_id).execute()

        return {'success': True, 'frame_count': len(frames)}

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def _reprocess_transcript(
    self,
    article: Dict,
    article_id: int,
    article_type: str,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Re-generate transcript from stored media using Deepgram.

    Useful when:
    - YouTube transcript wasn't available initially
    - Want higher quality transcript
    - Original transcription had errors

    Returns:
        {'success': True, 'word_count': 5000} or {'success': False, 'error': '...'}
    """
    pass
```

#### 2.4.4 Update Reprocess Route

**File**: `programs/article_summarizer_backend/app/routes/reprocess.py`

Add new step options:

```python
# Valid steps now include Phase 2 options
valid_steps = {
    "ai_summary",           # Phase 1
    "themed_insights",      # Phase 1
    "embedding",            # Phase 1
    "video_frames",         # Phase 2
    "transcript"            # Phase 2
}
```

Update `get_article_reprocess_info()`:

```python
# Phase 2 availability checks
has_stored_media = bool(article.get('media_storage_path'))
media_expired = (
    article.get('media_storage_expires_at') and
    datetime.fromisoformat(article['media_storage_expires_at']) < datetime.now()
)

return {
    # ... existing fields ...

    # Phase 2 fields
    'has_stored_media': has_stored_media,
    'media_expired': media_expired,
    'media_expires_at': article.get('media_storage_expires_at'),
    'media_size_mb': round(article.get('media_size_bytes', 0) / 1024 / 1024, 1),

    'can_regen_video_frames': has_stored_media and not media_expired,
    'video_frames_unavailable_reason': (
        'Media expired' if media_expired else
        'No stored media - re-process article' if not has_stored_media else None
    ),
    'can_regen_transcript': has_stored_media and not media_expired,
    'transcript_unavailable_reason': (
        'Media expired' if media_expired else
        'No stored media - re-process article' if not has_stored_media else None
    )
}
```

---

### 2.5 Cleanup Job

**File**: `programs/article_summarizer_backend/scripts/cleanup_expired_media.py`

```python
#!/usr/bin/env python3
"""
Cleanup expired media from Supabase Storage.

Run daily via cron or Railway scheduled job.

Usage:
    python3 scripts/cleanup_expired_media.py [--dry-run]
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from supabase import create_client
from core.storage_manager import StorageManager


def cleanup_expired_media(dry_run: bool = False):
    """Delete expired media from storage and clear database references."""

    supabase = create_client(
        os.environ['SUPABASE_URL'],
        os.environ['SUPABASE_SERVICE_ROLE_KEY']
    )

    storage = StorageManager(bucket_name='article-media')

    # Find expired articles
    for table in ['articles', 'private_articles']:
        result = supabase.table(table).select(
            'id, media_storage_path, media_storage_expires_at'
        ).lt(
            'media_storage_expires_at', datetime.now().isoformat()
        ).not_.is_(
            'media_storage_path', 'null'
        ).execute()

        expired_count = len(result.data)
        print(f"Found {expired_count} expired media files in {table}")

        for article in result.data:
            storage_path = article['media_storage_path']
            article_id = article['id']

            if dry_run:
                print(f"  [DRY RUN] Would delete: {storage_path}")
            else:
                # Delete from storage
                try:
                    supabase.storage.from_('article-media').remove([storage_path])
                    print(f"  Deleted from storage: {storage_path}")
                except Exception as e:
                    print(f"  ERROR deleting {storage_path}: {e}")
                    continue

                # Clear database fields
                supabase.table(table).update({
                    'media_storage_path': None,
                    'media_storage_expires_at': None,
                    'media_size_bytes': None
                }).eq('id', article_id).execute()

                print(f"  Cleared database fields for article {article_id}")

    print("Cleanup complete!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted')
    args = parser.parse_args()

    cleanup_expired_media(dry_run=args.dry_run)
```

**Railway Cron Job** (or run manually):
```bash
# Run daily at 3am
0 3 * * * python3 scripts/cleanup_expired_media.py
```

---

### 2.6 UI Updates

**File**: `web-apps/article-summarizer/src/app/admin/reprocess/ReprocessPageClient.tsx`

Add Phase 2 UI elements:

```tsx
// In article info display
{articleInfo.has_stored_media && (
  <div className="text-sm text-gray-400 mt-1">
    <div className="flex items-center gap-2">
      <span className="text-green-400">Media stored</span>
      <span>({articleInfo.media_size_mb} MB)</span>
      {articleInfo.media_expires_at && (
        <span>Expires: {new Date(articleInfo.media_expires_at).toLocaleDateString()}</span>
      )}
    </div>
  </div>
)}

{!articleInfo.has_stored_media && articleInfo.content_source !== 'article' && (
  <div className="text-sm text-yellow-400 mt-1">
    No stored media - re-process article to enable video frame extraction
  </div>
)}

// Add new step checkboxes
{
  id: 'video_frames',
  label: 'Re-extract Video Frames',
  checked: false,
  disabled: !articleInfo.can_regen_video_frames,
  reason: articleInfo.video_frames_unavailable_reason,
  badge: articleInfo.has_stored_media ? `From stored media (${articleInfo.media_size_mb}MB)` : undefined
},
{
  id: 'transcript',
  label: 'Regenerate Transcript (Deepgram)',
  checked: false,
  disabled: !articleInfo.can_regen_transcript,
  reason: articleInfo.transcript_unavailable_reason,
  badge: 'Uses stored media'
}
```

---

### 2.7 Configuration Options

**Environment Variables**:

```bash
# Enable media persistence (default: false in dev, true in prod)
PERSIST_ARTICLE_MEDIA=true

# Media retention period in days (default: 30)
MEDIA_RETENTION_DAYS=30

# Maximum media file size in bytes (default: 5GB)
MAX_MEDIA_SIZE_BYTES=5368709120

# Supabase storage bucket for media (default: article-media)
ARTICLE_MEDIA_BUCKET=article-media
```

**ArticleProcessor Config**:

```python
class ArticleProcessor:
    def __init__(self, ...):
        self.persist_media = os.getenv('PERSIST_ARTICLE_MEDIA', 'false').lower() == 'true'
        self.media_retention_days = int(os.getenv('MEDIA_RETENTION_DAYS', '30'))
```

---

### 2.8 Files to Create/Modify (Phase 2)

| Action | File | Description |
|--------|------|-------------|
| Create | `supabase/migrations/XXXX_add_media_persistence.sql` | Database schema changes |
| Modify | `core/storage_manager.py` | Add article media upload/download methods |
| Modify | `app/services/article_processor.py` | Add media persistence to download flow |
| Modify | `app/services/article_processor.py` | Add `_reprocess_video_frames()`, `_reprocess_transcript()` |
| Modify | `app/routes/reprocess.py` | Add video_frames and transcript steps |
| Create | `scripts/cleanup_expired_media.py` | Scheduled cleanup job |
| Modify | `ReprocessPageClient.tsx` | Add Phase 2 UI elements |

---

### 2.9 Estimated Costs

| Operation | Storage Cost | API Cost |
|-----------|--------------|----------|
| Store 100MB video for 30 days | ~$0.0075 | - |
| Store 1GB video for 30 days | ~$0.075 | - |
| Re-extract video frames | - | Free (local FFmpeg) |
| Regenerate transcript (Deepgram) | - | ~$0.0125/min |

**Supabase Storage Pricing** (Pro tier):
- $0.021/GB/month for storage
- First 250GB included in Pro plan

---

### 2.10 Rollout Plan

1. **Deploy database migration** (adds columns, doesn't affect existing functionality)
2. **Deploy storage manager changes** (new methods, backward compatible)
3. **Deploy ArticleProcessor changes** with `PERSIST_ARTICLE_MEDIA=false`
4. **Test locally** with `PERSIST_ARTICLE_MEDIA=true`
5. **Enable in production** by setting env var
6. **Deploy UI updates** (shows Phase 2 options)
7. **Set up cleanup job** (Railway scheduled task or cron)

---

## UI Design: /admin/reprocess

```
┌─────────────────────────────────────────────────────────────────┐
│  🔄 Article Reprocessing                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Article ID: [____] Type: ○ Public ● Private  [Load Article]   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 📄 "How AI is Transforming Healthcare"                     ││
│  │    Source: YouTube • Created: Dec 1, 2024                  ││
│  │    Has transcript: ✓ • Has video frames: ✓ (12 frames)    ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Select operations to run:                                      │
│                                                                 │
│  ☑ Regenerate AI Summary & Insights                             │
│     Uses existing transcript to regenerate summary              │
│     ⏱️ ~30 seconds • 💰 Claude API call                         │
│                                                                 │
│  ☐ Regenerate Themed Insights (Private only)                    │
│     Extracts insights for your organization's themes            │
│     ⏱️ ~20 seconds • 💰 Claude API call                         │
│                                                                 │
│  ☐ Re-extract Video Frames                                      │
│     ⚠️ Requires downloading video (Phase 2)                     │
│     Currently disabled - media persistence not implemented      │
│                                                                 │
│  ☐ Regenerate Embedding                                         │
│     Updates vector embedding for semantic search                │
│     ⏱️ ~2 seconds • 💰 OpenAI API call                          │
│                                                                 │
│  [▶️ Run Selected Operations]                                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Progress:                                                   ││
│  │ ✅ Loaded article metadata                                  ││
│  │ ⏳ Generating AI summary... (15s)                           ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### UI Logic

| Step | Enabled When | Disabled Message |
|------|--------------|------------------|
| AI Summary | `transcript_text` exists OR `content_source='article'` | "No transcript available - transcribe first" |
| Themed Insights | `article_type='private'` AND themes exist | "Only for private articles" or "No themes defined" |
| Video Frames | Phase 2 only | "Coming soon - requires media persistence" |
| Embedding | Always | - |

---

## Files to Create/Modify

### Phase 1

| Action | File |
|--------|------|
| Modify | `programs/article_summarizer_backend/app/services/article_processor.py` |
| Create | `programs/article_summarizer_backend/scripts/process_article_cli.py` |
| Create | `programs/article_summarizer_backend/app/routes/reprocess.py` |
| Modify | `programs/article_summarizer_backend/app/main.py` |
| Create | `web-apps/article-summarizer/src/app/admin/reprocess/page.tsx` |
| Create | `web-apps/article-summarizer/src/app/admin/reprocess/ReprocessPageClient.tsx` |

### Phase 2 (Future)

| Action | File |
|--------|------|
| Create | `supabase/migrations/XXXX_add_media_storage_fields.sql` |
| Modify | `programs/article_summarizer_backend/app/services/article_processor.py` (download logic) |
| Create | `programs/article_summarizer_backend/scripts/cleanup_expired_media.py` |

---

## Reference: Existing regenerate_summary.py

The existing script at `programs/article_summarizer_backend/scripts/regenerate_summary.py` provides a template for:

1. Fetching article from database
2. Reconstructing metadata from stored fields
3. Calling processor methods
4. Updating database

Key functions to reuse:
- `reconstruct_metadata()` - Rebuilds metadata dict from DB record
- `update_article_in_db()` - Updates specific fields

---

## Implementation Notes

### Statefulness

Each reprocessing operation is atomic:
1. Fetch current article state from database
2. Reconstruct metadata needed for processor methods
3. Execute the specific step
4. Update only the affected fields
5. No temporary state between operations

### Error Handling

- Check prerequisites before each step (e.g., transcript exists for AI summary)
- Return clear error messages for missing dependencies
- Don't stop on warnings, only on blocking errors
- Log all operations for debugging

### SSE Streaming

Reprocess endpoint uses SSE (like `/process-direct`) for real-time progress:

```
event: step_start
data: {"step": "ai_summary", "elapsed": 0}

event: step_complete
data: {"step": "ai_summary", "elapsed": 32, "insights_count": 5}

event: completed
data: {"success": true, "steps_completed": ["ai_summary", "embedding"]}
```
