"""
Authentication Setup Routes

Endpoints for configuring browser session authentication.
"""

import os
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Optional

from app.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


class UploadCookiesRequest(BaseModel):
    """Request model for uploading cookies"""
    platform: str
    cookies: Dict[str, str]


class UploadCookiesResponse(BaseModel):
    """Response model for cookie upload"""
    status: str
    message: str
    platform: str


class AuthStatusResponse(BaseModel):
    """Response model for authentication status"""
    storage_configured: bool
    storage_path: Optional[str]
    platforms: list


@router.post("/upload-cookies", response_model=UploadCookiesResponse)
async def upload_cookies(
    request: UploadCookiesRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Upload cookies from desktop Chrome extraction

    This endpoint receives cookies extracted from Chrome on your desktop
    and saves them to the storage_state.json file for Playwright to use.

    Args:
        request: UploadCookiesRequest with platform and cookies
        api_key: Validated API key from middleware

    Returns:
        UploadCookiesResponse with status
    """
    logger.info(f"🍪 Uploading cookies for platform: {request.platform}")

    try:
        storage_dir = os.getenv('STORAGE_DIR', '/app/storage')
        storage_state_file = os.path.join(storage_dir, 'storage_state.json')

        # Ensure storage directory exists
        os.makedirs(storage_dir, exist_ok=True)

        # Load existing storage state or create new
        if os.path.exists(storage_state_file):
            with open(storage_state_file, 'r') as f:
                storage_state = json.load(f)
        else:
            storage_state = {"cookies": [], "origins": []}

        # Convert cookies dict to Playwright format
        playwright_cookies = []
        for name, value in request.cookies.items():
            cookie = {
                "name": name,
                "value": value,
                "domain": f".{request.platform}",
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "Lax"
            }
            playwright_cookies.append(cookie)

        # Add/update cookies in storage state
        # Remove old cookies for this platform
        storage_state["cookies"] = [
            c for c in storage_state["cookies"]
            if request.platform not in c.get("domain", "")
        ]

        # Add new cookies
        storage_state["cookies"].extend(playwright_cookies)

        # Save updated storage state
        with open(storage_state_file, 'w') as f:
            json.dump(storage_state, f, indent=2)

        logger.info(f"✅ Saved {len(playwright_cookies)} cookies for {request.platform}")

        return UploadCookiesResponse(
            status="success",
            message=f"Uploaded {len(playwright_cookies)} cookies",
            platform=request.platform
        )

    except Exception as e:
        logger.error(f"❌ Failed to upload cookies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload cookies: {str(e)}"
        )


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(api_key: str = Depends(verify_api_key)):
    """
    Check authentication configuration status

    Returns information about configured browser sessions and platforms.

    Args:
        api_key: Validated API key from middleware

    Returns:
        AuthStatusResponse with configuration details
    """
    try:
        storage_dir = os.getenv('STORAGE_DIR', '/app/storage')
        storage_state_file = os.path.join(storage_dir, 'storage_state.json')

        if not os.path.exists(storage_state_file):
            return AuthStatusResponse(
                storage_configured=False,
                storage_path=storage_state_file,
                platforms=[]
            )

        # Load storage state and extract platforms
        with open(storage_state_file, 'r') as f:
            storage_state = json.load(f)

        # Extract unique platforms from cookies
        platforms = list(set([
            cookie.get("domain", "").lstrip(".")
            for cookie in storage_state.get("cookies", [])
            if cookie.get("domain")
        ]))

        return AuthStatusResponse(
            storage_configured=True,
            storage_path=storage_state_file,
            platforms=sorted(platforms)
        )

    except Exception as e:
        logger.error(f"❌ Failed to get auth status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get auth status: {str(e)}"
        )


@router.delete("/clear-session")
async def clear_session(api_key: str = Depends(verify_api_key)):
    """
    Clear all stored browser sessions

    Use this to reset authentication and force re-login.

    Args:
        api_key: Validated API key from middleware

    Returns:
        Success message
    """
    try:
        storage_dir = os.getenv('STORAGE_DIR', '/app/storage')
        storage_state_file = os.path.join(storage_dir, 'storage_state.json')

        if os.path.exists(storage_state_file):
            os.remove(storage_state_file)
            logger.info("🗑️ Cleared browser session storage")

        return {
            "status": "success",
            "message": "Browser session cleared"
        }

    except Exception as e:
        logger.error(f"❌ Failed to clear session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear session: {str(e)}"
        )
