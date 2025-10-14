"""
Content Type Detection Module

Determines if content has embedded video, embedded audio, or is text-only.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import re
import requests

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

    def __init__(self, session: requests.Session = None):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.session = session if session else requests.Session()

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

        # Look for YouTube iframe embeds in main content only
        iframes = main_content.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if not src:
                continue

            # YouTube iframe patterns
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
                            'context': 'iframe_embed'
                        }
                        video_urls.append(video_data)
                        self.logger.info(f"🎯 [IFRAME FOUND] YouTube: {video_id}")
                        break

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
        Validate video by checking YouTube page title/duration against embedded audio
        Returns True if video title matches article (90%+) OR duration matches embedded audio
        """
        video_id = video.get('video_id')
        if not video_id:
            return False

        try:
            # Get YouTube page content
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(youtube_url, timeout=10)
            youtube_soup = BeautifulSoup(response.content, 'html.parser')

            # Extract video title from YouTube page
            video_title = self._extract_youtube_title(youtube_soup)
            if not video_title:
                self.logger.warning(f"⚠️ [VALIDATION] Could not extract title for video {video_id}")
                return False

            # Get article title for comparison
            article_title = self._extract_article_title(soup)

            # Check title similarity (65%+ match)
            title_similarity = 0.0
            if article_title:
                title_similarity = self._calculate_title_similarity(video_title, article_title)
                self.logger.info(f"📊 [TITLE MATCH] {title_similarity:.1f}% similarity: '{video_title}' vs '{article_title}'")

                if title_similarity >= 65.0:
                    self.logger.info(f"✅ [TITLE MATCH] Title similarity {title_similarity:.1f}% >= 65%")
                    return True

            # Check duration against embedded audio (if available)
            video_duration = self._extract_youtube_duration(youtube_soup)
            audio_duration = self._get_embedded_audio_duration(soup)

            if video_duration and audio_duration:
                duration_diff = abs(video_duration - audio_duration)

                # Calculate flexible threshold: 5% of audio duration OR 45 seconds, whichever is smaller
                threshold_5_percent = audio_duration * 0.05
                threshold = min(threshold_5_percent, 45)

                self.logger.info(f"📊 [DURATION CHECK] Video: {video_duration}s, Audio: {audio_duration}s, Diff: {duration_diff}s")
                self.logger.info(f"📊 [THRESHOLD] 5% of audio: {threshold_5_percent:.1f}s, Max: 45s, Using: {threshold:.1f}s")

                if duration_diff <= threshold:
                    self.logger.info(f"✅ [DURATION MATCH] Duration difference {duration_diff}s <= {threshold:.1f}s")
                    return True

            # Calculate threshold for error message
            threshold_for_msg = min(audio_duration * 0.05, 45) if audio_duration else 45
            self.logger.info(f"❌ [NO MATCH] Title: {title_similarity:.1f}% (need 65%+), Duration: Video={video_duration}s Audio={audio_duration}s (need ≤{threshold_for_msg:.1f}s diff)")
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
        title_selectors = [
            'title',  # Highest priority - usually most complete
            'h1',
            'meta[property="og:title"]',
            'meta[name="title"]',
            '.post-title',
            '.entry-title'
        ]

        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') or element.get_text(strip=True)
                if title and len(title) > 10:  # Basic validation
                    return title.strip()

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