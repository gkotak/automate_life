"""
Content Type Detection Module

Determines if content has embedded video, embedded audio, or is text-only.
"""

import logging
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
import re
import requests

# Import shared utilities
from core.text_utils import check_title_and_date_match

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

    # Supported video file extensions
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg'}
    # Supported audio file extensions
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma', '.opus'}

    def __init__(self, session: requests.Session = None):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.session = session if session else requests.Session()

    def is_direct_media_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Check if URL points directly to a video or audio file

        Args:
            url: The URL to check

        Returns:
            Tuple of (is_media, media_type) where media_type is 'video', 'audio', or None
        """
        from urllib.parse import urlparse, unquote

        # Parse URL and get the path
        parsed = urlparse(url)
        path = unquote(parsed.path.lower())

        # Check for video extensions
        for ext in self.VIDEO_EXTENSIONS:
            if path.endswith(ext):
                self.logger.info(f"🎥 Detected direct video file URL: {ext}")
                return True, 'video'

        # Check for audio extensions
        for ext in self.AUDIO_EXTENSIONS:
            if path.endswith(ext):
                self.logger.info(f"🎵 Detected direct audio file URL: {ext}")
                return True, 'audio'

        return False, None

    def _extract_video_from_iframe_src(self, src: str) -> Optional[Dict]:
        """
        Generic function to extract video platform and ID from iframe src URL

        Supports: YouTube, Loom, Vimeo, Wistia, Dailymotion, and more

        Args:
            src: The iframe src URL

        Returns:
            Video data dict with platform, video_id, url, and embed_url, or None if not recognized
        """
        # Platform configurations: (domain_keyword, regex_patterns, url_template, embed_url_template)
        platforms = {
            'loom': {
                'domains': ['loom.com'],
                'patterns': [
                    r'loom\.com/embed/([a-zA-Z0-9_-]+)',
                    r'loom\.com/share/([a-zA-Z0-9_-]+)',
                    r'loom\.com/v/([a-zA-Z0-9_-]+)'
                ],
                'url_template': 'https://www.loom.com/share/{video_id}',
                'embed_template': 'https://www.loom.com/embed/{video_id}'
            },
            'vimeo': {
                'domains': ['vimeo.com'],
                'patterns': [
                    r'player\.vimeo\.com/video/([0-9]+)',
                    r'vimeo\.com/video/([0-9]+)',
                    r'vimeo\.com/([0-9]+)'
                ],
                'url_template': 'https://vimeo.com/{video_id}',
                'embed_template': 'https://player.vimeo.com/video/{video_id}'
            },
            'youtube': {
                'domains': ['youtube.com', 'youtube-nocookie.com'],
                'patterns': [
                    r'youtube\.com/embed/([a-zA-Z0-9_-]+)',
                    r'youtube-nocookie\.com/embed/([a-zA-Z0-9_-]+)'
                ],
                'url_template': 'https://www.youtube.com/watch?v={video_id}',
                'embed_template': 'https://www.youtube.com/embed/{video_id}'
            },
            'wistia': {
                'domains': ['wistia.com', 'wistia.net'],
                'patterns': [
                    r'fast\.wistia\.(?:net|com)/embed/iframe/([a-zA-Z0-9]+)',
                    r'wistia\.(?:net|com)/medias/([a-zA-Z0-9]+)'
                ],
                'url_template': 'https://fast.wistia.net/embed/iframe/{video_id}',
                'embed_template': 'https://fast.wistia.net/embed/iframe/{video_id}'
            },
            'dailymotion': {
                'domains': ['dailymotion.com'],
                'patterns': [
                    r'dailymotion\.com/embed/video/([a-zA-Z0-9]+)',
                    r'dailymotion\.com/video/([a-zA-Z0-9]+)'
                ],
                'url_template': 'https://www.dailymotion.com/video/{video_id}',
                'embed_template': 'https://www.dailymotion.com/embed/video/{video_id}'
            }
        }

        # Try each platform
        for platform_name, config in platforms.items():
            # Check if any domain keyword is in the src
            if any(domain in src for domain in config['domains']):
                self.logger.info(f"🎯 [{platform_name.upper()} DETECTED] Found {platform_name} iframe: {src[:100]}...")

                # Try each pattern for this platform
                video_id = None
                for pattern in config['patterns']:
                    match = re.search(pattern, src, re.IGNORECASE)
                    if match:
                        video_id = match.group(1)
                        break

                if video_id:
                    return {
                        'video_id': video_id,
                        'url': config['url_template'].format(video_id=video_id),
                        'embed_url': config['embed_template'].format(video_id=video_id),
                        'platform': platform_name,
                        'context': 'iframe_embed'
                    }
                else:
                    self.logger.warning(f"⚠️ [{platform_name.upper()}] Found {platform_name} URL but couldn't extract video ID: {src}")
                    return None

        return None

    def _resolve_iframely_embed(self, iframe_url: str) -> Optional[Dict]:
        """
        Resolve an iframe.ly URL to find the actual video it embeds

        Args:
            iframe_url: The iframe.ly URL (e.g., https://cdn.iframe.ly/QvSl8U8)

        Returns:
            Video dict with platform and video_id, or None if not a recognized video
        """
        try:
            # Fetch the iframe.ly page
            response = self.session.get(iframe_url, timeout=5, allow_redirects=True)

            if response.ok:
                html = response.text
                self.logger.info(f"   [IFRAME.LY] Fetched {len(html)} chars from iframe.ly")

                # Check for various video platforms in the iframe.ly response
                # Loom
                loom_match = re.search(r'loom\.com/(?:share|embed|v)/([a-zA-Z0-9_-]+)', html, re.IGNORECASE)
                if loom_match:
                    video_id = loom_match.group(1)
                    return {
                        'video_id': video_id,
                        'url': f'https://www.loom.com/share/{video_id}',
                        'embed_url': f'https://www.loom.com/embed/{video_id}',
                        'platform': 'loom',
                        'context': 'iframely_resolved'
                    }

                # YouTube
                youtube_match = re.search(r'youtube\.com/(?:watch\?v=|embed/)([a-zA-Z0-9_-]+)', html, re.IGNORECASE)
                if youtube_match:
                    video_id = youtube_match.group(1)
                    return {
                        'video_id': video_id,
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'embed_url': f'https://www.youtube.com/embed/{video_id}',
                        'platform': 'youtube',
                        'context': 'iframely_resolved'
                    }

                # Vimeo
                vimeo_match = re.search(r'vimeo\.com/(?:video/)?([0-9]+)', html, re.IGNORECASE)
                if vimeo_match:
                    video_id = vimeo_match.group(1)
                    return {
                        'video_id': video_id,
                        'url': f'https://vimeo.com/{video_id}',
                        'embed_url': f'https://player.vimeo.com/video/{video_id}',
                        'platform': 'vimeo',
                        'context': 'iframely_resolved'
                    }

                self.logger.info(f"   [IFRAME.LY] No recognized video platform found in response")
                return None
            else:
                self.logger.warning(f"   [IFRAME.LY] Failed to fetch: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"   [IFRAME.LY] Error resolving embed: {e}")
            return None

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

        # First, check if URL points to a direct media file (video/audio)
        is_media, media_type = self.is_direct_media_url(url)
        if is_media:
            if media_type == 'video':
                self.logger.info(f"🎯 [DIRECT VIDEO FILE] URL points to a video file")
                return ContentType(
                    has_embedded_video=True,
                    has_embedded_audio=False,
                    is_text_only=False,
                    video_urls=[{
                        'url': url,
                        'platform': 'direct_file',
                        'context': 'direct_video_file',
                        'requires_download': True
                    }],
                    audio_urls=[]
                )
            elif media_type == 'audio':
                self.logger.info(f"🎯 [DIRECT AUDIO FILE] URL points to an audio file")
                return ContentType(
                    has_embedded_video=False,
                    has_embedded_audio=True,
                    is_text_only=False,
                    video_urls=[],
                    audio_urls=[{
                        'url': url,
                        'platform': 'direct_file',
                        'context': 'direct_audio_file',
                        'requires_download': True
                    }]
                )

        # Check if the URL itself is a direct video link (Loom, YouTube, etc.)
        direct_video = self._detect_direct_video_url(url)
        if direct_video:
            self.logger.info(f"🎯 [DIRECT VIDEO] URL is a direct {direct_video['platform']} video")
            return ContentType(
                has_embedded_video=True,
                has_embedded_audio=False,
                is_text_only=False,
                video_urls=[direct_video],
                audio_urls=[]
            )

        # Check for embedded videos (highest priority)
        self.logger.info("🔍 [VIDEO DETECTION] Searching for video content...")
        video_urls = self._detect_embedded_videos(soup)

        # Only check for audio if no video found (video takes priority)
        audio_urls = []
        if len(video_urls) == 0:
            self.logger.info("🔍 [AUDIO DETECTION] No video found, searching for audio content...")
            audio_urls = self._detect_embedded_audio(soup)
        else:
            self.logger.info(f"⚡ [PRIORITY] Video content found - skipping audio detection (video takes priority)")

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

        # Log results with priority information
        if content_type.has_embedded_video:
            self.logger.info(f"✅ [CONTENT TYPE] 🎥 VIDEO content detected: {len(video_urls)} videos (PRIORITY CONTENT)")
            for i, video in enumerate(video_urls[:3], 1):  # Show first 3
                self.logger.info(f"   📹 Video {i}: {video.get('platform', 'unknown')} - {video.get('context', 'unknown')}")
        elif content_type.has_embedded_audio:
            self.logger.info(f"✅ [CONTENT TYPE] 🎵 AUDIO content detected: {len(audio_urls)} audio files")
            for i, audio in enumerate(audio_urls[:3], 1):  # Show first 3
                self.logger.info(f"   🔊 Audio {i}: {audio.get('platform', 'unknown')} - {audio.get('context', 'unknown')}")
        else:
            self.logger.info("✅ [CONTENT TYPE] 📄 TEXT-ONLY content detected")

        return content_type

    def _detect_direct_video_url(self, url: str) -> Optional[Dict]:
        """
        Detect if the URL itself is a direct video link (Loom, YouTube, etc.)

        Args:
            url: The URL to check

        Returns:
            Video dictionary if URL is a direct video, None otherwise
        """
        # Loom video patterns
        loom_patterns = [
            r'(?:https?://)?(?:www\.)?loom\.com/share/([a-zA-Z0-9]+)',
            r'(?:https?://)?(?:www\.)?loom\.com/embed/([a-zA-Z0-9]+)'
        ]

        for pattern in loom_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return {
                    'video_id': video_id,
                    'url': url,
                    'embed_url': f'https://www.loom.com/embed/{video_id}',
                    'platform': 'loom',
                    'context': 'direct_url'
                }

        # YouTube direct URL patterns
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
        ]

        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return {
                    'video_id': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'embed_url': f'https://www.youtube.com/embed/{video_id}',
                    'platform': 'youtube',
                    'context': 'direct_url'
                }

        return None

    def _detect_embedded_videos(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Detect embedded videos with simplified, reliable approach:
        1. Iframe embeds (highest priority)
        2. Video links in main body content only (no sidebars)
        3. Validate first 2 videos by checking YouTube page

        Args:
            soup: BeautifulSoup object

        Returns:
            List of validated video dictionaries
        """
        video_urls = []

        # 1. HIGHEST PRIORITY: iframe embeds in main content
        iframe_videos = self._detect_iframe_videos_in_main_content(soup)
        if iframe_videos:
            self.logger.info(f"🎯 [IFRAME PRIORITY] Found {len(iframe_videos)} iframe video(s) - using first one as main content")
            return iframe_videos[:1]  # Max 1 iframe video

        # 2. FALLBACK: Video links in main body content only
        self.logger.info("🔍 [FALLBACK] No iframe videos found, searching for video links in main content...")
        main_body_videos = self._detect_video_links_in_main_body(soup)

        if not main_body_videos:
            self.logger.info("ℹ️ [NO VIDEOS] No video content found in main body")
            return []

        # 3. VALIDATION: Check up to 3 videos, return first match only
        for i, video in enumerate(main_body_videos[:3], 1):
            self.logger.info(f"🔎 [VALIDATING] Video {i}: {video['video_id']}")
            if self._validate_video_against_content(video, soup):
                self.logger.info(f"✅ [VALIDATED] Video {i}: {video['video_id']} - matches content, using as main video")
                return [video]  # Return first validated video only
            else:
                self.logger.info(f"❌ [REJECTED] Video {i}: {video['video_id']} - doesn't match content")

        self.logger.info("❌ [NO MATCH] No videos validated against content")
        return []

    def _detect_iframe_videos_in_main_content(self, soup: BeautifulSoup) -> List[Dict]:
        """Detect iframe video embeds within main content areas only"""
        video_urls = []

        # Find main content container
        main_content = self._find_main_content_area(soup)
        if not main_content:
            main_content = soup  # Fallback to entire page

        # FIRST: Check for async embeds (divs/scripts with video IDs for any platform)
        async_embeds = self._detect_async_embeds(soup)
        if async_embeds:
            platform = async_embeds[0].get('platform', 'unknown').upper()
            video_id = async_embeds[0].get('video_id', 'unknown')
            self.logger.info(f"✅ [{platform} ASYNC] Found async embed: {video_id}")
            return async_embeds

        # Look for video iframe embeds in main content only
        iframes = main_content.find_all('iframe')
        self.logger.info(f"🔍 [IFRAME SEARCH] Found {len(iframes)} total iframes in main content")

        # Debug: Check if there are ANY iframes in the entire page
        all_iframes = soup.find_all('iframe')
        if len(all_iframes) != len(iframes):
            self.logger.info(f"   [DEBUG] Total iframes in entire page: {len(all_iframes)} (vs {len(iframes)} in main content)")

        # Also check for Loom embeds that might be loaded via JavaScript or in the full page
        # Look for any element that contains loom.com URL
        page_html = str(soup)
        page_html_lower = page_html.lower()

        self.logger.info(f"   [HTML SEARCH] Searching {len(page_html)} chars of HTML for 'loom' references...")

        # Debug: Save HTML to file for inspection
        try:
            from pathlib import Path
            debug_dir = Path(__file__).parent.parent / 'logs'
            debug_dir.mkdir(exist_ok=True)
            debug_file = debug_dir / 'debug_html_content.txt'
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(page_html)
            self.logger.info(f"   [DEBUG] Saved HTML to: {debug_file}")
        except Exception as e:
            self.logger.warning(f"   [DEBUG] Could not save HTML: {e}")

        # Debug: Check if "loom" appears anywhere in the HTML
        loom_count = page_html_lower.count('loom')
        self.logger.info(f"   [DEBUG] Found {loom_count} occurrences of 'loom' in HTML")

        # Debug: Check if iframe.ly is in there
        iframely_count = page_html_lower.count('iframe.ly')
        self.logger.info(f"   [DEBUG] Found {iframely_count} occurrences of 'iframe.ly' in HTML")

        # First, do a comprehensive search for ANY loom.com URLs in the HTML
        # This should catch it regardless of context (iframe.ly, direct embed, etc.)
        loom_url_pattern = r'https?://(?:www\.)?loom\.com/(?:share|embed|v)/([a-zA-Z0-9_-]+)'
        loom_matches = re.findall(loom_url_pattern, page_html, re.IGNORECASE)

        self.logger.info(f"   [DEBUG] Regex found {len(loom_matches)} loom.com URLs")

        if loom_matches:
            self.logger.info(f"🎯 [LOOM DETECTED] Found {len(loom_matches)} Loom URLs in page HTML")
            for i, match in enumerate(loom_matches[:3]):
                self.logger.info(f"   Loom URL {i+1}: video_id={match}")

            # Use the first Loom video found
            video_id = loom_matches[0]
            video_data = {
                'video_id': video_id,
                'url': f'https://www.loom.com/share/{video_id}',
                'embed_url': f'https://www.loom.com/embed/{video_id}',
                'platform': 'loom',
                'context': 'html_reference'
            }
            video_urls.append(video_data)
            self.logger.info(f"✅ [LOOM FOUND] Extracted video ID from HTML: {video_id}")
            return video_urls

        # Legacy fallback checks
        if 'loom' in page_html_lower:
            self.logger.info(f"🎯 [LOOM DETECTED] Page HTML contains 'loom' references")
            # Extract all loom URLs from page (case insensitive)
            loom_url_pattern = r'https?://(?:www\.)?loom\.com/(?:share|embed|v)/([a-zA-Z0-9]+)'
            loom_matches = re.findall(loom_url_pattern, page_html, re.IGNORECASE)
            if loom_matches:
                self.logger.info(f"   [LOOM] Found {len(loom_matches)} Loom video IDs in page HTML: {loom_matches[:3]}")
                # Use the first Loom video found
                video_id = loom_matches[0]
                video_data = {
                    'video_id': video_id,
                    'url': f'https://www.loom.com/share/{video_id}',
                    'embed_url': f'https://www.loom.com/embed/{video_id}',
                    'platform': 'loom',
                    'context': 'html_reference'
                }
                video_urls.append(video_data)
                self.logger.info(f"✅ [LOOM FOUND] Extracted video ID from HTML: {video_id}")
                return video_urls
            else:
                self.logger.info(f"   [LOOM] Found 'loom' in HTML but no valid loom.com URLs matched pattern")
        else:
            self.logger.info(f"   [HTML SEARCH] No 'loom' references found in page HTML")

        for iframe in iframes:
            src = iframe.get('src', '')
            if not src:
                self.logger.info(f"   [IFRAME] Found iframe with no src attribute, checking data-src or other attributes...")
                # Check for data-src or other lazy-loading attributes
                data_src = iframe.get('data-src', '')
                if data_src:
                    self.logger.info(f"   [IFRAME] Found data-src: {data_src[:100]}...")
                    src = data_src
                else:
                    # Log the entire iframe element to see what we have
                    self.logger.info(f"   [IFRAME] Full iframe element: {str(iframe)[:300]}...")
                    continue

            self.logger.info(f"   [IFRAME] Checking src: {src[:100]}...")

            # Check for iframe.ly embeds - these are proxies that wrap real videos
            # We should fetch the iframe.ly URL to see what it actually embeds
            if 'iframe.ly' in src:
                self.logger.info(f"🔍 [IFRAME.LY] Detected iframe.ly embed, fetching to find actual video...")
                actual_video = self._resolve_iframely_embed(src)
                if actual_video:
                    video_urls.append(actual_video)
                    self.logger.info(f"✅ [IFRAME.LY] Resolved to {actual_video['platform']} video: {actual_video['video_id']}")
                    return video_urls
                else:
                    self.logger.info(f"⚠️ [IFRAME.LY] Could not resolve iframe.ly embed to a video")

            # Try to extract video from iframe src using generic platform detection
            video_data = self._extract_video_from_iframe_src(src)
            if video_data:
                video_urls.append(video_data)
                self.logger.info(f"✅ [IFRAME FOUND] {video_data['platform'].title()} video ID: {video_data['video_id']}")
                return video_urls  # Return first video found

        return video_urls

    def _detect_async_embeds(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Detect async JavaScript embeds for various video platforms (Wistia, Loom, Vimeo, etc.)

        Many platforms support async embeds where the video is loaded via JavaScript
        instead of iframes. Common patterns:
        - Div with platform-specific class: <div class="wistia_async_VIDEO_ID">
        - Script tag with platform URL: <script src="https://platform.com/embed/VIDEO_ID">

        Args:
            soup: BeautifulSoup object

        Returns:
            List with single video dict, or empty list
        """
        video_urls = []

        # Platform configurations for async embeds
        # Format: (class_pattern, url_template, embed_template, platform_name)
        async_platforms = [
            {
                'name': 'wistia',
                'class_pattern': r'wistia_async_([a-zA-Z0-9]+)',
                'script_pattern': r'wistia\.(?:com|net)/embed/medias/([a-zA-Z0-9]+)',
                'url_template': 'https://fast.wistia.net/embed/iframe/{video_id}',
                'embed_template': 'https://fast.wistia.net/embed/iframe/{video_id}'
            },
            {
                'name': 'loom',
                'class_pattern': r'loom_async_([a-zA-Z0-9_-]+)',
                'script_pattern': r'loom\.com/(?:embed|share)/([a-zA-Z0-9_-]+)',
                'url_template': 'https://www.loom.com/share/{video_id}',
                'embed_template': 'https://www.loom.com/embed/{video_id}'
            },
            {
                'name': 'vimeo',
                'class_pattern': r'vimeo_async_([0-9]+)',
                'script_pattern': r'vimeo\.com/(?:video/)?([0-9]+)',
                'url_template': 'https://vimeo.com/{video_id}',
                'embed_template': 'https://player.vimeo.com/video/{video_id}'
            }
        ]

        # Pattern 1: Look for divs with platform_async_[video_id] class patterns
        for platform_config in async_platforms:
            class_pattern = re.compile(platform_config['class_pattern'])

            # Find all divs and check their classes
            for div in soup.find_all('div'):
                classes = div.get('class', [])
                for cls in classes:
                    match = class_pattern.search(str(cls))
                    if match:
                        video_id = match.group(1)
                        video_data = {
                            'video_id': video_id,
                            'url': platform_config['url_template'].format(video_id=video_id),
                            'embed_url': platform_config['embed_template'].format(video_id=video_id),
                            'platform': platform_config['name'],
                            'context': 'async_embed'
                        }
                        video_urls.append(video_data)
                        self.logger.info(f"✅ [{platform_config['name'].upper()} ASYNC] Found async embed with video ID: {video_id}")
                        return video_urls  # Return first one found

        # Pattern 2: Look for script tags with platform-specific URLs
        for script in soup.find_all('script', src=True):
            src = script.get('src', '')

            for platform_config in async_platforms:
                script_pattern = platform_config['script_pattern']
                match = re.search(script_pattern, src, re.IGNORECASE)
                if match:
                    video_id = match.group(1)
                    video_data = {
                        'video_id': video_id,
                        'url': platform_config['url_template'].format(video_id=video_id),
                        'embed_url': platform_config['embed_template'].format(video_id=video_id),
                        'platform': platform_config['name'],
                        'context': 'script_reference'
                    }
                    video_urls.append(video_data)
                    self.logger.info(f"✅ [{platform_config['name'].upper()} SCRIPT] Found script reference with video ID: {video_id}")
                    return video_urls  # Return first one found

        return video_urls

    def _detect_video_links_in_main_body(self, soup: BeautifulSoup) -> List[Dict]:
        """Detect YouTube video links within main body content only (no sidebars)"""
        video_urls = []

        # Find main content container
        main_content = self._find_main_content_area(soup)
        if not main_content:
            self.logger.warning("⚠️ [MAIN CONTENT] Could not identify main content area, using entire page")
            main_content = soup

        # YouTube URL patterns
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
        ]

        # Check links in main content only
        links = main_content.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')

            for pattern in youtube_patterns:
                match = re.search(pattern, href)
                if match:
                    video_id = match.group(1)
                    # Avoid duplicates
                    if not any(v.get('video_id') == video_id for v in video_urls):
                        video_data = {
                            'video_id': video_id,
                            'url': f'https://www.youtube.com/watch?v={video_id}',
                            'embed_url': f'https://www.youtube.com/embed/{video_id}',
                            'platform': 'youtube',
                            'context': 'main_body_link'
                        }
                        video_urls.append(video_data)
                        self.logger.info(f"🔗 [LINK FOUND] YouTube: {video_id}")
                        break

        return video_urls

    def _find_main_content_area(self, soup: BeautifulSoup) -> Optional:
        """Find the main content area, excluding sidebars and navigation"""

        # Try common main content selectors in order of specificity
        main_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.main-content',
            '.post-content',
            '.entry-content',
            '.content',
            '#main',
            '#content'
        ]

        for selector in main_selectors:
            main_element = soup.select_one(selector)
            if main_element:
                self.logger.debug(f"📍 [MAIN CONTENT] Found using selector: {selector}")
                return main_element

        # Fallback: exclude known sidebar/navigation areas
        excluded_elements = soup.find_all(['aside', 'nav', 'footer', 'header'])
        excluded_elements.extend(soup.find_all(class_=lambda x: x and any(
            keyword in x.lower() for keyword in ['sidebar', 'navigation', 'footer', 'header', 'menu']
        )))

        # Remove excluded elements from consideration
        for element in excluded_elements:
            element.decompose()

        return soup

    def _validate_video_against_content(self, video: Dict, soup: BeautifulSoup) -> bool:
        """
        Validate video by checking title and publication date matching

        Uses shared validation logic:
        - Strong match: 65% title similarity
        - Combined match: 50% title similarity + dates within 1 day

        Args:
            video: Video dict with video_id
            soup: BeautifulSoup of article page

        Returns:
            True if video matches article content, False otherwise
        """
        video_id = video.get('video_id')
        if not video_id:
            return False

        try:
            # Get YouTube page content
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(youtube_url, timeout=10)
            youtube_soup = BeautifulSoup(response.content, 'html.parser')

            # Extract video title and date from YouTube page
            video_title = self._extract_youtube_title(youtube_soup)
            if not video_title:
                self.logger.warning(f"⚠️ [VALIDATION] Could not extract title for video {video_id}")
                return False

            video_date = self._extract_youtube_date(youtube_soup)

            # Extract article title and date
            article_title = self._extract_article_title(soup)
            if not article_title:
                self.logger.warning(f"⚠️ [VALIDATION] Could not extract article title")
                return False

            article_date = self._extract_article_date(soup)

            # Use shared utility for validation
            matches, similarity, match_type = check_title_and_date_match(
                video_title,
                article_title,
                video_date,
                article_date,
                strong_threshold=0.65,
                weak_threshold=0.50,
                date_tolerance_days=1
            )

            # Log detailed info
            self.logger.info(f"📊 [TITLE MATCH] {similarity*100:.1f}% similarity")
            self.logger.info(f"   Video:   '{video_title}'")
            self.logger.info(f"   Article: '{article_title}'")

            if video_date:
                self.logger.info(f"📅 [VIDEO DATE] {video_date.strftime('%Y-%m-%d')}")
            else:
                self.logger.info(f"⚠️ [VIDEO DATE] Could not extract")

            if article_date:
                self.logger.info(f"📅 [ARTICLE DATE] {article_date.strftime('%Y-%m-%d')}")
            else:
                self.logger.info(f"⚠️ [ARTICLE DATE] Could not extract")

            if matches:
                if match_type == "strong_title":
                    self.logger.info(f"✅ [STRONG MATCH] Title {similarity*100:.1f}% >= 65%")
                elif match_type == "title_plus_date":
                    date_diff = abs((video_date - article_date).days)
                    self.logger.info(f"✅ [COMBINED MATCH] Title {similarity*100:.1f}% >= 50% + Date diff {date_diff} day(s) <= 1")
                return True
            else:
                self.logger.info(f"❌ [NO MATCH] Title {similarity*100:.1f}% (need 65% or 50%+date)")
                return False

        except Exception as e:
            self.logger.error(f"❌ [VALIDATION ERROR] {video_id}: {str(e)}")
            return False

    def _extract_youtube_title(self, youtube_soup: BeautifulSoup) -> Optional[str]:
        """Extract video title from YouTube page"""
        # Try multiple selectors for title
        title_selectors = [
            'meta[property="og:title"]',
            'meta[name="title"]',
            'title',
            'h1.ytd-video-primary-info-renderer',
            '.watch-main-col h1'
        ]

        for selector in title_selectors:
            element = youtube_soup.select_one(selector)
            if element:
                title = element.get('content') or element.get_text(strip=True)
                if title and len(title) > 5:  # Basic validation
                    return title.replace(' - YouTube', '').strip()

        return None

    def _extract_article_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article title from page"""
        # Try multiple selectors for article title in priority order
        # og:title and h1 are usually cleaner than <title> tag
        title_selectors = [
            'meta[property="og:title"]',  # Clean title without site name
            'h1',                          # Main heading
            'meta[name="title"]',
            '.post-title',
            '.entry-title',
            'title'                        # Last resort - often has extra text
        ]

        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') or element.get_text(strip=True)
                if title and len(title) > 10:  # Basic validation
                    # Clean common suffixes/prefixes
                    title = self._clean_article_title(title)
                    return title.strip()

        return None

    def _clean_article_title(self, title: str) -> str:
        """Remove common site names, author info from article titles"""
        import re

        # Common patterns to remove (case insensitive)
        patterns = [
            r'\s*[-–|]\s*by\s+.*$',           # " - by Author Name"
            r'\s*[-–|]\s*.*Newsletter.*$',     # " - Newsletter Name"
            r'\s*[-–|]\s*.*Blog.*$',           # " - Blog Name"
            r'\s*[-–|]\s*Medium$',             # " - Medium"
            r'\s*[-–|]\s*Substack$',           # " - Substack"
        ]

        cleaned = title
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _extract_youtube_date(self, youtube_soup: BeautifulSoup) -> Optional[datetime]:
        """Extract publication date from YouTube video page"""
        try:
            # Look for uploadDate in meta tags or JSON-LD
            date_patterns = [
                r'"uploadDate":"([^"]+)"',
                r'"datePublished":"([^"]+)"',
                r'"publishDate":"([^"]+)"'
            ]

            page_text = str(youtube_soup)
            for pattern in date_patterns:
                match = re.search(pattern, page_text)
                if match:
                    date_str = match.group(1)
                    try:
                        # Parse ISO format date (e.g., "2024-10-23" or "2024-10-23T10:30:00Z")
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    except:
                        continue

            # Fallback: Try meta tags
            meta_date = youtube_soup.find('meta', property='uploadDate')
            if meta_date and meta_date.get('content'):
                try:
                    date_str = meta_date.get('content')
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                except:
                    pass

            self.logger.debug("🔍 [YOUTUBE DATE] Could not extract publication date")
            return None

        except Exception as e:
            self.logger.debug(f"⚠️ [YOUTUBE DATE ERROR] {str(e)}")
            return None

    def _extract_article_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract publication date from article page"""
        try:
            # Try multiple selectors for article date
            date_selectors = [
                ('meta', {'property': 'article:published_time'}),
                ('meta', {'property': 'og:published_time'}),
                ('meta', {'name': 'publish_date'}),
                ('meta', {'name': 'publication_date'}),
                ('meta', {'name': 'datePublished'}),
                ('time', {'itemprop': 'datePublished'}),
                ('time', {'class': 'published'}),
            ]

            for tag, attrs in date_selectors:
                element = soup.find(tag, attrs)
                if element:
                    date_str = element.get('content') or element.get('datetime') or element.get_text(strip=True)
                    if date_str:
                        try:
                            # Try parsing various date formats
                            # ISO format
                            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        except:
                            try:
                                # Try common formats
                                from dateutil import parser
                                return parser.parse(date_str).replace(tzinfo=None)
                            except:
                                continue

            # Fallback: Look for date patterns in JSON-LD
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    date_str = data.get('datePublished') or data.get('uploadDate')
                    if date_str:
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                except:
                    continue

            self.logger.debug("🔍 [ARTICLE DATE] Could not extract publication date")
            return None

        except Exception as e:
            self.logger.debug(f"⚠️ [ARTICLE DATE ERROR] {str(e)}")
            return None

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity percentage between two titles using token overlap"""
        import re

        # Normalize titles
        def normalize(text):
            # Convert to lowercase, remove special chars, split into words
            return set(re.findall(r'\b\w+\b', text.lower()))

        words1 = normalize(title1)
        words2 = normalize(title2)

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return (intersection / union) * 100.0 if union > 0 else 0.0

    def _extract_youtube_duration(self, youtube_soup: BeautifulSoup) -> Optional[int]:
        """Extract video duration in seconds from YouTube page"""
        # Look for duration in meta tags or JSON-LD
        duration_patterns = [
            r'"lengthSeconds":"(\d+)"',
            r'"duration":"PT(\d+)M(\d+)S"',
            r'"duration":"PT(\d+)H(\d+)M(\d+)S"'
        ]

        page_text = str(youtube_soup)
        for pattern in duration_patterns:
            match = re.search(pattern, page_text)
            if match:
                if len(match.groups()) == 1:  # lengthSeconds
                    return int(match.group(1))
                elif len(match.groups()) == 2:  # PT30M45S
                    minutes, seconds = match.groups()
                    return int(minutes) * 60 + int(seconds)
                elif len(match.groups()) == 3:  # PT1H30M45S
                    hours, minutes, seconds = match.groups()
                    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

        return None

    def _get_embedded_audio_duration(self, soup: BeautifulSoup) -> Optional[int]:
        """Get duration of embedded audio player if available"""
        try:
            # Method 1: Look for Substack audio duration in player metadata
            duration_patterns = [
                r'"duration":(\d+)',
                r'"lengthSeconds":(\d+)',
                r'duration["\']:\s*(\d+)',
                r'audioDuration["\']:\s*(\d+)'
            ]

            page_text = str(soup)
            for pattern in duration_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    duration = int(matches[0])
                    if 30 <= duration <= 86400:  # Between 30 seconds and 24 hours
                        self.logger.info(f"🎵 [AUDIO DURATION] Found via pattern: {duration}s")
                        return duration

            # Method 2: Look for duration in audio player UI elements
            duration_selectors = [
                '.timestamp-FzOPmB',  # Substack timestamp classes
                '[class*="duration"]',
                '[class*="time"]',
                '[data-time]'
            ]

            for selector in duration_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    duration = self._parse_time_string(text)
                    if duration:
                        self.logger.info(f"🎵 [AUDIO DURATION] Found via selector '{selector}': {duration}s ({text})")
                        return duration

            # Method 3: Look for audio element with duration data
            audio_elements = soup.find_all('audio')
            for audio in audio_elements:
                # Check for data attributes
                for attr in ['data-duration', 'duration', 'data-length']:
                    if audio.get(attr):
                        try:
                            duration = int(float(audio.get(attr)))
                            if 30 <= duration <= 86400:
                                self.logger.info(f"🎵 [AUDIO DURATION] Found via audio[{attr}]: {duration}s")
                                return duration
                        except (ValueError, TypeError):
                            continue

            self.logger.debug("🎵 [AUDIO DURATION] No duration found in embedded audio")
            return None

        except Exception as e:
            self.logger.error(f"❌ [AUDIO DURATION ERROR] {str(e)}")
            return None

    def _parse_time_string(self, time_str: str) -> Optional[int]:
        """Parse time string like '1:46:32', '45:30', '2:15', '-1:46:32' into seconds"""
        if not time_str:
            return None

        try:
            # Remove common prefixes/suffixes and handle negative (remaining time)
            time_str = time_str.strip().replace('Total time:', '').replace('Duration:', '').strip()

            # Remove leading minus (for remaining time display like "-1:46:32")
            if time_str.startswith('-'):
                time_str = time_str[1:]
                self.logger.debug(f"🎵 [PARSE TIME] Removed negative sign from remaining time: {time_str}")

            # Match patterns like HH:MM:SS, MM:SS, or just numbers
            time_patterns = [
                r'^(\d+):(\d+):(\d+)$',  # HH:MM:SS
                r'^(\d+):(\d+)$',        # MM:SS
                r'^(\d+)$'               # Just seconds
            ]

            for pattern in time_patterns:
                match = re.match(pattern, time_str)
                if match:
                    parts = [int(x) for x in match.groups()]
                    if len(parts) == 3:  # HH:MM:SS
                        duration = parts[0] * 3600 + parts[1] * 60 + parts[2]
                        self.logger.debug(f"🎵 [PARSE TIME] Parsed {time_str} as {duration}s")
                        return duration
                    elif len(parts) == 2:  # MM:SS
                        duration = parts[0] * 60 + parts[1]
                        self.logger.debug(f"🎵 [PARSE TIME] Parsed {time_str} as {duration}s")
                        return duration
                    elif len(parts) == 1:  # SS
                        duration = parts[0]
                        self.logger.debug(f"🎵 [PARSE TIME] Parsed {time_str} as {duration}s")
                        return duration

            return None

        except (ValueError, TypeError):
            return None

    def _detect_iframe_videos(self, soup: BeautifulSoup) -> List[Dict]:
        """Detect video iframes from various platforms"""
        video_urls = []

        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if not src:
                continue

            # YouTube patterns
            youtube_patterns = [
                r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
                r'(?:https?://)?(?:www\.)?youtube-nocookie\.com/embed/([a-zA-Z0-9_-]+)'
            ]

            for pattern in youtube_patterns:
                match = re.search(pattern, src)
                if match:
                    video_id = match.group(1)
                    if any(domain in src for domain in ['youtube.com/embed', 'youtube-nocookie.com/embed']):
                        video_data = {
                            'video_id': video_id,
                            'url': f'https://www.youtube.com/watch?v={video_id}',
                            'embed_url': src,
                            'platform': 'youtube',
                            'context': 'embedded_iframe'
                        }
                        video_urls.append(video_data)
                        self.logger.info(f"✅ [VIDEO FOUND] YouTube iframe: {video_id}")
                        break

            # Vimeo patterns
            vimeo_pattern = r'(?:https?://)?(?:www\.)?vimeo\.com/video/([0-9]+)'
            match = re.search(vimeo_pattern, src)
            if match:
                video_id = match.group(1)
                video_data = {
                    'video_id': video_id,
                    'url': f'https://vimeo.com/{video_id}',
                    'embed_url': src,
                    'platform': 'vimeo',
                    'context': 'embedded_iframe'
                }
                video_urls.append(video_data)
                self.logger.info(f"✅ [VIDEO FOUND] Vimeo iframe: {video_id}")

        return video_urls

    def _detect_html5_videos(self, soup: BeautifulSoup) -> List[Dict]:
        """Detect HTML5 video elements"""
        video_urls = []

        video_elements = soup.find_all('video')
        for video in video_elements:
            src = video.get('src', '')

            if src:
                video_data = {
                    'url': src,
                    'platform': 'html5_video',
                    'context': 'embedded_video_element'
                }
                video_urls.append(video_data)
                self.logger.info(f"✅ [VIDEO FOUND] HTML5 video: {src[:100]}...")
            else:
                # Check for nested source tags
                source_elements = video.find_all('source')
                for source in source_elements:
                    source_src = source.get('src', '')
                    if source_src:
                        video_data = {
                            'url': source_src,
                            'platform': 'html5_video',
                            'context': 'embedded_video_source',
                            'type': source.get('type', '')
                        }
                        video_urls.append(video_data)
                        self.logger.info(f"✅ [VIDEO FOUND] HTML5 video source: {source_src[:100]}...")
                        break

        return video_urls

    def _detect_youtube_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Detect YouTube links in article content"""
        video_urls = []

        # YouTube URL patterns
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)'
        ]

        # Check all links in the content
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')

            for pattern in youtube_patterns:
                match = re.search(pattern, href)
                if match:
                    video_id = match.group(1)
                    video_data = {
                        'video_id': video_id,
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'embed_url': f'https://www.youtube.com/embed/{video_id}',
                        'platform': 'youtube',
                        'context': 'content_link'
                    }
                    video_urls.append(video_data)
                    self.logger.info(f"✅ [VIDEO FOUND] YouTube link: {video_id}")
                    break

        # Also check text content for YouTube URLs (in case they're not linked)
        text_content = soup.get_text()
        for pattern in youtube_patterns:
            matches = re.finditer(pattern, text_content)
            for match in matches:
                video_id = match.group(1)
                # Avoid duplicates
                if not any(v.get('video_id') == video_id for v in video_urls):
                    video_data = {
                        'video_id': video_id,
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'embed_url': f'https://www.youtube.com/embed/{video_id}',
                        'platform': 'youtube',
                        'context': 'text_mention'
                    }
                    video_urls.append(video_data)
                    self.logger.info(f"✅ [VIDEO FOUND] YouTube text mention: {video_id}")

        return video_urls

    def _detect_other_video_platforms(self, soup: BeautifulSoup) -> List[Dict]:
        """Detect other video platforms in iframes and links"""
        video_urls = []

        # Platform patterns for iframes and links
        platform_patterns = [
            ('wistia.com', 'wistia'),
            ('loom.com', 'loom'),
            ('twitch.tv', 'twitch'),
            ('dailymotion.com', 'dailymotion'),
            ('player.vimeo.com', 'vimeo'),
            ('embed.ted.com', 'ted')
        ]

        # Check iframes
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if src:
                for pattern, platform_name in platform_patterns:
                    if pattern in src:
                        video_data = {
                            'url': src,
                            'platform': platform_name,
                            'context': 'embedded_iframe'
                        }
                        video_urls.append(video_data)
                        self.logger.info(f"✅ [VIDEO FOUND] {platform_name} iframe")
                        break

        # Check links
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            for pattern, platform_name in platform_patterns:
                if pattern in href and 'video' in href.lower():
                    video_data = {
                        'url': href,
                        'platform': platform_name,
                        'context': 'content_link'
                    }
                    video_urls.append(video_data)
                    self.logger.info(f"✅ [VIDEO FOUND] {platform_name} link")
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

        # Look for direct MP3/audio file links (Pocket Casts, podcast sites, etc.)
        audio_links = soup.find_all('a', href=True)
        for link in audio_links:
            href = link.get('href', '')
            # Check if link points to audio file
            if any(ext in href.lower() for ext in ['.mp3', '.m4a', '.wav', '.ogg', '.aac']):
                audio_data = {
                    'url': href,
                    'platform': 'direct_audio_link',
                    'context': 'audio_file_link',
                    'link_text': link.get_text(strip=True)[:100]
                }
                audio_urls.append(audio_data)
                self.logger.info(f"✅ [AUDIO FOUND] direct_audio_link - URL: {href[:100]}... - Context: audio_file_link")

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