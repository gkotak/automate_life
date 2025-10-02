"""
Content Type Detection Module

Determines if content has embedded video, embedded audio, or is text-only.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

@dataclass
class ContentType:
    """Represents the detected content type"""
    has_embedded_video: bool = False
    has_embedded_audio: bool = False
    is_text_only: bool = True
    video_urls: List[Dict] = None
    audio_urls: List[Dict] = None

    def __post_init__(self):
        if self.video_urls is None:
            self.video_urls = []
        if self.audio_urls is None:
            self.audio_urls = []

class ContentTypeDetector:
    """Detects whether content has embedded video, audio, or is text-only"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def detect_content_type(self, soup: BeautifulSoup, url: str) -> ContentType:
        """
        Main method to detect content type

        Args:
            soup: BeautifulSoup object of the page
            url: Original URL for context

        Returns:
            ContentType object with detection results
        """
        self.logger.info("🔍 [CONTENT DETECTION] Analyzing content type...")

        # Check for embedded videos first (highest priority)
        video_urls = self._detect_embedded_videos(soup)

        # Check for embedded audio
        audio_urls = self._detect_embedded_audio(soup)

        # Determine content type
        has_embedded_video = len(video_urls) > 0
        has_embedded_audio = len(audio_urls) > 0
        is_text_only = not has_embedded_video and not has_embedded_audio

        content_type = ContentType(
            has_embedded_video=has_embedded_video,
            has_embedded_audio=has_embedded_audio,
            is_text_only=is_text_only,
            video_urls=video_urls,
            audio_urls=audio_urls
        )

        # Log results
        if content_type.has_embedded_video:
            self.logger.info(f"✅ [CONTENT TYPE] Embedded video detected: {len(video_urls)} videos")
        elif content_type.has_embedded_audio:
            self.logger.info(f"✅ [CONTENT TYPE] Embedded audio detected: {len(audio_urls)} audio files")
        else:
            self.logger.info("✅ [CONTENT TYPE] Text-only content detected")

        return content_type

    def _detect_embedded_videos(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Detect embedded YouTube videos (strict: iframe embeds only)

        Args:
            soup: BeautifulSoup object

        Returns:
            List of video dictionaries with metadata
        """
        video_urls = []

        # Look for YouTube iframe embeds only
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if not src:
                continue

            # Check for YouTube embed URLs
            youtube_patterns = [
                r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
                r'(?:https?://)?(?:www\.)?youtube-nocookie\.com/embed/([a-zA-Z0-9_-]+)'
            ]

            for pattern in youtube_patterns:
                match = re.search(pattern, src)
                if match:
                    video_id = match.group(1)

                    # Verify it's actually a YouTube embed domain
                    if any(domain in src for domain in ['youtube.com/embed', 'youtube-nocookie.com/embed']):
                        video_data = {
                            'video_id': video_id,
                            'url': f'https://www.youtube.com/watch?v={video_id}',
                            'embed_url': src,
                            'platform': 'youtube',
                            'context': 'embedded_iframe'
                        }
                        video_urls.append(video_data)
                        self.logger.info(f"✅ [VIDEO FOUND] {video_id} - Context: embedded_iframe")
                        break

        return video_urls

    def _detect_embedded_audio(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Detect embedded audio content

        Args:
            soup: BeautifulSoup object

        Returns:
            List of audio dictionaries with metadata
        """
        audio_urls = []

        # Check for Stratechery-specific audio player first (but only for text indicators)
        # The actual audio URLs will be found by the standard <audio>/<source> detection below

        # Look for audio elements
        audio_elements = soup.find_all('audio')
        for audio in audio_elements:
            src = audio.get('src', '')

            # Check direct src attribute first
            if src:
                audio_data = {
                    'url': src,
                    'platform': 'html_audio',
                    'context': 'embedded_audio'
                }
                audio_urls.append(audio_data)
                self.logger.info(f"✅ [AUDIO FOUND] {src} - Context: embedded_audio")
            else:
                # Check for nested <source> tags (common pattern)
                source_elements = audio.find_all('source')
                for source in source_elements:
                    source_src = source.get('src', '')
                    if source_src:
                        audio_data = {
                            'url': source_src,
                            'platform': 'html_audio',
                            'context': 'embedded_audio_source',
                            'type': source.get('type', '')
                        }
                        audio_urls.append(audio_data)
                        self.logger.info(f"✅ [AUDIO FOUND] html_audio - Source: {source_src[:100]}... - Context: embedded_audio_source")
                        break  # Use first valid source

        # Look for podcast/audio iframes
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if not src:
                continue

            # Check for common podcast/audio platforms
            audio_platforms = [
                ('spotify.com/embed', 'spotify'),
                ('anchor.fm', 'anchor'),
                ('soundcloud.com', 'soundcloud'),
                ('podcasts.apple.com', 'apple_podcasts'),
                ('player.simplecast.com', 'simplecast')
            ]

            for platform_pattern, platform_name in audio_platforms:
                if platform_pattern in src:
                    audio_data = {
                        'url': src,
                        'platform': platform_name,
                        'context': 'embedded_iframe'
                    }
                    audio_urls.append(audio_data)
                    self.logger.info(f"✅ [AUDIO FOUND] {platform_name} - Context: embedded_iframe")
                    break

        return audio_urls


    def _validate_video_context(self, soup: BeautifulSoup, video_id: str) -> Tuple[bool, str]:
        """
        Verify if video is actually embedded in article content (strict: embedded only)

        Args:
            soup: BeautifulSoup object
            video_id: YouTube video ID

        Returns:
            Tuple of (is_valid, context_description)
        """
        # ONLY check for actual iframe embeds - no links or text references
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if src and f'youtube.com/embed/{video_id}' in src:
                # Verify it's actually a YouTube embed domain
                if src.startswith(('http://youtube.com/embed', 'https://youtube.com/embed',
                                 'http://www.youtube.com/embed', 'https://www.youtube.com/embed')):
                    return True, "embedded_iframe"

        # If no embedded iframe found, treat as text-only article
        return False, "no_embedded_video"