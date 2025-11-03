"""
Configuration management for content_checker_backend
"""

import os
from pathlib import Path
from typing import Dict


class Config:
    """Centralized configuration constants and environment management"""

    # Post checking limits
    RSS_POST_RECENCY_DAYS = 3
    TRACKING_CLEANUP_DAYS = 30
    RSS_FEED_ENTRY_LIMIT = 10

    # HTTP timeouts (seconds)
    DEFAULT_TIMEOUT = 30
    LONG_TIMEOUT = 300
    SHORT_TIMEOUT = 15

    # Retry settings
    DEFAULT_RETRIES = 3
    MAX_RETRIES = 5

    # Environment variables
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    POCKETCASTS_EMAIL = os.getenv('POCKETCASTS_EMAIL', '')
    POCKETCASTS_PASSWORD = os.getenv('POCKETCASTS_PASSWORD', '')
    API_KEY = os.getenv('API_KEY', '')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

    @staticmethod
    def get_default_headers() -> Dict[str, str]:
        """Get default HTTP headers"""
        return {
            'User-Agent': os.getenv(
                'USER_AGENT',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    @staticmethod
    def get_platform_patterns() -> Dict[str, list]:
        """Get URL patterns for platform detection"""
        return {
            'substack': ['/p/', 'substack.com'],
            'medium': ['/@', '/p/', 'medium.com'],
            'youtube': ['/watch?v=', '/shorts/', 'youtube.com', 'youtu.be'],
            'ghost': ['ghost.io', '/ghost/'],
            'linkedin': ['linkedin.com'],
            'twitter': ['twitter.com', 'x.com'],
            'rss_feed': ['/feed', '/rss', '/atom', '.xml', '.rss']
        }

    @staticmethod
    def find_project_root() -> Path:
        """
        Find the project root directory by looking for marker files

        Returns:
            Path to project root directory
        """
        current_path = Path(__file__).resolve()

        # Look for project markers
        markers = ['.git', 'programs', 'README.md', '.env']

        for parent in [current_path] + list(current_path.parents):
            for marker in markers:
                if (parent / marker).exists():
                    return parent

        # Fallback to predefined structure
        return current_path.parent.parent.parent.parent
