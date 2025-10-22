# SSE Streaming Implementation Session - October 22, 2025

## Session Summary

Today we worked on fixing real-time Server-Sent Events (SSE) streaming for the article summarizer backend. The goal was to show real-time progress updates in the UI as articles are processed.

## Problem Identified

**Issue:** SSE events were buffering and arriving all at once at the end of processing instead of streaming in real-time.

**Root Cause:** The article processing pipeline has a critical bottleneck in `_process_audio_content()` → `_transcribe_large_audio_file()` which is **synchronous** and blocks the event loop for 40-105 seconds during audio transcription.

**Timeline of actual processing (Stratechery audio article):**
- 10:22:21 - Started processing
- 10:22:21 - Downloading 9.2MB MP3 audio
- 10:22:27 - Sending chunk 1/3 to OpenAI Whisper API (40 seconds)
- 10:23:07 - Sending chunk 2/3 to Whisper API (35 seconds)
- 10:23:42 - Sending chunk 3/3 to Whisper API (30 seconds)
- 10:24:32 - AI summary generation with Claude (23 seconds)
- 10:24:55 - Save to database (2 seconds)

**User Experience:** UI showed "Fetching article" for 105 seconds while audio was actually being transcribed in chunks.

## Solutions Attempted

### 1. ❌ Background Task + Queue Pattern (FAILED)
**Approach:** Background task emits events to queue, generator consumes from queue
**Why it failed:** Race condition - background task blocks event loop, queue fills up before generator can consume

### 2. ❌ Hybrid Approach with asyncio.sleep(0) (FAILED)
**Approach:** Event emitter yields control after each emit using `asyncio.sleep(0)`
**Why it failed:** Still buffered because `_process_audio_content()` is synchronous and blocks for 40+ seconds

### 3. ✅ Generator-Driven Approach (PARTIALLY WORKING)
**Approach:** Generator itself does the work step-by-step, yielding events between steps
**What works:** Events stream correctly for fast operations (HTML fetch, metadata analysis, AI summary, DB save)
**What doesn't work:** Still blocked during audio transcription because `_extract_metadata()` internally calls synchronous audio processing

## Code Changes Made

### 1. Refactored `/api/process-direct` endpoint
**File:** `programs/article_summarizer_backend/app/routes/article.py` (lines 198-338)

**Changes:**
- Removed background task pattern
- Removed event emitter and queue consumer
- Generator directly calls processor methods
- Yields SSE events between each step

```python
async def process_and_stream():
    processor = ArticleProcessor(event_emitter=None)

    # Step 1: Fetch & extract metadata
    yield fetch_start_event()
    metadata = await processor._extract_metadata(url)  # ◄─ BLOCKS HERE for 40-105s
    yield fetch_complete_event()

    # Step 2: Analyze media type (fast)
    yield media_detect_start_event()
    media_type = analyze_media_type(metadata)
    yield media_detected_event()

    # Step 3: AI summary (now async)
    yield ai_start_event()
    ai_summary = await processor._generate_summary_async(url, metadata)
    yield ai_complete_event()

    # Step 4: Save to database (fast)
    yield save_start_event()
    article_id = processor._save_to_database(metadata, ai_summary)
    yield save_complete_event()
```

### 2. Created async wrapper for AI summary
**File:** `programs/article_summarizer_backend/app/services/article_processor.py` (line 517)

**Added:**
```python
async def _generate_summary_async(self, url: str, metadata: Dict) -> Dict:
    """
    Async wrapper for AI summary generation.
    Runs synchronous Claude API call in thread pool.
    """
    import asyncio
    return await asyncio.to_thread(self._generate_summary_with_ai, url, metadata)
```

### 3. Deleted broken `/api/process-article-stream` endpoint
**File:** `programs/article_summarizer_backend/app/routes/article.py` (deleted lines 96-164)

**Reason:** This endpoint used the problematic background task + queue pattern

## Architecture Analysis

### Current Method Call Chain (Audio Article):

```
/api/process-direct (Generator)
  ├─ yield "fetch_start"
  │
  ├─ _extract_metadata(url)  ◄────────────────────┐
  │   ├─ Fetch HTML (1s)                          │
  │   ├─ Detect content type (instant)            │
  │   └─ _process_audio_content()  ◄──────────────┼─ BOTTLENECK
  │       └─ _download_and_transcribe_media()     │  40-105 seconds
  │           └─ _transcribe_large_audio_file()   │  Synchronous!
  │               ├─ Split audio into chunks      │  Blocks event loop
  │               └─ For each chunk:              │
  │                   └─ Whisper API call (30-40s)│
  │                                                │
  ├─ yield "fetch_complete"  ◄────────────────────┘
  │
  ├─ yield "media_detected"
  ├─ yield "content_extracted"
  │
  ├─ _generate_summary_async()  ◄─ Fixed! Uses thread pool
  │
  └─ _save_to_database()  ◄─ Fast, no issues
```

### Bottleneck Methods:

1. **`_process_audio_content(audio_urls, soup, url)`** - line 451
   - Synchronous method
   - Calls `_download_and_transcribe_media()`

2. **`_download_and_transcribe_media(media_url)`** - line 1265
   - Synchronous method
   - Downloads audio and calls Whisper API
   - Calls `_transcribe_large_audio_file()` for large files

3. **`_transcribe_large_audio_file(audio_path)`** - line 1350
   - Synchronous method
   - Splits large audio into chunks
   - Processes each chunk sequentially with Whisper API
   - **This is where 40-105 seconds are spent**

## Remaining Issue

**Current State:**
- UI shows "Fetching article" for 40-105 seconds
- Backend logs show it's actually transcribing audio in chunks
- Generator cannot yield progress updates during this time

**Why:**
The entire audio transcription pipeline (`_process_audio_content` → `_download_and_transcribe_media` → `_transcribe_large_audio_file`) is synchronous and blocks the event loop.

## Solution Options

### Option 1: Accept Current Behavior ⚠️
- Update UI text to "Fetching and transcribing content..."
- Set user expectations that audio articles take 1-2 minutes
- **Pros:** No code changes needed
- **Cons:** Not true "real-time" progress

### Option 2: Refactor Audio Processing to Async ✅ (RECOMMENDED)
**What needs to change:**

1. Make `_process_audio_content()` async
2. Make `_download_and_transcribe_media()` async
3. Make `_transcribe_large_audio_file()` async with progress callbacks
4. Have generator yield events during transcription:
   - "Downloading audio..."
   - "Transcribing chunk 1/3..."
   - "Transcribing chunk 2/3..."
   - "Transcribing chunk 3/3..."

**Changes required:**
```python
# In article_processor.py

async def _process_audio_content(self, audio_urls, soup, url, progress_callback=None):
    for idx, audio in enumerate(audio_urls):
        if progress_callback:
            await progress_callback('download_start', {'chunk': idx+1})

        transcript = await self._download_and_transcribe_media_async(
            audio_url,
            progress_callback=progress_callback
        )

        if progress_callback:
            await progress_callback('transcribe_complete', {'chunk': idx+1})

async def _download_and_transcribe_media_async(self, url, progress_callback=None):
    # Download audio
    audio_path = await asyncio.to_thread(download_audio, url)

    # Transcribe with progress
    transcript = await self._transcribe_large_audio_file_async(
        audio_path,
        progress_callback=progress_callback
    )
    return transcript

async def _transcribe_large_audio_file_async(self, audio_path, progress_callback=None):
    chunks = split_audio(audio_path)

    for i, chunk in enumerate(chunks):
        if progress_callback:
            await progress_callback('chunk_start', {
                'current': i+1,
                'total': len(chunks)
            })

        # Run Whisper API in thread pool (it's synchronous)
        result = await asyncio.to_thread(
            self.file_transcriber.transcribe_file,
            chunk
        )

        if progress_callback:
            await progress_callback('chunk_complete', {
                'current': i+1,
                'total': len(chunks)
            })
```

Then in the generator:
```python
async def process_and_stream():
    # Define progress callback
    async def progress_callback(event_type, data):
        yield {
            "event": event_type,
            "data": json.dumps({**data, "elapsed": elapsed()})
        }
        await asyncio.sleep(0)

    # Extract metadata with progress updates
    metadata = await processor._extract_metadata_async(
        url,
        progress_callback=progress_callback
    )
```

### Option 3: Background Progress Updates via WebSocket 🔄
- Keep current synchronous code
- Add separate WebSocket connection for progress
- Background task updates WebSocket during processing
- **Pros:** No refactoring needed
- **Cons:** More complex architecture, two connections

## Next Steps

**Recommended Path:**
1. Implement Option 2 (Async Audio Processing with Progress Callbacks)
2. Test with Stratechery audio article
3. Verify real-time progress in UI:
   - "Downloading audio file..."
   - "Processing audio chunk 1/3..."
   - "Processing audio chunk 2/3..."
   - "Processing audio chunk 3/3..."
   - "Generating AI summary..."
   - "Saving to database..."

**Estimated Effort:**
- Refactor audio processing methods: ~2-3 hours
- Test and debug: ~1 hour
- Update frontend to handle new events: ~30 minutes

## Technical Debt Eliminated

✅ Removed background task + queue pattern (root cause of buffering)
✅ Simplified architecture - generator-driven is cleaner
✅ Made AI summary generation async (no longer blocks)
✅ Deleted broken `/api/process-article-stream` endpoint

## Technical Debt Remaining

⚠️ Audio transcription pipeline is still synchronous
⚠️ Cannot show real-time progress during the longest operation (audio transcription)
⚠️ User sees "Fetching article" for 40-105 seconds with no updates

## Files Modified Today

1. `programs/article_summarizer_backend/app/routes/article.py`
   - Refactored `/api/process-direct` to generator-driven approach
   - Deleted `/api/process-article-stream` endpoint
   - Updated `/status/{job_id}` documentation

2. `programs/article_summarizer_backend/app/services/article_processor.py`
   - Added `_generate_summary_async()` method

3. `programs/article_summarizer_backend/core/event_emitter.py`
   - Added `await asyncio.sleep(0)` to emit method (can be reverted)

## Testing Performed

- Tested with text-only article (Wait But Why) ✅ Works
- Tested with audio article (Stratechery) ⚠️ Buffering during transcription
- Verified SSE events arrive for fast operations ✅
- Verified backend logs show correct processing sequence ✅

## Environment

- Backend: FastAPI with sse-starlette
- Frontend: Next.js (http://localhost:3000)
- Backend: http://localhost:8000
- Transcription: OpenAI Whisper API
- AI: Claude API
- Database: Supabase

## References

- SSE Debug Notes: `SSE_DEBUG_NOTES.md`
- Backend logs: `programs/article_summarizer_backend/logs/backend.log`
- Frontend admin page: `web-apps/article-summarizer/src/app/admin/page.tsx`

---

**Session Date:** October 22, 2025
**Status:** Partial solution implemented - async refactoring needed for full real-time progress
**Priority:** Medium - current behavior is functional but not ideal for user experience
