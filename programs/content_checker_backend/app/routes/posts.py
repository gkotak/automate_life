"""
API routes for post checking operations
"""

from fastapi import APIRouter, Header, HTTPException
from typing import Optional

from app.models.post import GetPostsResponse, CheckPostsResponse, Post
from app.services.post_checker import PostCheckerService
from app.middleware.auth import verify_api_key

router = APIRouter()


@router.get("/posts/discovered", response_model=GetPostsResponse)
async def get_discovered_posts(
    limit: int = 200,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Get discovered posts/articles from the database

    Args:
        limit: Maximum number of posts to return
        x_api_key: API key for authentication

    Returns:
        List of discovered posts
    """
    # Verify API key
    verify_api_key(x_api_key)

    # Get posts from service
    service = PostCheckerService()
    posts = await service.get_discovered_posts(limit=limit)

    return GetPostsResponse(
        posts=[Post(**p) for p in posts],
        total=len(posts)
    )


@router.post("/posts/check", response_model=CheckPostsResponse)
async def check_posts(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Check content_sources for new posts/articles

    Args:
        x_api_key: API key for authentication

    Returns:
        Results of the post check
    """
    # Verify API key
    verify_api_key(x_api_key)

    # Run post check
    service = PostCheckerService()
    result = await service.check_for_new_posts()

    return CheckPostsResponse(
        message=result["message"],
        new_posts_found=result["new_posts_found"],
        total_sources_checked=result["total_sources_checked"],
        newly_discovered_ids=result.get("newly_discovered_ids", [])
    )
