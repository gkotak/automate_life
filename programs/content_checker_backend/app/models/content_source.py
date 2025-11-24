"""
Pydantic models for content sources (RSS feeds, newsletters, etc.)
"""

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime


class ContentSourceBase(BaseModel):
    """Base model for content source"""
    title: str = Field(..., min_length=1, max_length=255, description="Display name for the source")
    url: HttpUrl = Field(..., description="RSS feed or content URL")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes")
    is_active: bool = Field(True, description="Whether to actively check this source")
    source_type: str = Field(default='newsletter', description="Type of source: 'newsletter' or 'podcast'")


class ContentSourceCreate(ContentSourceBase):
    """Model for creating a new content source"""
    pass


class ContentSourceUpdate(BaseModel):
    """Model for updating an existing content source"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = None
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    source_type: Optional[str] = None


class ContentSource(ContentSourceBase):
    """Full content source model with database fields"""
    id: int
    user_id: str
    organization_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_checked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContentSourceListResponse(BaseModel):
    """Response model for listing content sources"""
    sources: list[ContentSource]
    total: int


class ContentSourceResponse(BaseModel):
    """Response model for single content source"""
    source: ContentSource
    message: Optional[str] = None


class SourceDiscoveryRequest(BaseModel):
    """Request model for discovering source from URL"""
    url: HttpUrl = Field(..., description="URL to discover RSS feed and metadata from")
    source_type: str = Field(default='newsletter', description="Type of source: 'newsletter' or 'podcast'")


class PreviewPost(BaseModel):
    """Preview of a post/episode from the source"""
    title: str
    url: str
    published_date: Optional[str] = None


class SourceDiscoveryResponse(BaseModel):
    """Response model for source discovery"""
    url: str = Field(..., description="Discovered RSS feed URL or original URL")
    title: str = Field(..., description="Extracted title from feed or webpage")
    has_rss: bool = Field(..., description="Whether an RSS feed was found")
    source_type: str = Field(..., description="Type: rss_feed or html_scraping")
    preview_posts: list[PreviewPost] = Field(default_factory=list, description="Last 2 posts/episodes")
