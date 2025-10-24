"""
API routes for podcast checking operations
"""

from fastapi import APIRouter, Header, HTTPException
from typing import Optional

from app.models.podcast import GetPodcastsResponse, CheckPodcastsResponse, PodcastEpisode
from app.services.podcast_checker import PodcastCheckerService
from app.middleware.auth import verify_api_key

router = APIRouter()


@router.get("/podcasts/discovered", response_model=GetPodcastsResponse)
async def get_discovered_podcasts(
    limit: int = 100,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Get discovered podcast episodes from the database

    Args:
        limit: Maximum number of podcasts to return
        x_api_key: API key for authentication

    Returns:
        List of discovered podcast episodes
    """
    # Verify API key
    verify_api_key(x_api_key)

    # Get podcasts from service
    service = PodcastCheckerService()
    podcasts = await service.get_discovered_podcasts(limit=limit)

    return GetPodcastsResponse(
        podcasts=[PodcastEpisode(**p) for p in podcasts],
        total=len(podcasts)
    )


@router.post("/podcasts/check", response_model=CheckPodcastsResponse)
async def check_podcasts(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Check PocketCasts for new podcast episodes

    Args:
        x_api_key: API key for authentication

    Returns:
        Results of the podcast check
    """
    # Verify API key
    verify_api_key(x_api_key)

    # Run podcast check
    service = PodcastCheckerService()
    result = await service.check_for_new_podcasts()

    return CheckPodcastsResponse(
        message=result["message"],
        new_podcasts_found=result["new_podcasts_found"],
        total_episodes_checked=result["total_episodes_checked"],
        newly_discovered_ids=result.get("newly_discovered_ids", [])
    )
