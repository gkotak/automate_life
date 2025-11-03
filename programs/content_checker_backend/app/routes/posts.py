"""
API routes for post checking operations
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.models.post import GetPostsResponse, CheckPostsResponse, Post
from app.services.post_checker import PostCheckerService
from app.middleware.auth import verify_supabase_jwt

router = APIRouter()


@router.get("/posts/discovered", response_model=GetPostsResponse)
async def get_discovered_posts(
    limit: int = 200,
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Get discovered posts/articles from the database for the authenticated user

    Args:
        limit: Maximum number of posts to return
        user_id: User ID extracted from JWT token

    Returns:
        List of discovered posts for this user
    """
    # Get posts from service (filtered by user_id)
    service = PostCheckerService()
    posts = await service.get_discovered_posts(user_id=user_id, limit=limit)

    return GetPostsResponse(
        posts=[Post(**p) for p in posts],
        total=len(posts)
    )


@router.post("/posts/check", response_model=CheckPostsResponse)
async def check_posts(
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Check content_sources for new posts/articles for the authenticated user

    Args:
        user_id: User ID extracted from JWT token

    Returns:
        Results of the post check
    """
    # Run post check for this user
    service = PostCheckerService()
    result = await service.check_for_new_posts(user_id=user_id)

    return CheckPostsResponse(
        message=result["message"],
        new_posts_found=result["new_posts_found"],
        total_sources_checked=result["total_sources_checked"],
        newly_discovered_ids=result.get("newly_discovered_ids", [])
    )
