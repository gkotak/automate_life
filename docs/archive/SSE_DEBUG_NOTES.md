# SSE Debugging Notes - Session End 2025-10-22

## Current Status: SSE Events Buffering Instead of Streaming

### The Problem
Events are being received all at once at the end of processing instead of streaming in real-time.

### Root Cause Identified
From backend logs (`programs/article_summarizer_backend/logs/backend.log`):

```
Processing Timeline:
01:24:42 - Processing starts (fetching, transcribing audio)
01:25:23 - Transcription completes
01:26:04 - AI summary completes, saves to database
01:26:05,055 - ✅ Processing complete

SSE Events (ALL AT ONCE):
01:26:05,058 - 📡 [SSE] Streaming event 'started'
01:26:05,058 - 📡 [SSE] Streaming event 'fetch_start'
01:26:05,058 - 📡 [SSE] Streaming event 'fetch_complete'
01:26:05,059 - 📡 [SSE] Streaming event 'media_detect_start'
01:26:05,059 - 📡 [SSE] Streaming event 'media_detected'
01:26:05,059 - 📡 [SSE] Streaming event 'content_extract_start'
01:26:05,059 - 📡 [SSE] Streaming event 'content_extracted'
01:26:05,060 - 📡 [SSE] Streaming event 'ai_start'
01:26:05,060 - 📡 [SSE] Streaming event 'ai_complete'
01:26:05,060 - 📡 [SSE] Streaming event 'save_start'
01:26:05,061 - 📡 [SSE] Streaming event 'save_complete'
01:26:05,061 - 📡 [SSE] Streaming event 'completed'
01:26:05,061 - 📡 [SSE] Streaming event 'complete'
```

**All 13 events streamed in 3 milliseconds** - clearly buffered!

### Why This Happens

**Current Architecture:**
```
1. POST /process-article-stream
   ├─ Create event emitter
   ├─ Start background task (asyncio.create_task)
   └─ Return job_id immediately

2. GET /status/{job_id}
   ├─ Return EventSourceResponse(stream_events())
   └─ Generator created but NOT consumed yet

3. Background task runs
   ├─ Emits events to asyncio.Queue
   └─ Events pile up in queue

4. Processing completes

5. THEN generator finally runs
   └─ Consumes ALL queued events at once
```

**The Issue:** The async generator (`stream_events()`) doesn't actually start executing until something actively pulls from it. By the time it starts, all processing is done and all events are queued.

### What We Tried (Didn't Work)

1. ✅ **2KB padding** - Tried to force proxy flush (didn't help, not a proxy issue)
2. ✅ **`await asyncio.sleep(0)`** after yields - Tried to give control to event loop (didn't help)
3. ✅ **Increased delay before processing** - Tried to ensure SSE connects first (didn't help)
4. ✅ **Heartbeat pings** - Tried to keep connection alive (didn't help with buffering)

### The Real Problem

The async generator pattern with background tasks **fundamentally doesn't work** for our use case because:

- Background task emits events → asyncio.Queue
- SSE generator reads from queue → but doesn't start until response streams
- Response doesn't stream until function returns
- Function already returned, processing continues in background
- **Generator isn't consumed until processing finishes**

This is a **chicken-and-egg problem** with async generators and background tasks.

## Solutions for Tomorrow

### Option 1: Generator-Driven Processing (Recommended)
**Don't use background tasks.** Make the SSE generator itself run the processing:

```python
@router.get("/process-and-stream/{job_id}")
async def process_and_stream(job_id: str, url: str):
    async def process_with_events():
        emitter = ProcessingEventEmitter(job_id)

        yield ping_event()

        # Do processing RIGHT HERE in the generator
        yield fetch_start_event()
        metadata = await fetch_article(url)
        yield fetch_complete_event()

        yield media_detect_event()
        # ... etc

    return EventSourceResponse(process_with_events())
```

**Pros:**
- Generator is actively consuming as it processes
- Events stream in real-time automatically
- Simpler architecture

**Cons:**
- Processing blocks the SSE response (but that's fine for SSE)
- Can't easily separate processing from streaming

### Option 2: Use Channels/Streams Instead of Queue
Use a proper async pub/sub like `asyncio.Stream` or third-party library that actively pushes instead of queuing.

### Option 3: Polling Instead of SSE (Fallback)
If SSE proves too complex, switch to frontend polling:
- Frontend polls `/status/{job_id}` every 2 seconds
- Backend returns current progress
- Much simpler, works reliably

## Local Development Setup (Working!)

✅ **Backend logs now save to file:**
```bash
# Start backend
cd programs/article_summarizer_backend
./run_local.sh

# Logs saved to: logs/backend.log
# View in real-time: tail -f logs/backend.log
# Or Claude can read: Read logs/backend.log
```

✅ **CORS configured for all Next.js ports:**
- localhost:3000, 3001, 3002, 8000

✅ **Environment setup:**
- Local: `.env.local` → points to localhost:8000
- Production: `.env.production` → points to Railway
- Vercel always uses Railway (production env vars)

## Files Modified Today

**Backend:**
- `programs/article_summarizer_backend/core/event_emitter.py` - Added padding, asyncio.sleep(0)
- `programs/article_summarizer_backend/app/routes/article.py` - Added SSE endpoints
- `programs/article_summarizer_backend/requirements.txt` - Added sse-starlette
- `programs/article_summarizer_backend/run_local.sh` - Added log file output
- `programs/article_summarizer_backend/.env.local` - Added CORS ports

**Frontend:**
- `web-apps/article-summarizer/src/app/admin/page.tsx` - Added SSE consumer
- `web-apps/article-summarizer/.env.local` - Added API_URL config

**Documentation:**
- `LOCAL_DEVELOPMENT.md` - Complete local dev guide
- `.claude/commands/start-local.md` - Slash command for starting servers

## Next Session TODO

1. **Implement Option 1** (generator-driven processing)
2. **Test locally** to verify real-time streaming
3. **If working, deploy to Railway**
4. **If still issues, consider Option 3** (polling)

## Key Insights

- ✅ SSE works locally (no Railway proxy issues)
- ✅ Python emits events correctly
- ✅ Events reach the queue
- ❌ **Async generator pattern doesn't consume in real-time**
- 🎯 **Need to redesign architecture** where generator drives processing

## Commands for Tomorrow

```bash
# Start backend (Terminal 1)
cd programs/article_summarizer_backend
./run_local.sh

# Start frontend (Terminal 2)
cd web-apps/article-summarizer
npm run dev

# View logs
tail -f programs/article_summarizer_backend/logs/backend.log

# Or use slash command
/start-local
```

---

**Status:** Ready to implement generator-driven SSE tomorrow! 🚀
