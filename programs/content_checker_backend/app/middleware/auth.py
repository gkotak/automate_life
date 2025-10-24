"""
Authentication middleware for API key validation
"""

from fastapi import HTTPException, status
from typing import Optional
import os


def verify_api_key(api_key: Optional[str] = None):
    """
    Verify API key from request header

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
