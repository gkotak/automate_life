"""
Authentication middleware for Supabase JWT validation
Uses Supabase client library to verify tokens.
"""

from fastapi import HTTPException, status, Header
from typing import Optional
import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Initialize Supabase client with service role key for admin operations
_supabase_client: Optional[Client] = None


def get_supabase_admin() -> Client:
    """Get or create Supabase admin client (singleton)"""
    global _supabase_client

    if _supabase_client is None:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Using the service role key

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase admin client initialized")

    return _supabase_client


async def verify_supabase_jwt(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify Supabase JWT token from Authorization header using Supabase client

    Args:
        authorization: Authorization header value (Bearer TOKEN)

    Returns:
        The user_id extracted from the JWT token

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        logger.warning("🔒 API request without Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"🔒 Invalid Authorization format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Verify token using Supabase client
    try:
        supabase = get_supabase_admin()

        # Get user from token
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            logger.warning("🔒 Invalid token - no user found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = user_response.user.id
        logger.debug(f"✅ JWT validated successfully for user: {user_id}")
        return user_id

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Error verifying JWT: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Keep old function for backward compatibility
def verify_api_key(api_key: Optional[str] = None):
    """
    DEPRECATED: Legacy API key validation

    This function is kept for backward compatibility with podcast checking
    which is still single-user and doesn't need JWT auth.

    Args:
        api_key: API key from X-API-Key header

    Raises:
        HTTPException: If API key is invalid or missing
    """
    required_api_key = os.getenv('API_KEY', '').strip()

    # If no API key is configured, allow all requests (for local development)
    if not required_api_key:
        return

    # If API key is configured, require it
    if not api_key or api_key != required_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
