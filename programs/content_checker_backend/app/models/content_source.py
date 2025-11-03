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


class ContentSourceCreate(ContentSourceBase):
    """Model for creating a new content source"""
    pass


class ContentSourceUpdate(BaseModel):
    """Model for updating an existing content source"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = None
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class ContentSource(ContentSourceBase):
    """Full content source model with database fields"""
    id: int
    user_id: str
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
