"""
Article Reprocessing Routes

Endpoints for partial reprocessing of existing articles:
- Regenerate AI summary only
- Regenerate themed insights (private articles)
- Regenerate embedding
- Get article reprocess info (what operations are available)
"""

import logging
import asyncio
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.middleware.auth import get_supabase_admin

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_available_operations(info: dict, is_private: bool) -> List[str]:
    """Get list of available reprocessing operations based on article state."""
    ops = []
    # Phase 1 operations
    if info.get('can_regen_summary', False):
        ops.append('ai_summary')
    if is_private and info.get('can_regen_themed_insights', False):
        ops.append('themed_insights')
    if info.get('can_regen_embedding', True):
        ops.append('embedding')
    # Phase 2 operations (require stored media)
    if info.get('can_regen_video_frames', False):
        ops.append('video_frames')
    if info.get('can_regen_transcript', False):
        ops.append('transcript')
    return ops


def _get_unavailable_operations(info: dict, is_private: bool) -> dict:
    """Get mapping of unavailable operations to their reasons."""
    unavailable = {}
    if not info.get('can_regen_summary', False):
        unavailable['ai_summary'] = info.get('summary_unavailable_reason', 'Not available')
    if not is_private:
        unavailable['themed_insights'] = 'Only available for private articles'
    # Phase 2: video_frames and transcript availability
    if not info.get('can_regen_video_frames', False):
        unavailable['video_frames'] = info.get('video_frames_unavailable_reason', 'Not available')
    if not info.get('can_regen_transcript', False):
        unavailable['transcript'] = info.get('transcript_unavailable_reason', 'Not available')
    return unavailable


class ReprocessRequest(BaseModel):
    """Request model for reprocessing an article"""
    article_id: int
    is_private: bool = False
    steps: List[str]  # List of steps: ["ai_summary", "themed_insights", "embedding", "video_frames", "transcript"]


class ReprocessInfoResponse(BaseModel):
    """Response model for article reprocess info"""
    article_id: int
    title: str
    url: str
    is_private: bool
    has_transcript: bool
    has_video_frames: bool
    has_embedding: bool
    has_themed_insights: bool
    content_source: str
    available_operations: List[str]
    unavailable_operations: dict  # Maps operation to reason why unavailable
    # Phase 2: Media storage info
    has_stored_media: Optional[bool] = None
    media_storage_bucket: Optional[str] = None
    media_size_mb: Optional[float] = None
    media_days_remaining: Optional[int] = None
    media_is_permanent: Optional[bool] = None


def get_user_friendly_error_message(error: Exception) -> str:
    """Convert an exception to a user-friendly error message."""
    error_str = str(error).lower()
    error_type = type(error).__name__

    if 'rate_limit' in error_str or 'ratelimit' in error_str:
        return "The AI service is temporarily busy. Please wait a moment and try again."

    if 'api_key' in error_str or 'unauthorized' in error_str:
        return "There was an authentication issue with the AI service. Please try again later."

    if 'timeout' in error_str or 'timed out' in error_str:
        return "The request timed out. Please try again."

    if 'database' in error_str or 'supabase' in error_str:
        return "There was a database error. Please try again later."

    logger.error(f"Unhandled error type for user message: {error_type}: {error}")
    return f"Sorry, there was an error: {str(error)}"


@router.get("/info")
async def get_reprocess_info(
    article_id: int,
    is_private: bool = False,
    token: Optional[str] = None
):
    """
    Get information about what reprocessing operations are available for an article.

    This helps the UI show which checkboxes should be enabled/disabled and why.

    Args:
        article_id: ID of the article
        is_private: Whether this is a private article
        token: Supabase JWT token

    Returns:
        ReprocessInfoResponse with available operations
    """
    from app.services.article_processor import ArticleProcessor

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    try:
        supabase = get_supabase_admin()
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        user_id = user_response.user.id
        logger.info(f"🔍 Getting reprocess info for article {article_id} (private={is_private}, user={user_id})")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verifying token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    # Get article info using processor helper
    processor = ArticleProcessor(event_emitter=None)
    article_type = 'private' if is_private else 'public'
    info = processor.get_article_reprocess_info(article_id, article_type)

    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article {article_id} not found"
        )

    if 'error' in info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=info['error']
        )

    # Transform response to match frontend expectations
    return {
        "article_id": info['id'],
        "title": info['title'],
        "url": info['url'],
        "is_private": is_private,
        "has_transcript": info['has_transcript'],
        "has_video_frames": info['has_video_frames'],
        "has_embedding": info['has_embedding'],
        "has_themed_insights": info.get('themed_insights_count', 0) > 0,
        "content_source": info['content_source'],
        "available_operations": _get_available_operations(info, is_private),
        "unavailable_operations": _get_unavailable_operations(info, is_private),
        # Phase 2: Media storage info
        "has_stored_media": info.get('has_stored_media', False),
        "media_storage_bucket": info.get('media_storage_bucket'),
        "media_size_mb": info.get('media_size_mb'),
        "media_days_remaining": info.get('media_days_remaining'),
        "media_is_permanent": info.get('media_is_permanent', False)
    }


@router.post("/run")
async def run_reprocess(
    request: ReprocessRequest,
    token: Optional[str] = None
):
    """
    Run partial reprocessing of an article with SSE streaming.

    Executes only the specified steps (ai_summary, themed_insights, embedding).
    Streams progress events in real-time.

    Args:
        request: ReprocessRequest with article_id, is_private, and steps
        token: Supabase JWT token

    Returns:
        EventSourceResponse with real-time processing events
    """
    from app.services.article_processor import ArticleProcessor

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    try:
        supabase = get_supabase_admin()
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        user_id = user_response.user.id
        logger.info(f"🔄 Starting reprocess for article {request.article_id} (private={request.is_private}, steps={request.steps}, user={user_id})")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verifying token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    # Validate steps (Phase 1 + Phase 2)
    valid_steps = {"ai_summary", "themed_insights", "embedding", "video_frames", "transcript"}
    invalid_steps = set(request.steps) - valid_steps
    if invalid_steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid steps: {invalid_steps}. Valid steps: {valid_steps}"
        )

    if not request.steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one step must be specified"
        )

    async def reprocess_and_stream():
        """Generator that runs reprocessing and yields SSE events."""
        import time

        start_time = time.time()
        event_queue = asyncio.Queue()

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
                "data": json.dumps({
                    "article_id": request.article_id,
                    "is_private": request.is_private,
                    "steps": request.steps,
                    "elapsed": elapsed()
                })
            }
            await asyncio.sleep(0)

            # Initialize processor
            processor = ArticleProcessor(event_emitter=None)

            # Create progress callback that adds events to queue
            async def progress_callback(event_type: str, data: dict):
                await event_queue.put({
                    "event": event_type,
                    "data": {**data, "elapsed": elapsed()}
                })

            # Run reprocessing in background task with callback
            reprocess_error = None
            reprocess_result = None

            async def run_reprocess():
                nonlocal reprocess_error, reprocess_result
                try:
                    article_type = 'private' if request.is_private else 'public'
                    reprocess_result = await processor.reprocess_article(
                        article_id=request.article_id,
                        article_type=article_type,
                        steps=request.steps,
                        user_id=user_id,
                        progress_callback=progress_callback
                    )
                    await event_queue.put(None)  # Signal completion
                except Exception as e:
                    reprocess_error = e
                    await event_queue.put(None)

            # Start reprocessing task
            reprocess_task = asyncio.create_task(run_reprocess())

            # Stream events as they arrive
            while True:
                event = await event_queue.get()
                if event is None:
                    break

                # Map internal event types to SSE events
                event_type = event["event"]
                data = event["data"]

                # Map progress callback events to frontend-friendly events
                if event_type == 'article_loaded':
                    yield {
                        "event": "article_loaded",
                        "data": json.dumps(data)
                    }
                elif event_type.endswith('_start'):
                    step_name = event_type.replace('_start', '')
                    yield {
                        "event": "step_start",
                        "data": json.dumps({
                            "step": step_name,
                            "message": f"Processing {step_name.replace('_', ' ')}...",
                            **data
                        })
                    }
                elif event_type.endswith('_complete'):
                    step_name = event_type.replace('_complete', '')
                    yield {
                        "event": "step_complete",
                        "data": json.dumps({
                            "step": step_name,
                            "success": True,
                            **data
                        })
                    }
                elif event_type.endswith('_error'):
                    step_name = event_type.replace('_error', '')
                    yield {
                        "event": "step_error",
                        "data": json.dumps({
                            "step": step_name,
                            "success": False,
                            **data
                        })
                    }
                elif event_type.endswith('_skipped'):
                    step_name = event_type.replace('_skipped', '')
                    yield {
                        "event": "step_skipped",
                        "data": json.dumps({
                            "step": step_name,
                            **data
                        })
                    }
                else:
                    # Pass through unknown events
                    yield {
                        "event": event_type,
                        "data": json.dumps(data)
                    }

                await asyncio.sleep(0)

            # Wait for task to complete
            await reprocess_task

            # Handle errors
            if reprocess_error:
                raise reprocess_error

            # Calculate overall success from results
            results = reprocess_result or {}
            all_success = all(r.get("success", False) for r in results.values()) if results else False
            any_success = any(r.get("success", False) for r in results.values()) if results else False

            # Build article URL
            article_url = f"/private-article/{request.article_id}" if request.is_private else f"/article/{request.article_id}"

            # Completion event
            yield {
                "event": "completed",
                "data": json.dumps({
                    "article_id": request.article_id,
                    "url": article_url,
                    "all_success": all_success,
                    "any_success": any_success,
                    "results": {
                        k: {
                            "success": v.get("success", False),
                            "message": v.get("message", v.get("error", ""))
                        }
                        for k, v in results.items()
                    },
                    "elapsed": elapsed()
                })
            }

            logger.info(f"✅ Reprocessing completed for article {request.article_id} (all_success={all_success})")

        except Exception as e:
            logger.error(f"❌ Reprocessing failed: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": get_user_friendly_error_message(e),
                    "elapsed": elapsed()
                })
            }

    return EventSourceResponse(
        reprocess_and_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/list")
async def list_articles_for_reprocess(
    is_private: bool = False,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    token: Optional[str] = None
):
    """
    List articles available for reprocessing.

    Returns a paginated list of articles with basic info for the reprocess UI.

    Args:
        is_private: Whether to list private articles
        search: Optional search query for title
        limit: Maximum number of results
        offset: Offset for pagination
        token: Supabase JWT token

    Returns:
        List of articles with basic info
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    try:
        supabase = get_supabase_admin()
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        user_id = user_response.user.id
        logger.info(f"📋 Listing articles for reprocess (private={is_private}, user={user_id})")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error verifying token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    try:
        table_name = 'private_articles' if is_private else 'articles'

        # Build query
        query = supabase.table(table_name).select(
            'id, title, url, content_source, created_at, updated_at'
        )

        # For private articles, filter by user's organization
        if is_private:
            # Get user's organization
            user_data = supabase.table('users').select('organization_id').eq('id', user_id).single().execute()
            organization_id = user_data.data.get('organization_id') if user_data.data else None

            if organization_id:
                query = query.eq('organization_id', organization_id)
            else:
                # User has no org, return empty list
                return {"articles": [], "total": 0, "limit": limit, "offset": offset}

        # Add search filter if provided
        if search:
            query = query.ilike('title', f'%{search}%')

        # Order by most recently updated
        query = query.order('updated_at', desc=True)

        # Get total count first
        count_query = supabase.table(table_name).select('id', count='exact')
        if is_private and organization_id:
            count_query = count_query.eq('organization_id', organization_id)
        if search:
            count_query = count_query.ilike('title', f'%{search}%')
        count_result = count_query.execute()
        total = count_result.count if hasattr(count_result, 'count') else len(count_result.data)

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        result = query.execute()

        articles = []
        for article in result.data:
            articles.append({
                "id": article['id'],
                "title": article.get('title', 'Untitled'),
                "url": article.get('url', ''),
                "content_source": article.get('content_source', 'unknown'),
                "created_at": article.get('created_at'),
                "updated_at": article.get('updated_at')
            })

        return {
            "articles": articles,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"❌ Error listing articles: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list articles: {str(e)}"
        )
