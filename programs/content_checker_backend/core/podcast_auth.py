"""
Podcast authentication handler for podcast tracking
Uses direct API calls to PocketCasts unofficial API
"""

import os
import logging
import requests
from typing import Optional, Dict


class PodcastAuth:
    """Handle PocketCasts authentication using direct API"""

    LOGIN_URL = "https://api.pocketcasts.com/user/login"
    HISTORY_URL = "https://api.pocketcasts.com/user/history"
    IN_PROGRESS_URL = "https://api.pocketcasts.com/up_next/list"

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

        # Load credentials from environment
        self.email = os.getenv('POCKETCASTS_EMAIL')
        self.password = os.getenv('POCKETCASTS_PASSWORD')

        # Authentication token
        self.token = None
        self.uuid = None

    def authenticate(self) -> bool:
        """
        Authenticate with PocketCasts

        Returns:
            True if authentication successful, False otherwise
        """
        # Check credentials
        if not self.email or not self.password:
            self.logger.error("PocketCasts credentials not found in environment")
            self.logger.error("Please set POCKETCASTS_EMAIL and POCKETCASTS_PASSWORD")
            return False

        self.logger.info("Authenticating with PocketCasts...")

        try:
            payload = {
                "email": self.email,
                "password": self.password,
                "scope": "webplayer"
            }

            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(self.LOGIN_URL, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            self.token = data.get('token')
            self.uuid = data.get('uuid')

            if not self.token:
                self.logger.error("No token received from PocketCasts")
                return False

            self.logger.info("Successfully authenticated with PocketCasts")
            return True

        except Exception as e:
            self.logger.error(f"Failed to authenticate with PocketCasts: {e}")
            return False

    def get_token(self) -> Optional[str]:
        """
        Get authentication token

        Returns:
            Token string or None if not authenticated
        """
        if not self.token:
            if not self.authenticate():
                return None

        return self.token

    def get_headers(self) -> Dict[str, str]:
        """
        Get authenticated request headers

        Returns:
            Dictionary of headers with authorization token
        """
        token = self.get_token()
        if not token:
            return {}

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def is_authenticated(self) -> bool:
        """Check if we have an authentication token"""
        return self.token is not None
