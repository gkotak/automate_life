"""
Article Processing Routes

Endpoints for processing and managing articles.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import Optional

from app.middleware.auth import verify_api_key

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

        # Process the article
        article_id = processor.process_article(str(request.url))

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
