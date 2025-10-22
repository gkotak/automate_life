"""
Article Processing Routes

Endpoints for processing and managing articles.
"""

import logging
import uuid
import asyncio
import os
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from app.middleware.auth import verify_api_key
from core.event_emitter import ProcessingEventEmitter

logger = logging.getLogger(__name__)

router = APIRouter()


class ProcessArticleRequest(BaseModel):
    """Request model for processing an article"""
    url: HttpUrl


class ProcessArticleResponse(BaseModel):
    """Response model for article processing"""
    article_id: int
    status: str
    message: str
    url: Optional[str] = None


@router.post("/process-article", response_model=ProcessArticleResponse)
async def process_article(
    request: ProcessArticleRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Process an article URL and save to database

    This endpoint:
    1. Fetches the article content (with authentication if needed)
    2. Extracts video/audio transcripts if present
    3. Generates AI-powered summary using Claude
    4. Saves structured data to Supabase
    5. Returns the article ID for frontend display

    Args:
        request: ProcessArticleRequest with URL
        api_key: Validated API key from middleware

    Returns:
        ProcessArticleResponse with article_id and status
    """
    logger.info(f"📥 Processing article request: {request.url}")

    try:
        # Import ArticleProcessor here to avoid circular imports
        from app.services.article_processor import ArticleProcessor

        # Initialize processor
        processor = ArticleProcessor()

        # Process the article (now async)
        article_id = await processor.process_article(str(request.url))

        logger.info(f"✅ Successfully processed article: ID={article_id}")

        return ProcessArticleResponse(
            article_id=article_id,
            status="success",
            message="Article processed successfully",
            url=f"/article/{article_id}"
        )

    except Exception as e:
        logger.error(f"❌ Failed to process article {request.url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process article: {str(e)}"
        )


class ProcessArticleStreamResponse(BaseModel):
    """Response model for starting article processing with SSE"""
    job_id: str
    status: str
    message: str


@router.get("/process-direct")
async def process_article_direct(
    url: str,
    api_key: Optional[str] = None,
    user_id: Optional[str] = None
):
    """
    NEW APPROACH: Process article with generator-driven SSE streaming

    The generator itself does the processing and yields events in real-time.
    No background tasks, no queues - just direct streaming.

    Args:
        url: Article URL to process
        api_key: API key as query parameter
        user_id: Optional user ID for authentication (Supabase auth user)

    Returns:
        EventSourceResponse with real-time processing events
    """
    # Validate API key
    expected_api_key = os.getenv('API_KEY')
    if not expected_api_key or api_key != expected_api_key:
        logger.warning(f"🔒 Invalid or missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    logger.info(f"📡 Starting direct SSE processing for: {url}")

    async def process_and_stream():
        """
        Generator-driven processing: The generator itself does the work and yields events.

        This ensures real-time streaming because:
        1. Generator does work step-by-step
        2. Yields SSE event immediately after each step
        3. No background tasks, no queues, no race conditions
        """
        from app.services.article_processor import ArticleProcessor
        import time

        start_time = time.time()

        def elapsed():
            return int(time.time() - start_time)

        try:
            # Send ping to establish connection
            yield {
                "event": "ping",
                "data": json.dumps({"message": "SSE connection established", "elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            # Send started event
            yield {
                "event": "started",
                "data": json.dumps({"url": url, "elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            # Initialize processor (no event emitter - we're streaming directly)
            processor = ArticleProcessor(event_emitter=None)

            # Create async queue for progress events (producer-consumer pattern)
            event_queue = asyncio.Queue()
            metadata_result = None
            extraction_error = None

            # Define progress callback to add events to queue
            async def progress_callback(event_type: str, data: dict):
                """Callback to add progress events to queue for streaming"""
                await event_queue.put({
                    "event": event_type,
                    "data": {**data, "elapsed": elapsed()}
                })

            # Step 1: Extract metadata (includes content fetch and transcription)
            yield {
                "event": "fetch_start",
                "data": json.dumps({"url": url, "elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            logger.info(f"Starting metadata extraction for: {url}")

            # Run metadata extraction in background task
            async def extract_metadata_task():
                nonlocal metadata_result, extraction_error
                try:
                    metadata_result = await processor._extract_metadata(url, progress_callback=progress_callback)
                    # Signal completion
                    await event_queue.put(None)
                except Exception as e:
                    extraction_error = e
                    await event_queue.put(None)

            # Start extraction task
            extraction_task = asyncio.create_task(extract_metadata_task())

            # Stream progress events as they arrive
            while True:
                event = await event_queue.get()
                if event is None:  # Completion signal
                    break
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"])
                }
                await asyncio.sleep(0)

            # Wait for extraction to complete
            await extraction_task

            # Check for errors
            if extraction_error:
                raise extraction_error

            metadata = metadata_result

            # NOTE: fetch_complete is now emitted from within _extract_metadata() immediately after HTML fetch

            # Step 2: Detect media type (just analyze metadata, no I/O)
            yield {
                "event": "media_detect_start",
                "data": json.dumps({"elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            content_type = metadata.get('content_type')
            media_type = 'text-only'
            if content_type and hasattr(content_type, 'has_embedded_video') and content_type.has_embedded_video:
                media_type = 'video'
            elif content_type and hasattr(content_type, 'has_embedded_audio') and content_type.has_embedded_audio:
                media_type = 'audio'

            yield {
                "event": "media_detected",
                "data": json.dumps({"media_type": media_type, "elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            # Step 3: Determine transcript method (just analyze metadata, no I/O)
            yield {
                "event": "content_extract_start",
                "data": json.dumps({"elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            transcript_method = None
            if metadata.get('transcript'):
                if media_type == 'video':
                    transcript_method = 'youtube'
                elif media_type == 'audio':
                    # Check if it was chunked
                    if metadata.get('audio_chunks'):
                        transcript_method = 'chunked'
                    else:
                        transcript_method = 'audio'

            yield {
                "event": "content_extracted",
                "data": json.dumps({"transcript_method": transcript_method, "elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            # Step 4: Generate AI summary
            yield {
                "event": "ai_start",
                "data": json.dumps({"elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            logger.info("Starting AI summary generation...")
            ai_summary = await processor._generate_summary_async(url, metadata)

            yield {
                "event": "ai_complete",
                "data": json.dumps({"elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            # Step 5: Save to database
            yield {
                "event": "save_start",
                "data": json.dumps({"elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            logger.info("Saving to database...")
            article_id = processor._save_to_database(metadata, ai_summary)

            yield {
                "event": "save_complete",
                "data": json.dumps({"article_id": article_id, "elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            # Completion
            yield {
                "event": "completed",
                "data": json.dumps({"article_id": article_id, "url": f"/article/{article_id}", "elapsed": elapsed()})
            }

            logger.info(f"✅ Successfully processed article: ID={article_id}")

        except Exception as e:
            logger.error(f"❌ Processing failed: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e), "elapsed": elapsed()})
            }

    return EventSourceResponse(
        process_and_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/status/{job_id}")
async def stream_processing_status(
    job_id: str,
    api_key: Optional[str] = None
):
    """
    Stream real-time processing updates for a job via Server-Sent Events

    NOTE: This endpoint is deprecated. Use /process-direct instead for generator-driven streaming.

    This endpoint uses the old background task + queue pattern and may have buffering issues.

    Args:
        job_id: Job ID from background processing task
        api_key: API key as query parameter (since EventSource can't send headers)

    Returns:
        EventSourceResponse streaming processing events
    """
    # Validate API key from query parameter (EventSource limitation)
    expected_api_key = os.getenv('API_KEY')
    if not expected_api_key or api_key != expected_api_key:
        logger.warning(f"🔒 Invalid or missing API key for SSE stream: {job_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    logger.info(f"📡 Starting SSE stream for job: {job_id}")

    return EventSourceResponse(
        ProcessingEventEmitter.stream_events(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/article/{article_id}/status")
async def get_article_status(
    article_id: int,
    api_key: str = Depends(verify_api_key)
):
    """
    Get processing status of an article

    Useful for polling while article is being processed.

    Args:
        article_id: ID of the article
        api_key: Validated API key from middleware

    Returns:
        Status information
    """
    # This is a placeholder for future async processing
    # For now, all processing is synchronous
    return {
        "article_id": article_id,
        "status": "completed",
        "message": "Article processing is synchronous"
    }
