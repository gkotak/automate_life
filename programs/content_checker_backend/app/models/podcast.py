"""
Pydantic models for podcast-related API requests/responses
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class PodcastEpisode(BaseModel):
    """Podcast episode data model"""
    id: Optional[str] = None
    episode_title: str
    podcast_title: str
    episode_url: str
    podcast_video_url: Optional[str] = None
    progress_percent: Optional[float] = None
    published_date: Optional[str] = None
    found_at: Optional[str] = None
    status: str = "discovered"
    is_new: bool = Field(default=False, description="Whether this is a newly discovered episode")
    duration_seconds: Optional[int] = Field(default=None, description="Episode duration in seconds")


class GetPodcastsResponse(BaseModel):
    """Response model for GET /api/podcasts/discovered"""
    podcasts: List[PodcastEpisode]
    total: int


class CheckPodcastsResponse(BaseModel):
    """Response model for POST /api/podcasts/check"""
    message: str
    new_podcasts_found: int
    total_episodes_checked: int
    newly_discovered_ids: List[str] = Field(default_factory=list, description="IDs of newly discovered episodes")
