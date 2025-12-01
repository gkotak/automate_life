"""
API routes for content source management (RSS feeds, newsletters, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging
import os
from supabase import create_client, Client

from app.models.content_source import (
    ContentSourceCreate,
    ContentSourceUpdate,
    ContentSource,
    ContentSourceListResponse,
    ContentSourceResponse,
    SourceDiscoveryRequest,
    SourceDiscoveryResponse,
    PreviewPost
)
from app.middleware.auth import verify_supabase_jwt

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize Supabase client
_supabase_client: Optional[Client] = None

def get_supabase() -> Client:
    """Get or create Supabase client (singleton)"""
    global _supabase_client

    if _supabase_client is None:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase client initialized for sources routes")

    return _supabase_client


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
        supabase = get_supabase()

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
        supabase = get_supabase()

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
        supabase = get_supabase()

        # Prepare data for insertion (organization_id removed - scoped by user_id only)
        source_data = {
            'user_id': user_id,
            'title': source.title,
            'url': str(source.url),
            'notes': source.notes,
            'is_active': source.is_active,
            'source_type': source.source_type
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
        supabase = get_supabase()

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
        if updates.title is not None:
            update_data['title'] = updates.title
        if updates.url is not None:
            update_data['url'] = str(updates.url)
        if updates.notes is not None:
            update_data['notes'] = updates.notes
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
        supabase = get_supabase()

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


@router.post("/sources/discover", response_model=SourceDiscoveryResponse)
async def discover_source(
    request: SourceDiscoveryRequest,
    user_id: str = Depends(verify_supabase_jwt)
):
    """
    Discover RSS feed and metadata from a URL

    Tries to:
    1. Check if URL is already an RSS feed
    2. Auto-discover RSS feed from HTML page
    3. Fall back to HTML scraping if no RSS found
    4. Extract title and preview posts

    Args:
        request: URL to discover
        user_id: User ID extracted from JWT token

    Returns:
        Discovered source information with preview posts
    """
    try:
        from app.services.post_checker import PostCheckerService

        url = str(request.url)
        logger.info(f"Discovering source from URL: {url}")

        # Initialize post checker service (reuse existing discovery logic)
        post_checker = PostCheckerService()

        # Try RSS discovery first
        discovered_feed_url = None
        has_rss = False
        feed_type = "html_scraping"

        # Fetch the URL
        response = post_checker.session.get(url, timeout=10)
        response.raise_for_status()

        # Check if it's already an RSS feed
        if post_checker._is_rss_feed(url, response):
            discovered_feed_url = url
            has_rss = True
            feed_type = "rss_feed"
            logger.info(f"URL is already an RSS feed: {url}")
        else:
            # Try to discover RSS feed from HTML
            discovered_feed_url = post_checker._discover_rss_feed(url, response)
            if discovered_feed_url:
                has_rss = True
                feed_type = "rss_feed"
                logger.info(f"Discovered RSS feed: {discovered_feed_url}")

        # Use discovered feed URL or fall back to original URL
        final_url = discovered_feed_url if discovered_feed_url else url

        # Extract posts to get title and preview
        # Pass user's intended source_type ('newsletter' or 'podcast')
        platform_type = post_checker._detect_platform_type(final_url)
        posts = post_checker._extract_posts_from_feed(final_url, platform_type, user_source_type=request.source_type)

        # Extract title from posts or fetch from page
        title = "Unknown Source"
        if posts and len(posts) > 0:
            # Get channel title from first post if available
            title = posts[0].get('channel_title', 'Unknown Source')

        # If still no title, try to extract from HTML
        if title == "Unknown Source":
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            # Also try og:title meta tag
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title.get('content').strip()

        # Create preview posts (last 2)
        preview_posts = []
        for post in posts[:2]:
            preview_posts.append(PreviewPost(
                title=post['title'],
                url=post['url'],
                published_date=post['published'].isoformat() if post.get('published') else None
            ))

        logger.info(f"Successfully discovered source: {title} ({len(preview_posts)} preview posts)")

        return SourceDiscoveryResponse(
            url=final_url,
            title=title,
            has_rss=has_rss,
            source_type=request.source_type,  # Return user's intended source_type, not feed_type
            preview_posts=preview_posts
        )

    except Exception as e:
        logger.error(f"Error discovering source from {request.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover source: {str(e)}"
        )
