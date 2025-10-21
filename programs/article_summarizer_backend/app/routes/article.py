"""
Article Processing Routes

Endpoints for processing and managing articles.
"""

import logging
import uuid
import asyncio
import os
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


@router.post("/process-article-stream", response_model=ProcessArticleStreamResponse)
async def process_article_stream(
    request: ProcessArticleRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Start processing an article and return a job_id for SSE streaming

    This endpoint immediately returns a job_id that can be used to
    stream real-time processing updates via the /status/{job_id} endpoint.

    Args:
        request: ProcessArticleRequest with URL
        api_key: Validated API key from middleware

    Returns:
        ProcessArticleStreamResponse with job_id for streaming
    """
    logger.info(f"📥 Starting streamed article processing: {request.url}")

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Create event emitter for this job
    emitter = ProcessingEventEmitter(job_id)

    # Start processing in background
    async def process_in_background():
        try:
            from app.services.article_processor import ArticleProcessor

            # Send initial event
            await emitter.emit('started', {'url': str(request.url)})

            # Initialize processor with event emitter
            processor = ArticleProcessor(event_emitter=emitter)

            # Process the article
            article_id = await processor.process_article(str(request.url))

            # Send completion event
            await emitter.emit('completed', {
                'article_id': article_id,
                'url': f"/article/{article_id}"
            })

            logger.info(f"✅ Successfully processed article: ID={article_id}")

        except Exception as e:
            logger.error(f"❌ Failed to process article {request.url}: {e}", exc_info=True)
            await emitter.emit('error', {
                'message': str(e),
                'error': True
            })
        finally:
            # Signal end of stream
            await emitter.complete()

    # Start background task
    asyncio.create_task(process_in_background())

    return ProcessArticleStreamResponse(
        job_id=job_id,
        status="processing",
        message="Article processing started. Use job_id to stream progress."
    )


@router.get("/status/{job_id}")
async def stream_processing_status(
    job_id: str,
    api_key: Optional[str] = None
):
    """
    Stream real-time processing updates for a job via Server-Sent Events

    Connect to this endpoint with EventSource to receive real-time
    updates about article processing progress.

    Args:
        job_id: Job ID returned from /process-article-stream
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
        media_type="text/event-stream"
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
