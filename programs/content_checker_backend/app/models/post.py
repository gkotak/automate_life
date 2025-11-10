"""
Pydantic models for post/article API responses
"""

from pydantic import BaseModel
from typing import List, Optional


class Post(BaseModel):
    """Model for a discovered post/article"""
    id: str
    title: str
    url: str
    content_type: str
    channel_title: Optional[str] = None
    channel_url: Optional[str] = None
    platform: str
    source_feed: Optional[str] = None
    published_date: Optional[str] = None
    found_at: str
    status: str
    is_new: bool = False


class CheckPostsResponse(BaseModel):
    """Response model for POST /api/posts/check"""
    message: str
    new_posts_found: int
    total_sources_checked: int
    newly_discovered_ids: List[str]


class GetPostsResponse(BaseModel):
    """Response model for GET /api/posts/discovered"""
    posts: List[Post]
    total: int
