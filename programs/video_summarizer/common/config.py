#!/usr/bin/env python3
"""
Centralized configuration management for video summarizer
"""

import os
from typing import Dict, Optional


class Config:
    """Centralized configuration constants and environment management"""

    # File processing limits
    MAX_TRANSCRIPT_CHARS = 150000
    MAX_WHISPER_FILE_SIZE_MB = 25
    RSS_POST_RECENCY_DAYS = 3
    TRACKING_CLEANUP_DAYS = 30

    # HTTP timeouts (seconds)
    DEFAULT_TIMEOUT = 30
    LONG_TIMEOUT = 300
    SHORT_TIMEOUT = 15

    # Retry settings
    DEFAULT_RETRIES = 3
    MAX_RETRIES = 5

    # Claude API settings
    CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
    CLAUDE_MAX_TOKENS = 8192

    # OpenAI Whisper settings
    WHISPER_MODEL = "whisper-1"

    # Processing settings
    RSS_FEED_ENTRY_LIMIT = 10
    HTML_SUMMARY_MAX_LENGTH = 50000

    @staticmethod
    def get_api_keys() -> Dict[str, Optional[str]]:
        """Get all configured API keys"""
        return {
            'openai': os.getenv('OPENAI_API_KEY'),
            'claude': os.getenv('ANTHROPIC_API_KEY'),
        }

    @staticmethod
    def get_auth_credentials() -> Dict[str, Optional[str]]:
        """Get authentication credentials for various platforms"""
        return {
            'substack_email': os.getenv('SUBSTACK_EMAIL'),
            'substack_password': os.getenv('SUBSTACK_PASSWORD'),
            'medium_session_cookie': os.getenv('MEDIUM_SESSION_COOKIE'),
            'patreon_session_cookie': os.getenv('PATREON_SESSION_COOKIE'),
            'newsletter_session_cookies': os.getenv('NEWSLETTER_SESSION_COOKIES'),
        }

    @staticmethod
    def get_supported_audio_formats() -> set:
        """Get supported audio/video formats for transcription"""
        return {
            '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
            '.flac', '.aac', '.ogg', '.wma', '.3gp', '.amr', '.aiff'
        }

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
    def validate_environment() -> Dict[str, bool]:
        """Validate required environment variables and return status"""
        required_for_full_functionality = {
            'OPENAI_API_KEY': bool(os.getenv('OPENAI_API_KEY')),
            'ANTHROPIC_API_KEY': bool(os.getenv('ANTHROPIC_API_KEY')),
        }

        optional_auth = {
            'SUBSTACK_EMAIL': bool(os.getenv('SUBSTACK_EMAIL')),
            'MEDIUM_SESSION_COOKIE': bool(os.getenv('MEDIUM_SESSION_COOKIE')),
            'NEWSLETTER_SESSION_COOKIES': bool(os.getenv('NEWSLETTER_SESSION_COOKIES')),
        }

        return {
            'required': required_for_full_functionality,
            'optional': optional_auth,
            'all_required_present': all(required_for_full_functionality.values()),
            'any_auth_present': any(optional_auth.values())
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
    def get_claude_prompts() -> Dict[str, str]:
        """Get standardized Claude prompts"""
        return {
            'timestamp_validation': """
CRITICAL TIMESTAMP RULES - NEVER EXTRAPOLATE OR GUESS:
1. ONLY include timestamps that you can find EXACT matches for in the provided transcript text
2. If you cannot find the exact text/keywords for an insight in the transcript, DO NOT include a timestamp
3. When you do include timestamps, verify they correspond to actual content in the transcript
4. It's better to have NO timestamp than a wrong timestamp
""",
            'summary_instruction': """
Create a comprehensive summary that includes:
1. Key insights with accurate timestamps (only if verifiable in transcript)
2. Main topics and themes
3. Practical takeaways
4. Interactive elements for engagement
"""
        }