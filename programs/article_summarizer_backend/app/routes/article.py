"""
Article Processing Routes

Endpoints for processing and managing articles.
"""

import logging
import uuid
import asyncio
import os
import json
import tempfile
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, HttpUrl
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from app.middleware.auth import verify_supabase_jwt
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


class ProcessArticleStreamResponse(BaseModel):
    """Response model for starting article processing with SSE"""
    job_id: str
    status: str
    message: str


@router.get("/process-direct")
async def process_article_direct(
    url: str,
    force_reprocess: bool = False,
    demo_video: bool = False,
    token: Optional[str] = None
):
    """
    NEW APPROACH: Process article with generator-driven SSE streaming

    The generator itself does the processing and yields events in real-time.
    No background tasks, no queues - just direct streaming.

    NOTE: EventSource doesn't support custom headers, so we accept the token as a query parameter.

    Args:
        url: Article URL to process
        force_reprocess: If True, reprocess article even if it already exists
        demo_video: If True, extract video frames for demo videos (screen shares)
        token: Supabase JWT token (passed as query param for SSE compatibility)

    Returns:
        EventSourceResponse with real-time processing events
    """
    # Verify token manually since we can't use Depends with query param
    from app.middleware.auth import get_supabase_admin

    if not token:
        logger.warning("🔒 SSE request without token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    try:
        supabase = get_supabase_admin()
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            logger.warning("🔒 Invalid token for SSE request")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        user_id = user_response.user.id
        logger.info(f"📡 Starting direct SSE processing for: {url} (user: {user_id})")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verifying token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

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

            # Check if article already exists (unless force_reprocess is True)
            if not force_reprocess:
                existing = processor.check_article_exists(url)
                if existing:
                    article_id = existing['id']

                    # Check if user has already saved this article
                    user_already_has_article = False
                    if user_id:
                        try:
                            result = processor.supabase.table('article_users').select('*').eq(
                                'article_id', article_id
                            ).eq(
                                'user_id', user_id
                            ).execute()
                            user_already_has_article = len(result.data) > 0
                        except Exception as e:
                            logger.warning(f"⚠️ Error checking article_users: {e}")

                    if user_already_has_article:
                        # User already has this article - show reprocess warning
                        logger.info(f"⚠️ User already has this article (ID: {article_id}). Asking for confirmation...")
                        yield {
                            "event": "duplicate_detected",
                            "data": json.dumps({
                                "article_id": existing['id'],
                                "title": existing['title'],
                                "created_at": existing['created_at'],
                                "updated_at": existing['updated_at'],
                                "url": f"/article/{existing['id']}",
                                "elapsed": elapsed()
                            })
                        }
                        await asyncio.sleep(0)
                        logger.info(f"⚠️ Waiting for user confirmation to reprocess")
                        return
                    else:
                        # Article exists globally but user doesn't have it - add to library
                        logger.info(f"📚 Article exists globally (ID: {article_id}). Adding to user's library...")

                        # Associate article with user in junction table
                        if user_id:
                            try:
                                # Get user's organization_id
                                user_data = processor.supabase.table('users').select('organization_id').eq('id', user_id).single().execute()
                                organization_id = user_data.data.get('organization_id') if user_data.data else None

                                processor.supabase.table('article_users').insert({
                                    'article_id': article_id,
                                    'user_id': user_id,
                                    'organization_id': organization_id
                                }).execute()
                                logger.info(f"✅ Associated article with user: {user_id}")

                                # Emit success event only if association succeeded
                                yield {
                                    "event": "completed",
                                    "data": json.dumps({
                                        "article_id": article_id,
                                        "url": f"/article/{article_id}",
                                        "elapsed": elapsed(),
                                        "already_processed": True,
                                        "message": "Article already exists - added to your library"
                                    })
                                }
                                await asyncio.sleep(0)
                                logger.info(f"✅ Article added to user's library (no reprocessing needed)")
                                return
                            except Exception as e:
                                logger.error(f"❌ Failed to associate article with user: {e}")
                                # Emit error event instead of success
                                yield {
                                    "event": "error",
                                    "data": json.dumps({
                                        "error": f"Failed to add article to your library: {str(e)}",
                                        "elapsed": elapsed()
                                    })
                                }
                                await asyncio.sleep(0)
                                return
                        else:
                            # No user_id - just return article exists without associating
                            yield {
                                "event": "completed",
                                "data": json.dumps({
                                    "article_id": article_id,
                                    "url": f"/article/{article_id}",
                                    "elapsed": elapsed(),
                                    "already_processed": True,
                                    "message": "Article already exists"
                                })
                            }
                            await asyncio.sleep(0)
                            return
            else:
                logger.info(f"🔄 Force reprocessing article: {url}")

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

            # Step 0 & 1: YouTube Discovery + Fetch Start
            yield {
                "event": "fetch_start",
                "data": json.dumps({"url": url, "elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            # Try to discover YouTube URL from content_queue (part of "Fetching article" step)
            processing_url = await processor._try_youtube_discovery(url)

            logger.info(f"Starting metadata extraction for: {processing_url} (demo_video={demo_video})")

            # Run metadata extraction in background task
            async def extract_metadata_task():
                nonlocal metadata_result, extraction_error
                try:
                    metadata_result = await processor._extract_metadata(
                        processing_url,
                        progress_callback=progress_callback,
                        extract_demo_frames=demo_video
                    )
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

            # NOTE: fetch_complete, content_extract_start, and content_extracted are now emitted
            # from within _extract_metadata() as progress callbacks during actual processing.
            # This ensures correct timing: events fire when work actually happens, not after.

            # Step 4: Generate AI summary
            yield {
                "event": "ai_start",
                "data": json.dumps({"elapsed": elapsed()})
            }
            await asyncio.sleep(0)

            logger.info("Starting AI summary generation...")
            ai_summary = await processor._generate_summary_async(processing_url, metadata)

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
            article_id = processor._save_to_database(metadata, ai_summary, user_id=user_id)

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
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Stream real-time processing updates for a job via Server-Sent Events

    NOTE: This endpoint is deprecated. Use /process-direct instead for generator-driven streaming.

    This endpoint uses the old background task + queue pattern and may have buffering issues.

    Args:
        job_id: Job ID from background processing task
        user_id: User ID extracted from JWT token

    Returns:
        EventSourceResponse streaming processing events
    """
    logger.info(f"📡 Starting SSE stream for job: {job_id} (user: {user_id})")

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
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Get processing status of an article

    Useful for polling while article is being processed.

    Args:
        article_id: ID of the article
        user_id: User ID extracted from JWT token

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


@router.post("/upload-media")
async def upload_media(
    file: UploadFile = File(...),
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Upload a media file via backend proxy to Supabase Storage

    This securely uploads files through the backend with proper authentication.
    File size limits are based on Supabase tier (Pro: 5GB, Free: 50MB).

    Args:
        file: The uploaded media file
        user_id: User ID extracted from JWT token

    Returns:
        Dictionary with the file URL
    """
    from core.storage_manager import StorageManager

    logger.info(f"📤 [UPLOAD] Receiving file upload from user {user_id}: {file.filename}")

    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )

    # Get file extension
    file_ext = Path(file.filename).suffix.lower()

    # Supported extensions
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg'}
    audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma', '.opus'}
    document_extensions = {'.pdf'}

    if file_ext not in video_extensions and file_ext not in audio_extensions and file_ext not in document_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(sorted(video_extensions | audio_extensions | document_extensions))}"
        )

    # Determine media type and content type
    if file_ext in video_extensions:
        media_type = 'video'
    elif file_ext in audio_extensions:
        media_type = 'audio'
    else:
        media_type = 'document'

    # Map extensions to MIME types
    mime_types = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.pdf': 'application/pdf'
    }
    content_type = mime_types.get(file_ext, f"{media_type}/{file_ext[1:]}" if media_type != 'document' else 'application/octet-stream')

    logger.info(f"📁 [UPLOAD] File type: {media_type} ({file_ext}, {content_type})")

    # Save to temporary location first
    temp_dir = Path(tempfile.gettempdir()) / "article_summarizer_uploads"
    temp_dir.mkdir(exist_ok=True, parents=True)

    unique_id = uuid.uuid4().hex[:12]
    temp_filename = f"{unique_id}_{file.filename}"
    temp_path = temp_dir / temp_filename

    try:
        # Save uploaded file to temp location
        logger.info(f"💾 [UPLOAD] Saving to temp: {temp_path}")
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size_mb = temp_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ [UPLOAD] Temp file saved: {file_size_mb:.2f} MB")

        # Upload to Supabase Storage
        logger.info(f"☁️ [UPLOAD] Uploading to Supabase Storage...")
        storage_manager = StorageManager(bucket_name=StorageManager.MEDIA_BUCKET_NAME)
        success, storage_path, public_url = storage_manager.upload_media_file(
            file_path=str(temp_path),
            user_id=user_id,
            original_filename=file.filename,
            content_type=content_type
        )

        # Clean up temp file
        try:
            temp_path.unlink()
            logger.info(f"🗑️ [UPLOAD] Cleaned up temp file")
        except Exception as e:
            logger.warning(f"⚠️ [UPLOAD] Failed to clean up temp file: {e}")

        if not success or not public_url:
            raise Exception("Failed to upload file to Supabase Storage")

        logger.info(f"✅ [UPLOAD] File uploaded to Supabase: {public_url}")

        return {
            "url": public_url,
            "filename": file.filename,
            "size_mb": round(file_size_mb, 2),
            "media_type": media_type,
            "storage_path": storage_path,
            "message": f"File uploaded successfully: {file.filename}"
        }

    except Exception as e:
        logger.error(f"❌ [UPLOAD ERROR] Failed to upload file: {e}")
        # Clean up temp file if it exists
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )
