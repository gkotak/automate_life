"""
YouTube Discovery Service

Shared module for discovering YouTube URLs from various content sources.
Used by both podcast_checker and post_checker to find YouTube videos.
"""

import re
import logging
import requests
from typing import Optional
from bs4 import BeautifulSoup


class YouTubeDiscoveryService:
    """Service for discovering YouTube URLs from web pages"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = requests.Session()

    def extract_youtube_url_from_page(self, page_url: str, content_type: str = 'generic') -> Optional[str]:
        """
        Extract YouTube URL from any web page (article, podcast episode, etc.)

        Args:
            page_url: URL of the page to scrape
            content_type: Type of content ('podcast', 'article', 'generic')

        Returns:
            YouTube URL (video, channel, or playlist) or None
        """
        try:
            self.logger.info(f"🔍 [YOUTUBE DISCOVERY] Checking page for YouTube link: {page_url[:80]}")

            response = self.session.get(page_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Strategy 1: Search HTML links (most reliable)
            youtube_url = self._extract_from_html_links(soup)
            if youtube_url:
                self.logger.info(f"✅ [YOUTUBE] Found in HTML links: {youtube_url[:60]}...")
                return youtube_url

            # Strategy 2: Search embedded iframes
            youtube_url = self._extract_from_iframes(soup)
            if youtube_url:
                self.logger.info(f"✅ [YOUTUBE] Found in iframe: {youtube_url[:60]}...")
                return youtube_url

            # Strategy 3: Look for YouTube links in page text
            youtube_url = self._extract_from_text(soup)
            if youtube_url:
                self.logger.info(f"✅ [YOUTUBE] Found in page text: {youtube_url[:60]}...")
                return youtube_url

            self.logger.info(f"ℹ️ [YOUTUBE] No YouTube link found on page")
            return None

        except Exception as e:
            self.logger.warning(f"⚠️ [YOUTUBE] Error extracting YouTube URL: {e}")
            return None

    def _extract_from_html_links(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract YouTube URL from HTML anchor tags"""
        try:
            youtube_link_pattern = re.compile(r'(youtube\.com|youtu\.be)', re.IGNORECASE)
            links = soup.find_all('a', href=youtube_link_pattern)

            for link in links:
                href = link.get('href', '')
                if href:
                    # Clean and validate URL
                    if not href.startswith('http'):
                        href = f"https://{href}"

                    # Skip YouTube homepage/generic links
                    if href in ['https://youtube.com', 'https://www.youtube.com', 'https://youtu.be']:
                        continue

                    return href

            return None

        except Exception as e:
            self.logger.debug(f"Error in _extract_from_html_links: {e}")
            return None

    def _extract_from_iframes(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract YouTube URL from embedded iframes"""
        try:
            iframes = soup.find_all('iframe')

            for iframe in iframes:
                src = iframe.get('src', '')
                if 'youtube.com' in src or 'youtu.be' in src:
                    # Extract video ID from embed URL
                    match = re.search(r'/embed/([A-Za-z0-9_-]+)', src)
                    if match:
                        video_id = match.group(1)
                        return f"https://www.youtube.com/watch?v={video_id}"

                    # Return the iframe src if it's a valid YouTube URL
                    if src.startswith('http'):
                        return src

            return None

        except Exception as e:
            self.logger.debug(f"Error in _extract_from_iframes: {e}")
            return None

    def _extract_from_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract YouTube URL from page text using regex patterns"""
        try:
            youtube_patterns = [
                r'youtube\.com/watch\?v=([^/\s"\'&]+)',  # Direct video
                r'youtu\.be/([A-Za-z0-9_-]+)',  # Short URL
                r'youtube\.com/channel/([^/\s"\'?&]+)',
                r'youtube\.com/@([^/\s"\'?&]+)',
                r'youtube\.com/c/([^/\s"\'?&]+)',
                r'youtube\.com/user/([^/\s"\'?&]+)',
                r'youtube\.com/playlist\?list=([^/\s"\'&]+)'
            ]

            page_text = soup.get_text()

            for pattern in youtube_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    # Reconstruct full URL
                    if 'youtu.be' in pattern:
                        return f"https://youtu.be/{match.group(1)}"
                    elif 'watch?v=' in pattern:
                        return f"https://www.youtube.com/watch?v={match.group(1)}"
                    elif 'playlist' in pattern:
                        return f"https://www.youtube.com/playlist?list={match.group(1)}"
                    else:
                        url = match.group(0)
                        if not url.startswith('http'):
                            url = f"https://{url}"
                        return url

            return None

        except Exception as e:
            self.logger.debug(f"Error in _extract_from_text: {e}")
            return None

    def get_youtube_url_for_known_source(self, source_url: str, supabase_client) -> Optional[str]:
        """
        Check known_channels table for YouTube URL by source URL

        Args:
            source_url: Content source URL (RSS feed, PocketCasts channel, etc.)
            supabase_client: Supabase client instance

        Returns:
            YouTube URL if found in database, None otherwise
        """
        from core.url_normalizer import URLNormalizer

        try:
            # Normalize URL for consistent lookup
            normalized_url = URLNormalizer.normalize_url(source_url)

            result = supabase_client.table('known_channels')\
                .select('youtube_url, channel_name')\
                .eq('source_url', normalized_url)\
                .eq('is_active', True)\
                .single()\
                .execute()

            if result.data:
                youtube_url = result.data.get('youtube_url')
                channel_name = result.data.get('channel_name', 'Unknown')
                if youtube_url:
                    self.logger.info(f"✅ [KNOWN SOURCE] Found YouTube URL for '{channel_name}': {youtube_url}")
                    return youtube_url

        except Exception as e:
            # Not found is expected for unknown sources
            if 'PGRST116' not in str(e):  # Ignore "no rows returned" error
                self.logger.debug(f"ℹ️ [KNOWN SOURCE] Source not in database: {source_url[:60]}")

        return None
