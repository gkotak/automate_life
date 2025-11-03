"""
API routes for content source management (RSS feeds, newsletters, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging

from app.models.content_source import (
    ContentSourceCreate,
    ContentSourceUpdate,
    ContentSource,
    ContentSourceListResponse,
    ContentSourceResponse
)
from app.middleware.auth import verify_supabase_jwt
from core.config import Config

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sources", response_model=ContentSourceListResponse)
async def list_content_sources(
    user_id: str = Depends(verify_supabase_jwt),
    include_inactive: bool = False
):
    """
    List all content sources for the authenticated user

    Args:
        user_id: User ID extracted from JWT token
        include_inactive: Whether to include inactive sources

    Returns:
        List of content sources
    """
    try:
        supabase = Config.get_supabase_client()

        # Build query
        query = supabase.table('content_sources').select('*').eq('user_id', user_id)

        # Filter by active status if requested
        if not include_inactive:
            query = query.eq('is_active', True)

        # Order by created_at descending
        query = query.order('created_at', desc=True)

        result = query.execute()

        sources = [ContentSource(**source) for source in result.data]

        logger.info(f"Listed {len(sources)} content sources for user: {user_id}")

        return ContentSourceListResponse(
            sources=sources,
            total=len(sources)
        )

    except Exception as e:
        logger.error(f"Error listing content sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list content sources: {str(e)}"
        )


@router.get("/sources/{source_id}", response_model=ContentSourceResponse)
async def get_content_source(
    source_id: int,
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Get a specific content source

    Args:
        source_id: ID of the content source
        user_id: User ID extracted from JWT token

    Returns:
        Content source details
    """
    try:
        supabase = Config.get_supabase_client()

        result = supabase.table('content_sources').select('*').eq(
            'id', source_id
        ).eq(
            'user_id', user_id
        ).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content source with ID {source_id} not found"
            )

        source = ContentSource(**result.data[0])

        logger.info(f"Retrieved content source {source_id} for user: {user_id}")

        return ContentSourceResponse(source=source)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting content source {source_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get content source: {str(e)}"
        )


@router.post("/sources", response_model=ContentSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_content_source(
    source: ContentSourceCreate,
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Create a new content source

    Args:
        source: Content source data
        user_id: User ID extracted from JWT token

    Returns:
        Created content source
    """
    try:
        supabase = Config.get_supabase_client()

        # Prepare data for insertion
        source_data = {
            'user_id': user_id,
            'name': source.name,
            'url': str(source.url),
            'description': source.description,
            'is_active': source.is_active,
            'source_type': source.source_type or 'rss_feed'
        }

        result = supabase.table('content_sources').insert(source_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create content source"
            )

        created_source = ContentSource(**result.data[0])

        logger.info(f"Created content source {created_source.id} for user: {user_id}")

        return ContentSourceResponse(
            source=created_source,
            message="Content source created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating content source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create content source: {str(e)}"
        )


@router.patch("/sources/{source_id}", response_model=ContentSourceResponse)
async def update_content_source(
    source_id: int,
    updates: ContentSourceUpdate,
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Update an existing content source

    Args:
        source_id: ID of the content source
        updates: Fields to update
        user_id: User ID extracted from JWT token

    Returns:
        Updated content source
    """
    try:
        supabase = Config.get_supabase_client()

        # Check if source exists and belongs to user
        existing = supabase.table('content_sources').select('*').eq(
            'id', source_id
        ).eq(
            'user_id', user_id
        ).execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content source with ID {source_id} not found"
            )

        # Prepare update data (only include fields that were provided)
        update_data = {}
        if updates.name is not None:
            update_data['name'] = updates.name
        if updates.url is not None:
            update_data['url'] = str(updates.url)
        if updates.description is not None:
            update_data['description'] = updates.description
        if updates.is_active is not None:
            update_data['is_active'] = updates.is_active
        if updates.source_type is not None:
            update_data['source_type'] = updates.source_type

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        # Add updated_at timestamp
        update_data['updated_at'] = 'now()'

        result = supabase.table('content_sources').update(update_data).eq(
            'id', source_id
        ).eq(
            'user_id', user_id
        ).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update content source"
            )

        updated_source = ContentSource(**result.data[0])

        logger.info(f"Updated content source {source_id} for user: {user_id}")

        return ContentSourceResponse(
            source=updated_source,
            message="Content source updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating content source {source_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update content source: {str(e)}"
        )


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content_source(
    source_id: int,
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Delete a content source

    Args:
        source_id: ID of the content source
        user_id: User ID extracted from JWT token

    Returns:
        No content on success
    """
    try:
        supabase = Config.get_supabase_client()

        # Check if source exists and belongs to user
        existing = supabase.table('content_sources').select('id').eq(
            'id', source_id
        ).eq(
            'user_id', user_id
        ).execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content source with ID {source_id} not found"
            )

        # Delete the source
        supabase.table('content_sources').delete().eq(
            'id', source_id
        ).eq(
            'user_id', user_id
        ).execute()

        logger.info(f"Deleted content source {source_id} for user: {user_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting content source {source_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete content source: {str(e)}"
        )
