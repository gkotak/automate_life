"""
API routes for podcast history checking operations
"""

from fastapi import APIRouter, Header, HTTPException
from typing import Optional

from app.models.podcast import GetPodcastsResponse, CheckPodcastsResponse, PodcastEpisode
from app.services.podcast_history_checker import PodcastHistoryCheckerService
from app.middleware.auth import verify_api_key

router = APIRouter()


@router.get("/podcast-history/discovered", response_model=GetPodcastsResponse)
async def get_discovered_podcast_history(
    limit: int = 100,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Get discovered podcast episodes from listening history

    Args:
        limit: Maximum number of podcasts to return
        x_api_key: API key for authentication

    Returns:
        List of discovered podcast episodes from history
    """
    # Verify API key
    verify_api_key(x_api_key)

    # Get podcasts from service
    service = PodcastHistoryCheckerService()
    podcasts = await service.get_discovered_podcasts(limit=limit)

    return GetPodcastsResponse(
        podcasts=[PodcastEpisode(**p) for p in podcasts],
        total=len(podcasts)
    )


@router.post("/podcast-history/check", response_model=CheckPodcastsResponse)
async def check_podcast_history(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Check PocketCasts for new podcast episodes from listening history

    Args:
        x_api_key: API key for authentication

    Returns:
        Results of the podcast history check
    """
    # Verify API key
    verify_api_key(x_api_key)

    # Run podcast history check
    service = PodcastHistoryCheckerService()
    result = await service.check_for_new_podcasts()

    return CheckPodcastsResponse(
        message=result["message"],
        new_podcasts_found=result["new_podcasts_found"],
        total_episodes_checked=result["total_episodes_checked"],
        newly_discovered_ids=result.get("newly_discovered_ids", [])
    )
