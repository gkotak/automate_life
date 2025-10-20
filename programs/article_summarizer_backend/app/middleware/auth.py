"""
Authentication Middleware

Provides API key authentication for protected endpoints.
"""

import os
import logging
from fastapi import Header, HTTPException, status
from typing import Optional

logger = logging.getLogger(__name__)


async def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify API key from Authorization header

    Args:
        authorization: Authorization header value (Bearer TOKEN)

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is missing or invalid
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
        logger.warning(f"🔒 Invalid Authorization format: {authorization[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Get expected API key from environment
    expected_api_key = os.getenv('API_KEY')
    if not expected_api_key:
        logger.error("❌ API_KEY environment variable not set!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error"
        )

    # Validate token
    if token != expected_api_key:
        logger.warning(f"🔒 Invalid API key attempt: {token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("✅ API key validated successfully")
    return token
