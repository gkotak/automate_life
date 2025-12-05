#!/usr/bin/env python3
"""
Article Processor - Railway Backend Version

Processes articles and saves structured data to Supabase database.
Adapted for Railway deployment with FastAPI integration.

Features:
- Content type detection (video/audio/text-only)
- Authentication handling for paywalled content
- AI-powered content analysis using Claude
- Saves structured data (summaries, insights, transcripts) to Supabase
- Returns article ID for API response

Usage (via FastAPI):
    POST /api/process-article
    {"url": "https://example.com/article"}

View results:
    http://localhost:3000/article/{id}
"""

import sys
import json
import os
import re
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Awaitable
from bs4 import BeautifulSoup
from supabase import create_client, Client
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables (Railway uses environment variables directly)
# No need to load from .env.local files on Railway
load_dotenv()  # Still loads from .env.local for local testing

# Add parent directory to Python path for Railway
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import from core and processors (Railway backend structure)
from core.base import BaseProcessor
from core.config import Config
from core.content_detector import ContentTypeDetector, ContentType
from core.authentication import AuthenticationManager
from core.claude_client import ClaudeClient
from core.source_extractor import extract_source, extract_domain, normalize_source_name
from core.text_utils import sanitize_filename
from core.prompts import (
    ArticleAnalysisPrompt,
    VideoContextBuilder,
    AudioContextBuilder,
    TextContextBuilder,
    ThemedInsightsPrompt,
    MediaContextBuilder,
    create_metadata_for_prompt
)
from processors.transcript_processor import TranscriptProcessor
from processors.file_transcriber import FileTranscriber
from core.youtube_discovery import YouTubeDiscoveryService


class ArticleProcessor(BaseProcessor):
    """
    Main article summarizer that handles all content types:
    - Embedded video content (with transcripts)
    - Embedded audio content (with transcripts)
    - Text-only articles
    """

    def __init__(self, event_emitter=None):
        super().__init__("ArticleProcessor")
        self.event_emitter = event_emitter
        self.auth_manager = AuthenticationManager(self.base_dir, self.session)
        self.content_detector = ContentTypeDetector(self.session)
        self.transcript_processor = TranscriptProcessor(self.base_dir, self.session)
        claude_cmd = Config.find_claude_cli()
        self.claude_client = ClaudeClient(claude_cmd, self.base_dir, self.logger)

        # Initialize file transcriber for audio/video without transcripts
        try:
            self.file_transcriber = FileTranscriber()
            self.logger.info("✅ File transcriber initialized")
        except Exception as e:
            self.logger.warning(f"⚠️ File transcriber not available: {e}")
            self.file_transcriber = None

        # Initialize Supabase client with service role key
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.supabase: Optional[Client] = None

        if supabase_url and supabase_key:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                self.logger.info("✅ Supabase client initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to initialize Supabase: {e}")
        else:
            missing = []
            if not supabase_url:
                missing.append('SUPABASE_URL')
            if not supabase_key:
                missing.append('SUPABASE_SERVICE_ROLE_KEY')
            self.logger.warning(f"⚠️ Supabase credentials not found - database insertion will be skipped (missing: {', '.join(missing)})")

        # Initialize OpenAI client for embeddings
        openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_client: Optional[OpenAI] = None

        if openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=openai_api_key)
                self.logger.info("✅ OpenAI client initialized for embeddings")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to initialize OpenAI client: {e}")
        else:
            self.logger.warning("⚠️ OPENAI_API_KEY not found - embeddings will not be generated")

        # Phase 2: Media persistence configuration
        self.persist_media = os.getenv('PERSIST_ARTICLE_MEDIA', 'false').lower() == 'true'
        self.media_retention_days = int(os.getenv('MEDIA_RETENTION_DAYS', '30'))
        if self.persist_media:
            self.logger.info(f"✅ Media persistence enabled (retention: {self.media_retention_days} days)")

    async def process_article(self, url: str, user_id: Optional[str] = None, is_private: bool = False) -> str:
        """
        DEPRECATED: Use the /api/article/process-direct endpoint instead.

        This method is kept for backwards compatibility but lacks features:
        - No privacy auto-detection (must pass is_private manually)
        - No duplicate handling
        - No demo video frame support
        - No library management

        For CLI usage, use scripts/process_article_cli.py which calls the API.

        Args:
            url: URL of the article to process
            user_id: Optional user ID for authentication (Supabase auth user)
            is_private: If True, save to private_articles table (org-scoped)

        Returns:
            Article ID
        """
        import warnings
        warnings.warn(
            "process_article() is deprecated. Use /api/article/process-direct endpoint instead. "
            "See scripts/process_article_cli.py for CLI usage.",
            DeprecationWarning,
            stacklevel=2
        )
        self.logger.info(f"Processing article: {url}")
        if user_id:
            self.logger.info(f"   User ID: {user_id}")
        if is_private:
            self.logger.info(f"   Privacy: Private (org-scoped)")

        # Store user_id and privacy flag for database save
        self.current_user_id = user_id
        self.is_private = is_private

        try:
            # Step 0: Try to discover YouTube URL from content_queue
            url = await self._try_youtube_discovery(url)

            # Step 1: Extract metadata and detect content type
            if self.event_emitter:
                await self.event_emitter.emit('fetch_start', {'url': url})

            self.logger.info("1. Extracting metadata...")
            metadata = await self._extract_metadata(url)
            self.logger.info(f"   Title: {metadata['title']}")

            if self.event_emitter:
                await self.event_emitter.emit('fetch_complete', {
                    'title': metadata['title'],
                    'url': url
                })

            # Step 2: Detect media type
            if self.event_emitter:
                await self.event_emitter.emit('media_detect_start')

            # Step 2: Generate filename
            filename = sanitize_filename(metadata['title']) + '.html'
            self.logger.info(f"   Filename: {filename}")

            # Emit media detection result
            content_type = metadata.get('content_type')
            media_type = 'text-only'
            if content_type and hasattr(content_type, 'has_embedded_video') and content_type.has_embedded_video:
                media_type = 'video'
            elif content_type and hasattr(content_type, 'has_embedded_audio') and content_type.has_embedded_audio:
                media_type = 'audio'

            if self.event_emitter:
                await self.event_emitter.emit('media_detected', {'media_type': media_type})

            # Step 3: Content extraction
            if self.event_emitter:
                await self.event_emitter.emit('content_extract_start')

            # Check if we have transcript data
            transcript_method = None
            transcripts = metadata.get('transcripts', {})
            if transcripts:
                if media_type == 'video':
                    transcript_method = 'youtube'
                elif media_type == 'audio':
                    # Check if it was chunked
                    if metadata.get('audio_chunks'):
                        transcript_method = 'chunked'
                    else:
                        transcript_method = 'audio'

            if self.event_emitter:
                await self.event_emitter.emit('content_extracted', {
                    'transcript_method': transcript_method
                })

            # Step 4: AI-powered content analysis
            if self.event_emitter:
                await self.event_emitter.emit('ai_start')

            self.logger.info("2. Analyzing content with AI...")
            ai_summary = await self._generate_summary_async(url, metadata)

            if self.event_emitter:
                await self.event_emitter.emit('ai_complete')

            # Step 4b: Generate themed insights for private articles
            themed_insights_data = None
            if self.is_private and self.current_user_id:
                themed_insights_data = await self._generate_themed_insights_async(
                    user_id=self.current_user_id,
                    metadata=metadata,
                    ai_summary=ai_summary
                )

            # Step 5: Save to Supabase database
            if self.event_emitter:
                await self.event_emitter.emit('save_start')

            self.logger.info("3. Saving to Supabase database...")
            article_id = self._save_to_database(metadata, ai_summary, self.current_user_id, self.is_private, themed_insights_data)

            if self.event_emitter:
                await self.event_emitter.emit('save_complete', {
                    'article_id': article_id
                })

            self.logger.info(f"✅ Processing complete! View at: http://localhost:3000/article/{article_id}")
            return article_id

        except Exception as e:
            self.logger.error(f"❌ Processing failed: {e}")
            raise

    async def _extract_metadata(
        self,
        url: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None,
        extract_demo_frames: bool = False
    ) -> Dict:
        """
        Extract metadata and detect content type

        Args:
            url: URL to analyze
            progress_callback: Optional async callback for progress updates
            extract_demo_frames: If True, extract video frames for demo videos

        Returns:
            Dictionary containing metadata and content analysis
        """
        # Check if URL points to a direct media file (video/audio/document)
        is_media, media_type = self.content_detector.is_direct_media_url(url)
        if is_media:
            if media_type == 'document':
                self.logger.info(f"📄 [DIRECT PDF FILE] Detected direct PDF file URL")
                return await self._process_pdf_file(url, progress_callback)
            else:
                self.logger.info(f"🎥 [DIRECT MEDIA FILE] Detected direct {media_type} file URL")
                return await self._process_direct_media_file(url, media_type, progress_callback, extract_demo_frames)

        # Check if URL is a direct YouTube video link
        youtube_match = re.match(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', url)
        if youtube_match:
            self.logger.info("🎥 [DIRECT YOUTUBE] Detected direct YouTube video URL")
            return await self._process_direct_youtube_url(url, youtube_match.group(1), extract_demo_frames, progress_callback)

        # Check if URL is a direct Loom video link
        loom_match = re.match(r'(?:https?://)?(?:www\.)?loom\.com/(?:share|embed)/([a-zA-Z0-9]+)', url)
        if loom_match:
            self.logger.info("🎥 [DIRECT LOOM] Detected direct Loom video URL")
            return await self._process_direct_loom_url(url, loom_match.group(1), progress_callback, extract_demo_frames)

        # Load Chrome cookies for this specific URL domain (for Substack subdomains, etc.)
        self.auth_manager.load_cookies_for_url(url)

        # Detect platform first
        platform = self.auth_manager.detect_platform(url)

        # Check if URL already has authentication tokens - if so, skip browser fetch
        # This prevents unnecessary Playwright invocation for URLs with access_token params
        auth_required, auth_reason = self.auth_manager.check_authentication_required(url, platform)

        # Check if browser fetch is needed BEFORE making initial request (to avoid redirect loops)
        # Only skip browser fetch check if URL contains access token
        if auth_reason != "url_contains_auth_token":
            # Check domain-based browser fetch requirements (doesn't need response object)
            should_use_browser = self.auth_manager.should_use_browser_fetch(url, None)

            if should_use_browser:
                self.logger.info("🌐 [BROWSER FETCH] Domain configured for browser fetch, using Playwright...")
                # Use async version for FastAPI compatibility
                browser_success, html_content, browser_message = await self.auth_manager.fetch_with_browser_async(url)

                if browser_success:
                    soup = self._get_soup(html_content)
                    self.logger.info("✅ [BROWSER FETCH] Successfully retrieved content via browser")
                else:
                    self.logger.warning(f"⚠️ [BROWSER FETCH] Browser fetch failed: {browser_message}")
                    # Fall back to regular request
                    response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
                    soup = self._get_soup(response.content)
            else:
                # Make regular request first
                response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
                soup = self._get_soup(response.content)

                # Check response for anti-bot measures and fallback to browser if needed
                should_use_browser_fallback = self.auth_manager.should_use_browser_fetch(url, response)
                if should_use_browser_fallback:
                    self.logger.info("🌐 [BROWSER FALLBACK] Anti-bot measures detected in response, switching to browser fetch...")
                    browser_success, html_content, browser_message = await self.auth_manager.fetch_with_browser_async(url)

                    if browser_success:
                        soup = self._get_soup(html_content)
                        self.logger.info("✅ [BROWSER FALLBACK] Successfully retrieved content via browser")
                    else:
                        self.logger.warning(f"⚠️ [BROWSER FALLBACK] Browser fetch failed: {browser_message}")
                        self.logger.warning("⚠️ [BROWSER FALLBACK] Continuing with standard request content...")
        else:
            self.logger.info("✅ [SKIP BROWSER] URL contains access token, using direct request")
            # Get page content with regular request
            response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
            soup = self._get_soup(response.content)

        if auth_required:
            auth_success, auth_message = self.auth_manager.authenticate_if_needed(url, platform)
            if not auth_success:
                self.logger.warning(f"⚠️ Authentication failed: {auth_message}")
            else:
                # Re-fetch content after authentication
                response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
                soup = self._get_soup(response.content)

        # Extract basic metadata (title)
        title = self._extract_title(soup, url)

        # Emit fetch_complete callback immediately after HTML is fetched
        if progress_callback:
            await progress_callback("fetch_complete", {"title": title})

        # Detect content type
        content_type = self.content_detector.detect_content_type(soup, url)

        # Build metadata based on content type
        metadata = {
            'title': title,
            'url': url,
            'platform': platform,
            'content_type': content_type,
            'extracted_at': datetime.now().isoformat(),
            'media_info': {}
        }

        # Handle different content types
        if content_type.has_embedded_video:
            if progress_callback:
                await progress_callback("detecting_video", {"video_count": len(content_type.video_urls)})

            # Use unified optimized method for demo videos, fallback to standard for others
            if extract_demo_frames and content_type.video_urls:
                # Get first video for demo processing
                first_video = content_type.video_urls[0]
                video_platform = first_video.get('platform')
                video_id = first_video.get('video_id')
                video_url = first_video.get('url')

                self.logger.info(f"🎬 [DEMO MODE] Using unified optimized method for {video_platform} video")

                result = await self._process_demo_video_optimized(
                    video_url=video_url,
                    video_id=video_id,
                    platform=video_platform,
                    base_url=url,
                    progress_callback=progress_callback,
                    referer=url
                )

                video_frames = result.get('video_frames', [])
                transcript_data = result.get('transcript_data')

                # If unified method failed to get transcript (e.g., due to authentication), fall back to standard method
                if not transcript_data:
                    self.logger.warning(f"⚠️ [DEMO MODE] Unified method failed to get transcript for {video_platform}, falling back to standard method")
                    fallback_result = await self._process_video_content_async(
                        content_type.video_urls, soup, url, progress_callback, extract_demo_frames=False
                    )
                    # Preserve any frames we managed to extract
                    if video_frames:
                        fallback_result['video_frames'] = video_frames
                    metadata.update(fallback_result)
                else:
                    # Format transcript data to match expected structure
                    transcripts = {}
                    article_text = ''
                    formatted_transcript = {
                        'success': True,
                        'type': 'deepgram',
                        'text': transcript_data.get('text', ''),
                        'segments': transcript_data.get('segments', []),
                        'transcript': transcript_data.get('segments', []),
                        'language': transcript_data.get('language', 'en'),
                        'words': transcript_data.get('words', [])
                    }
                    transcripts[video_id] = formatted_transcript
                    article_text = transcript_data.get('text', '')

                    # Extract article text and images from page
                    page_text = self._extract_article_text_content(soup)
                    if page_text:
                        article_text = f"{article_text}\n\n{page_text}" if article_text else page_text

                    # Skip image extraction for YouTube videos (images are just other video thumbnails)
                    images = [] if video_platform == 'youtube' else self._extract_article_images(soup, url)

                    # TODO: TEMPORARY - Keep temp files for debugging
                    if result.get('temp_video_path'):
                        self.logger.info(f"💾 [TEMPORARY] Video file preserved at: {result['temp_video_path']}")
                    if result.get('temp_dir'):
                        self.logger.info(f"📂 [TEMPORARY] Temp directory preserved at: {result['temp_dir']}")

                    # Use platform-specific key (e.g., 'vimeo_urls', 'loom_urls') for correct platform detection
                    # This ensures the database platform field is set correctly (e.g., 'vimeo' not 'video')
                    video_platform = content_type.video_urls[0].get('platform', 'youtube')
                    media_key = f'{video_platform}_urls'

                    metadata.update({
                        'media_info': {media_key: content_type.video_urls},
                        'transcripts': transcripts,
                        'article_text': article_text,
                        'images': images,
                        'video_frames': video_frames
                    })
            else:
                # Standard mode: use existing async method
                metadata.update(await self._process_video_content_async(
                    content_type.video_urls, soup, url, progress_callback, extract_demo_frames
                ))
        elif content_type.has_embedded_audio:
            if progress_callback:
                await progress_callback("detecting_audio", {"audio_count": len(content_type.audio_urls)})
            metadata.update(await self._process_audio_content_async(
                content_type.audio_urls, soup, url, progress_callback
            ))
        else:
            if progress_callback:
                await progress_callback("detecting_text_only", {})
            metadata.update(self._process_text_content(soup, url))
            # Emit content_extracted for text-only articles
            if progress_callback:
                await progress_callback("content_extracted", {"transcript_method": "text"})

        return metadata

    async def _extract_metadata_from_html(
        self,
        url: str,
        html_content: str,
        title_hint: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None,
        extract_demo_frames: bool = False
    ) -> Dict:
        """
        Extract metadata from pre-provided HTML content (for Chrome extension).

        This method is used when the Chrome extension sends HTML content extracted
        from the user's browser tab. Since the content is already fetched (with the
        user's authentication), we skip all fetching/Playwright/auth steps.

        NOTE: Audio/video files are still downloaded directly by the backend since
        they're typically publicly accessible.

        Args:
            url: Original URL (for reference/metadata)
            html_content: Pre-extracted HTML content from extension
            title_hint: Optional title from browser tab
            progress_callback: Optional async callback for progress updates
            extract_demo_frames: If True, extract video frames for demo videos

        Returns:
            Dictionary containing metadata and content analysis
        """
        self.logger.info(f"📄 [EXTENSION MODE] Processing pre-provided HTML ({len(html_content)} chars)")

        # Parse the provided HTML
        soup = self._get_soup(html_content)

        # Extract basic metadata (title)
        title = self._extract_title(soup, url)
        if title_hint and not title:
            title = title_hint

        # Emit fetch_complete callback
        if progress_callback:
            await progress_callback("fetch_complete", {"title": title, "source": "extension"})

        # Detect platform from URL
        platform = self.auth_manager.detect_platform(url)

        # Detect content type from the HTML
        content_type = self.content_detector.detect_content_type(soup, url)

        # Build metadata based on content type
        metadata = {
            'title': title,
            'url': url,
            'platform': platform,
            'content_type': content_type,
            'extracted_at': datetime.now().isoformat(),
            'media_info': {},
            'source': 'extension'  # Mark that this came from extension
        }

        # Handle different content types
        if content_type.has_embedded_video:
            if progress_callback:
                await progress_callback("detecting_video", {"video_count": len(content_type.video_urls)})

            # Use standard video processing (downloads videos directly - they're usually public)
            if extract_demo_frames and content_type.video_urls:
                first_video = content_type.video_urls[0]
                video_platform = first_video.get('platform')
                video_id = first_video.get('video_id')
                video_url = first_video.get('url')

                self.logger.info(f"🎬 [EXTENSION MODE] Processing demo video from {video_platform}")

                result = await self._process_demo_video_optimized(
                    video_url=video_url,
                    video_id=video_id,
                    platform=video_platform,
                    base_url=url,
                    progress_callback=progress_callback,
                    referer=url
                )

                video_frames = result.get('video_frames', [])
                transcript_data = result.get('transcript_data')

                if not transcript_data:
                    self.logger.warning(f"⚠️ [EXTENSION MODE] Failed to get transcript, falling back")
                    fallback_result = await self._process_video_content_async(
                        content_type.video_urls, soup, url, progress_callback, extract_demo_frames=False
                    )
                    if video_frames:
                        fallback_result['video_frames'] = video_frames
                    metadata.update(fallback_result)
                else:
                    transcripts = {}
                    article_text = ''
                    formatted_transcript = {
                        'success': True,
                        'type': 'deepgram',
                        'text': transcript_data.get('text', ''),
                        'segments': transcript_data.get('segments', []),
                        'transcript': transcript_data.get('segments', []),
                        'language': transcript_data.get('language', 'en'),
                        'words': transcript_data.get('words', [])
                    }
                    transcripts[video_id] = formatted_transcript
                    article_text = transcript_data.get('text', '')

                    page_text = self._extract_article_text_content(soup)
                    if page_text:
                        article_text = f"{article_text}\n\n{page_text}" if article_text else page_text

                    images = self._extract_article_images(soup, url)
                    video_platform = content_type.video_urls[0].get('platform', 'youtube')
                    media_key = f'{video_platform}_urls'

                    metadata.update({
                        'media_info': {media_key: content_type.video_urls},
                        'transcripts': transcripts,
                        'article_text': article_text,
                        'images': images,
                        'video_frames': video_frames
                    })
            else:
                metadata.update(await self._process_video_content_async(
                    content_type.video_urls, soup, url, progress_callback, extract_demo_frames
                ))

        elif content_type.has_embedded_audio:
            if progress_callback:
                await progress_callback("detecting_audio", {"audio_count": len(content_type.audio_urls)})
            # Audio files are typically publicly accessible, download directly
            metadata.update(await self._process_audio_content_async(
                content_type.audio_urls, soup, url, progress_callback
            ))

        else:
            # Text-only content - just extract from provided HTML
            if progress_callback:
                await progress_callback("detecting_text_only", {})
            metadata.update(self._process_text_content(soup, url))
            if progress_callback:
                await progress_callback("content_extracted", {"transcript_method": "text"})

        self.logger.info(f"✅ [EXTENSION MODE] Metadata extraction complete")
        return metadata

    async def _process_demo_video_optimized(
        self,
        video_url: str,
        video_id: str,
        platform: str,
        base_url: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None,
        referer: Optional[str] = None
    ) -> Dict:
        """
        Unified optimized method for demo video processing across all platforms.
        Downloads video once, then extracts both frames and audio from it.

        This method is used by all platforms (YouTube, Loom, Vimeo, Wistia, Direct Media)
        when extract_demo_frames=True to avoid duplicate downloads.

        Args:
            video_url: The video URL to download
            video_id: Platform-specific video ID
            platform: Platform name (youtube, loom, vimeo, wistia, direct)
            base_url: Base URL for frame context
            progress_callback: Optional async callback for progress updates
            referer: Optional referer header for download

        Returns:
            Dictionary containing:
                - video_frames: List of extracted frames with Supabase URLs
                - transcript_data: Transcribed text with segments
                - transcript_text: Plain text transcript
                - temp_video_path: Path to downloaded video (for cleanup)
                - temp_dir: Temp directory path (for cleanup)
        """
        self.logger.info(f"🎬 [DEMO VIDEO OPTIMIZED] Processing {platform} video: {video_id}")

        video_frames = []
        transcript_data = None
        transcript_text = ''
        temp_video_path = None
        temp_dir = None

        try:
            # Step 1: Download full video (not just audio)
            if progress_callback:
                await progress_callback("downloading_video", {
                    "message": f"Downloading {platform} video for frame extraction..."
                })

            import tempfile
            temp_dir = tempfile.mkdtemp(prefix="demo_video_")
            temp_template = os.path.join(temp_dir, f'video_{video_id}')

            # For Vimeo and Loom, use embed URL (more likely to work without auth)
            download_url = video_url
            if platform == 'vimeo':
                download_url = f'https://player.vimeo.com/video/{video_id}'
                self.logger.info(f"🎬 [VIMEO] Using embed URL for download: {download_url}")
            elif platform == 'loom':
                download_url = f'https://www.loom.com/embed/{video_id}'
                self.logger.info(f"🎬 [LOOM] Using embed URL for download: {download_url}")

            self.logger.info(f"📥 [DEMO VIDEO OPTIMIZED] Downloading video from {platform}...")
            temp_video_path = self._download_video_with_ytdlp(
                download_url,
                temp_template,
                referer=referer,
                download_video=True  # Download full video, not just audio
            )

            if not temp_video_path:
                self.logger.error(f"❌ [DEMO VIDEO OPTIMIZED] Failed to download video")
                return {
                    'video_frames': [],
                    'transcript_data': None,
                    'transcript_text': '',
                    'temp_video_path': None,
                    'temp_dir': temp_dir
                }

            self.logger.info(f"✅ [DEMO VIDEO OPTIMIZED] Video downloaded: {temp_video_path}")

            # Step 2: Extract audio from downloaded video
            if progress_callback:
                await progress_callback("extracting_audio", {
                    "message": "Extracting audio from video..."
                })

            self.logger.info(f"🎵 [DEMO VIDEO OPTIMIZED] Extracting audio from video...")
            audio_temp_path = await self._extract_audio_from_video(temp_video_path, progress_callback=progress_callback)

            if not audio_temp_path:
                self.logger.warning(f"⚠️ [DEMO VIDEO OPTIMIZED] Failed to extract audio - video may have no audio track")
                self.logger.info(f"ℹ️ [DEMO VIDEO OPTIMIZED] Continuing with frame extraction only (no transcription)")
            else:
                self.logger.info(f"✅ [DEMO VIDEO OPTIMIZED] Audio extracted: {audio_temp_path}")

                # Step 3: Transcribe the extracted audio
                # Get audio file size for progress reporting
                audio_file_size_mb = os.path.getsize(audio_temp_path) / (1024 * 1024) if os.path.exists(audio_temp_path) else 0

                if progress_callback:
                    await progress_callback("transcribing_audio", {
                        "message": "Transcribing audio with DeepGram...",
                        "file_size_mb": audio_file_size_mb
                    })

                self.logger.info(f"📝 [DEMO VIDEO OPTIMIZED] Transcribing audio...")
                result = await self._transcribe_audio_with_size_check(
                    audio_temp_path,
                    media_type='video',
                    progress_callback=progress_callback
                )

                if result and result.get('transcript_data'):
                    transcript_data = result['transcript_data']
                    transcript_text = transcript_data.get('text', '')
                    self.logger.info(f"✅ [DEMO VIDEO OPTIMIZED] Transcription successful ({len(transcript_text)} chars)")
                else:
                    self.logger.warning(f"⚠️ [DEMO VIDEO OPTIMIZED] Transcription failed or empty")

            # Step 4: Extract frames from video
            if progress_callback:
                await progress_callback("extracting_frames", {
                    "message": "Extracting video frames..."
                })

            self.logger.info(f"🖼️ [DEMO VIDEO OPTIMIZED] Extracting frames...")
            video_frames = await self._extract_and_upload_frames(temp_video_path, base_url)
            self.logger.info(f"✅ [DEMO VIDEO OPTIMIZED] Extracted {len(video_frames)} frames")

            return {
                'video_frames': video_frames,
                'transcript_data': transcript_data,
                'transcript_text': transcript_text,
                'temp_video_path': temp_video_path,
                'temp_dir': temp_dir
            }

        except Exception as e:
            self.logger.error(f"❌ [DEMO VIDEO OPTIMIZED] Failed: {e}", exc_info=True)
            return {
                'video_frames': [],
                'transcript_data': None,
                'transcript_text': '',
                'temp_video_path': temp_video_path,
                'temp_dir': temp_dir
            }

    async def _process_direct_loom_url(
        self,
        url: str,
        video_id: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None,
        extract_demo_frames: bool = False
    ) -> Dict:
        """
        Process a direct Loom video URL (e.g., https://www.loom.com/share/xyz)

        Args:
            url: The Loom video URL
            video_id: Extracted Loom video ID
            progress_callback: Optional async callback for progress updates
            extract_demo_frames: If True, download video and extract frames

        Returns:
            Dictionary containing metadata for direct Loom video with transcript
        """
        self.logger.info(f"   📹 [LOOM VIDEO] Processing video ID: {video_id}")

        # Try to get video title from Loom page
        try:
            response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
            soup = self._get_soup(response.content)
            title = self._extract_title(soup, url)
        except:
            title = f"Loom Video: {video_id}"

        # Create video URL dict in expected format
        video_urls = [{
            'video_id': video_id,
            'url': url,
            'platform': 'loom',
            'context': 'direct_url',
            'relevance_score': 1.0
        }]

        # Process video using unified optimized method or standard fallback
        video_frames = []
        transcripts = {}
        article_text = ''

        if extract_demo_frames:
            # Use unified optimized method for demo mode
            result = await self._process_demo_video_optimized(
                video_url=url,
                video_id=video_id,
                platform='loom',
                base_url=url,
                progress_callback=progress_callback,
                referer=url
            )

            video_frames = result.get('video_frames', [])
            transcript_data = result.get('transcript_data')

            if transcript_data:
                formatted_transcript = {
                    'success': True,
                    'type': 'deepgram',
                    'text': transcript_data.get('text', ''),
                    'segments': transcript_data.get('segments', []),
                    'transcript': transcript_data.get('segments', []),
                    'language': transcript_data.get('language', 'en'),
                    'words': transcript_data.get('words', [])
                }
                transcripts[video_id] = formatted_transcript
                article_text = transcript_data.get('text', '')

            # TODO: TEMPORARY - Keep temp files for debugging
            if result.get('temp_video_path'):
                self.logger.info(f"💾 [TEMPORARY] Video file preserved at: {result['temp_video_path']}")
            if result.get('temp_dir'):
                self.logger.info(f"📂 [TEMPORARY] Temp directory preserved at: {result['temp_dir']}")
        else:
            # Standard path: audio-only download (no frame extraction)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup('', 'html.parser')
            video_data = await self._process_video_content_async(
                video_urls, soup, url, progress_callback, extract_demo_frames=False
            )
            transcripts = video_data.get('transcripts', {})
            article_text = video_data.get('article_text', '')

        return {
            'title': title,
            'url': url,
            'platform': 'loom',
            'content_type': type('obj', (object,), {
                'has_embedded_video': True,
                'has_embedded_audio': False,
                'is_text_only': False
            })(),
            'extracted_at': datetime.now().isoformat(),
            'media_info': {'loom_urls': video_urls},
            'transcripts': transcripts,
            'article_text': article_text,
            'images': [],
            'video_frames': video_frames
        }

    async def _process_direct_media_file(
        self,
        url: str,
        media_type: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None,
        extract_demo_frames: bool = False
    ) -> Dict:
        """
        Process a direct media file URL (video or audio file)

        Args:
            url: URL of the media file
            media_type: 'video' or 'audio'
            progress_callback: Optional async callback for progress updates
            extract_demo_frames: If True and media_type is video, extract frames

        Returns:
            Dict with metadata and transcript data
        """
        import tempfile
        import os
        from urllib.parse import urlparse, unquote

        self.logger.info(f"📥 [DIRECT {media_type.upper()} FILE] Processing direct media file...")

        # Extract filename from URL
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = os.path.basename(path) or f"media_file.{media_type[:3]}"

        # Generate a simple title from the filename
        title = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
        self.logger.info(f"📝 [TITLE] Extracted title from filename: {title}")

        # Set source as 'Direct Upload' for all uploaded media files
        source = 'Direct Upload'

        # Emit progress
        if progress_callback:
            await progress_callback("fetch_complete", {"title": title})

        # Use unified optimized method for demo videos, standard path for audio-only
        transcripts = {}
        article_text = ''
        video_frames = []

        try:
            if extract_demo_frames and media_type == 'video':
                # DEMO MODE: Use unified method (download video once for frames + transcription)
                self.logger.info(f"🎬 [DEMO MODE] Using unified optimized method for direct media file...")
                if progress_callback:
                    await progress_callback("download_start", {"filename": filename, "mode": "demo"})

                result = await self._process_demo_video_optimized(
                    video_url=url,
                    video_id='direct_file',
                    platform='direct_file',
                    base_url=url,
                    progress_callback=progress_callback,
                    referer=None
                )

                video_frames = result.get('video_frames', [])
                transcript_data = result.get('transcript_data')

                if transcript_data:
                    transcripts = {
                        'direct_file': {
                            'success': True,
                            'text': transcript_data.get('text', ''),
                            'segments': transcript_data.get('segments', []),
                            'duration': transcript_data.get('duration'),
                            'source': 'deepgram',
                            'type': 'deepgram',
                            'words': transcript_data.get('words', [])
                        }
                    }
                    article_text = transcript_data.get('text', '')

                # TODO: TEMPORARY - Keep temp files
                if result.get('temp_video_path'):
                    self.logger.info(f"💾 [TEMPORARY] Video file preserved at: {result['temp_video_path']}")
                if result.get('temp_dir'):
                    self.logger.info(f"📂 [TEMPORARY] Temp directory preserved at: {result['temp_dir']}")

            else:
                # STANDARD MODE: Download audio only (more efficient, no frames needed)
                self.logger.info(f"⬇️ [STANDARD MODE] Downloading {media_type} with yt-dlp (audio extraction)...")
                if progress_callback:
                    await progress_callback("download_start", {"filename": filename})

                # Use yt-dlp to download - it will extract only audio for video files
                temp_template = os.path.join(tempfile.gettempdir(), f"direct_media_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                audio_path = self._download_video_with_ytdlp(url, temp_template)

                if not audio_path:
                    raise Exception("Failed to download media file with yt-dlp")

                temp_path = audio_path
                self.logger.info(f"✅ [DOWNLOAD] Audio downloaded to: {temp_path}")

                if progress_callback:
                    await progress_callback("download_complete", {"path": temp_path})

                # Use FileTranscriber to extract audio and transcribe
                if not self.file_transcriber:
                    raise Exception("FileTranscriber not available - cannot process media files")

                self.logger.info(f"🎙️ [TRANSCRIBE] Extracting audio and transcribing...")
                if progress_callback:
                    await progress_callback("transcribe_start", {})

                # Use centralized transcription method with automatic size checking and chunking
                transcript_result = await self._transcribe_audio_with_size_check(
                    temp_path,
                    media_type='direct_file',
                    progress_callback=progress_callback
                )

                # Clean up the audio temporary file
                try:
                    os.unlink(temp_path)
                    self.logger.info(f"🗑️ [CLEANUP] Removed temporary audio file: {temp_path}")
                except Exception as e:
                    self.logger.warning(f"⚠️ [CLEANUP] Failed to remove temp file: {e}")

                # Handle case where video has no audio track
                if transcript_result is None:
                    self.logger.warning(f"⚠️ [{media_type.upper()}] No audio track found - will process without transcription")
                    if progress_callback:
                        await progress_callback("no_audio_track", {"reason": "Video file has no audio track"})
                elif not transcript_result:
                    raise Exception("Transcription failed")
                else:
                    # Extract transcript data
                    transcript_data = transcript_result.get('transcript_data', {})
                    transcript_text = transcript_data.get('text', '')
                    transcripts = {
                        'direct_file': {
                            'success': True,
                            'text': transcript_text,
                            'segments': transcript_data.get('segments', []),
                            'duration': transcript_data.get('duration'),
                            'source': 'deepgram',
                            'type': 'deepgram'
                        }
                    }
                # Use transcript text as article_text for AI analysis
                article_text = transcript_text
                if progress_callback:
                    await progress_callback("transcribe_complete", {"word_count": len(transcript_text.split())})

            # Build ContentType object
            from core.content_detector import ContentType
            content_type = ContentType()
            content_type.is_text_only = False

            # Set flags based on what the web app needs to DISPLAY
            # (DeepGram always transcribes audio regardless - we extract audio from MP4)
            # Since VideoContextBuilder and AudioContextBuilder are now unified (MediaContextBuilder),
            # we just set the flag based on what player the web app should show
            if media_type == 'video':
                # MP4 file → show video player in web app
                content_type.has_embedded_video = True
                content_type.has_embedded_audio = False
                content_type.video_urls = [{
                    'url': url,
                    'platform': 'direct_file',
                    'video_id': 'direct_file',  # Special marker for HTML5 video
                    'context': f'direct_{media_type}_file'
                }]
                media_info = {
                    'video_urls': [{
                        'url': url,
                        'platform': 'direct_file',
                        'video_id': 'direct_file',
                        'context': f'direct_{media_type}_file'
                    }]
                }
            else:
                # MP3/audio file → show audio player in web app
                content_type.has_embedded_video = False
                content_type.has_embedded_audio = True
                content_type.audio_urls = [{
                    'url': url,
                    'platform': 'direct_file',
                    'context': f'direct_{media_type}_file'
                }]
                media_info = {
                    'audio_urls': [{
                        'url': url,
                        'platform': 'direct_file',
                        'context': f'direct_{media_type}_file'
                    }]
                }

            return {
                'url': url,
                'title': title,
                'source': source,
                'content_type': content_type,
                'media_info': media_info,
                'transcripts': transcripts,
                'article_text': article_text,
                'images': [],
                'video_frames': video_frames
            }

        except Exception as e:
            self.logger.error(f"❌ [ERROR] Failed to process media file: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise

    async def _process_pdf_file(
        self,
        url: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None
    ) -> Dict:
        """
        Process a PDF file URL and extract text content

        Args:
            url: URL of the PDF file
            progress_callback: Optional async callback for progress updates

        Returns:
            Dict with metadata and extracted text content
        """
        import tempfile
        import os
        import requests
        from urllib.parse import urlparse, unquote
        from pypdf import PdfReader

        self.logger.info(f"📄 [PDF] Processing PDF file...")

        # Extract filename from URL
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = os.path.basename(path) or "document.pdf"

        # Generate a simple title from the filename
        title = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
        self.logger.info(f"📝 [TITLE] Extracted title from filename: {title}")

        # Emit progress
        if progress_callback:
            await progress_callback("fetch_complete", {"title": title})

        try:
            # Download PDF file
            self.logger.info(f"⬇️ [PDF] Downloading PDF file...")
            if progress_callback:
                await progress_callback("download_start", {"filename": filename})

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                temp_pdf.write(response.content)
                temp_path = temp_pdf.name

            self.logger.info(f"✅ [PDF] Downloaded to: {temp_path}")
            file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
            self.logger.info(f"📊 [PDF] File size: {file_size_mb:.2f}MB")

            if progress_callback:
                await progress_callback("download_complete", {"path": temp_path, "size_mb": file_size_mb})

            # Extract text from PDF
            self.logger.info(f"📝 [PDF] Extracting text content...")
            if progress_callback:
                await progress_callback("extracting_text", {"message": "Extracting text from PDF..."})

            reader = PdfReader(temp_path)
            num_pages = len(reader.pages)
            self.logger.info(f"📄 [PDF] PDF has {num_pages} pages")

            # Extract text from all pages
            text_content = []
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_content.append(page_text)

                    # Log progress every 10 pages
                    if page_num % 10 == 0:
                        self.logger.info(f"📄 [PDF] Processed {page_num}/{num_pages} pages...")
                except Exception as e:
                    self.logger.warning(f"⚠️ [PDF] Failed to extract text from page {page_num}: {e}")

            article_text = "\n\n".join(text_content)
            word_count = len(article_text.split())

            self.logger.info(f"✅ [PDF] Text extraction complete: {word_count} words from {num_pages} pages")

            # Truncate if exceeds limit (consistent with text article processing)
            if word_count > Config.MAX_ARTICLE_WORDS:
                article_text = ' '.join(article_text.split()[:Config.MAX_ARTICLE_WORDS]) + '...'
                self.logger.info(f"📄 [PDF] Truncated to {Config.MAX_ARTICLE_WORDS} words for processing")

            if progress_callback:
                await progress_callback("content_extracted", {
                    "pages": num_pages,
                    "word_count": word_count,
                    "transcript_method": None  # No transcript for PDFs
                })

            # Clean up temp file
            try:
                os.unlink(temp_path)
                self.logger.info(f"🗑️ [CLEANUP] Removed temporary PDF file")
            except Exception as e:
                self.logger.warning(f"⚠️ [CLEANUP] Failed to remove temp file: {e}")

            # Build ContentType object for text-only content
            from core.content_detector import ContentType
            content_type = ContentType()
            content_type.is_text_only = True
            content_type.has_embedded_video = False
            content_type.has_embedded_audio = False

            return {
                'url': url,
                'title': title,
                'source': 'Direct Upload',  # User-friendly source for uploaded files
                'content_type': content_type,
                'media_info': {},
                'transcripts': {},  # No transcripts for PDFs
                'article_text': article_text,
                'video_frames': [],
                'pdf_metadata': {
                    'num_pages': num_pages,
                    'word_count': word_count,
                    'file_size_mb': file_size_mb
                }
            }

        except Exception as e:
            self.logger.error(f"❌ [PDF ERROR] Failed to process PDF file: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise

    async def _process_direct_youtube_url(
        self,
        url: str,
        video_id: str,
        extract_demo_frames: bool = False,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None
    ) -> Dict:
        """
        Process a direct YouTube video URL (e.g., https://www.youtube.com/watch?v=xyz)

        Args:
            url: The YouTube video URL
            video_id: Extracted YouTube video ID
            extract_demo_frames: If True, download video and extract frames
            progress_callback: Optional async callback for progress updates

        Returns:
            Dictionary containing metadata for direct YouTube video
        """
        self.logger.info(f"   📹 [YOUTUBE VIDEO] Processing video ID: {video_id}")

        # Try to get video title from YouTube
        try:
            response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
            soup = self._get_soup(response.content)
            title = self._extract_title(soup, url)
        except:
            title = f"YouTube Video: {video_id}"

        # Emit fetch_complete after title extraction
        if progress_callback:
            await progress_callback("fetch_complete", {"title": title})

        # For demo mode, use unified optimized method (download once for frames + audio)
        # For standard mode, try native transcript first, then fallback to DeepGram
        transcripts = {}
        article_text = ""
        video_frames = []

        if extract_demo_frames:
            # DEMO MODE: Try native transcript first (fast, free, high quality)
            self.logger.info(f"   🎥 [DEMO MODE] Trying native YouTube transcript first...")
            transcript_data = self.transcript_processor.get_youtube_transcript(video_id)

            if transcript_data and transcript_data.get('success'):
                # Native transcript available - use it + download video for frames only
                transcripts[video_id] = transcript_data
                self.logger.info(f"      ✓ Using native transcript ({transcript_data.get('type', 'unknown')})")

                if 'transcript' in transcript_data:
                    article_text = ' '.join([entry['text'] for entry in transcript_data['transcript']])

                # Download video for frame extraction only (audio already transcribed via API)
                self.logger.info("🎬 [DEMO MODE] Native transcript found, downloading video for frames only...")
                try:
                    video_temp_path = await self._download_video_for_frames(url)
                    if video_temp_path:
                        video_frames = await self._extract_and_upload_frames(video_temp_path, url)
                        self.logger.info(f"✅ [DEMO MODE] Extracted {len(video_frames)} frames")

                        # Clean up
                        try:
                            import shutil
                            temp_dir = os.path.dirname(video_temp_path)
                            shutil.rmtree(temp_dir)
                        except Exception as e:
                            self.logger.warning(f"⚠️ Failed to cleanup: {e}")
                    else:
                        self.logger.warning("⚠️ [DEMO MODE] Could not download video for frames")
                except Exception as e:
                    self.logger.error(f"❌ [DEMO MODE] Frame extraction failed: {e}")
            else:
                # No native transcript - use unified method (download once for frames + transcription)
                error_msg = transcript_data.get('error', 'Unknown error') if transcript_data else 'Unknown error'
                self.logger.info(f"      ✗ No native transcript: {error_msg}")
                self.logger.info(f"      🎬 [DEMO MODE] Using unified optimized method...")

                result = await self._process_demo_video_optimized(
                    video_url=url,
                    video_id=video_id,
                    platform='youtube',
                    base_url=url,
                    progress_callback=progress_callback,
                    referer=None
                )

                video_frames = result.get('video_frames', [])
                transcript_data_unified = result.get('transcript_data')

                if transcript_data_unified:
                    formatted_transcript = {
                        'success': True,
                        'type': 'deepgram',
                        'text': transcript_data_unified.get('text', ''),
                        'segments': transcript_data_unified.get('segments', []),
                        'transcript': transcript_data_unified.get('segments', []),
                        'language': transcript_data_unified.get('language', 'en'),
                        'words': transcript_data_unified.get('words', [])
                    }
                    transcripts[video_id] = formatted_transcript
                    article_text = transcript_data_unified.get('text', '')

                # TODO: TEMPORARY - Keep temp files
                if result.get('temp_video_path'):
                    self.logger.info(f"💾 [TEMPORARY] Video file preserved at: {result['temp_video_path']}")
                if result.get('temp_dir'):
                    self.logger.info(f"📂 [TEMPORARY] Temp directory preserved at: {result['temp_dir']}")
        else:
            # STANDARD MODE: Try native transcript, fallback to DeepGram audio-only
            self.logger.info(f"   🎥 [STANDARD MODE] Extracting YouTube transcript for video: {video_id}")
            transcript_data = self.transcript_processor.get_youtube_transcript(video_id)

            if transcript_data and transcript_data.get('success'):
                transcripts[video_id] = transcript_data
                self.logger.info(f"      ✓ Transcript extracted ({transcript_data.get('type', 'unknown')})")

                if 'transcript' in transcript_data:
                    article_text = ' '.join([entry['text'] for entry in transcript_data['transcript']])
                    self.logger.info(f"      ✓ Extracted {len(article_text)} characters from transcript")
            else:
                error_msg = transcript_data.get('error', 'Unknown error') if transcript_data else 'Unknown error'
                self.logger.info(f"      ✗ No YouTube transcript available: {error_msg}")
                self.logger.info(f"      🎵 [FALLBACK] Attempting DeepGram transcription for video...")

                audio_url = self._extract_youtube_audio_url(video_id)
                if audio_url:
                    self.logger.info(f"      🎵 [FALLBACK] Transcribing audio with DeepGram...")
                    transcript_data = await self._download_and_transcribe_media_async(audio_url, "video")
                    if transcript_data:
                        transcripts[video_id] = transcript_data
                        self.logger.info(f"      ✓ Video transcription successful via DeepGram")

                        if 'transcript' in transcript_data:
                            article_text = ' '.join([entry['text'] for entry in transcript_data['transcript']])
                            self.logger.info(f"      ✓ Extracted {len(article_text)} characters from DeepGram transcript")
                    else:
                        self.logger.info(f"      ✗ DeepGram transcription failed")
                else:
                    self.logger.info(f"      ✗ Could not extract audio URL from YouTube")
                    self.logger.info(f"      ℹ️ [FALLBACK] Proceeding with title and metadata only")

        # Create video URL dict in expected format
        video_urls = [{
            'video_id': video_id,
            'url': url,
            'platform': 'youtube',
            'context': 'direct_url',
            'relevance_score': 1.0
        }]

        # Emit content_extracted event with transcript method
        if progress_callback:
            transcript_method = 'youtube' if transcripts else None
            await progress_callback("content_extracted", {"transcript_method": transcript_method})

        return {
            'title': title,
            'url': url,
            'platform': 'youtube',
            'content_type': type('obj', (object,), {
                'has_embedded_video': True,
                'has_embedded_audio': False,
                'is_text_only': False
            })(),
            'extracted_at': datetime.now().isoformat(),
            'media_info': {'youtube_urls': video_urls},
            'transcripts': transcripts,
            'article_text': article_text,
            'images': [],  # Skip images for YouTube - they're just other video thumbnails
            'video_frames': video_frames
        }

    async def _process_video_content_async(
        self,
        video_urls: List[Dict],
        soup,
        base_url: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None,
        extract_demo_frames: bool = False
    ) -> Dict:
        """
        Async version: Process content with single validated video with progress callbacks

        Args:
            video_urls: List of video URLs detected
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            progress_callback: Optional async callback for progress updates
            extract_demo_frames: If True, extract video frames for demo videos

        Returns:
            Dict with transcripts, article_text, images, and video_frames
        """
        # Should only receive 1 validated video from detection logic
        if not video_urls:
            self.logger.info("   No validated videos to process")
            return {'media_info': {'youtube_urls': []}, 'transcripts': {}}

        if len(video_urls) > 1:
            self.logger.warning(f"   ⚠️ [UNEXPECTED] Received {len(video_urls)} videos, expected 1. Using first video only.")

        # Process only the first (and should be only) video
        video = video_urls[0]
        video_id = video.get('video_id', 'N/A')
        platform = video.get('platform', 'unknown')
        score = video.get('relevance_score', 'N/A')
        context = video.get('context', 'unknown')

        self.logger.info(f"   Processing single validated video: Platform={platform} | ID={video_id} | Score={score} | Context={context}")

        # Signal start of content extraction (for UI progress)
        if progress_callback:
            await progress_callback("content_extract_start", {})

        if progress_callback:
            await progress_callback("processing_video", {"video_id": video_id})

        # Extract transcript for the single video based on platform
        transcripts = {}
        self.logger.info(f"      🎥 [EXTRACTING] {platform.title()} video: {video_id}")

        # Step 1: Try platform-specific transcript extraction (only YouTube has a native API)
        transcript_data = None

        if platform == 'youtube':
            transcript_data = self.transcript_processor.get_youtube_transcript(video_id)
        else:
            # For other platforms (Loom, Vimeo, etc.), we don't have native transcript support
            self.logger.info(f"      ℹ️ No native transcript API for platform: {platform}, will use generic fallback")

        # Check if platform-specific transcript worked
        if transcript_data and transcript_data.get('success'):
            transcripts[video_id] = transcript_data
            self.logger.info(f"      ✓ Transcript extracted ({transcript_data.get('type', 'unknown')})")
        else:
            # Step 2: GENERIC FALLBACK - works for ANY platform
            error_msg = transcript_data.get('error', 'Unknown error') if transcript_data else 'No native transcript'
            self.logger.info(f"      ✗ No {platform} transcript available: {error_msg}")
            self.logger.info(f"      🎵 [FALLBACK] Attempting audio extraction and transcription with DeepGram...")

            if progress_callback:
                await progress_callback("video_fallback_deepgram", {"video_id": video_id})

            # Try to download audio using yt-dlp (supports many platforms and HLS streams)
            try:
                import tempfile
                import os

                # Send progress callback: downloading audio
                if progress_callback:
                    await progress_callback("downloading_audio", {"video_id": video_id})

                # Create temp file template (don't create the file, just get a path)
                temp_dir = tempfile.gettempdir()
                temp_template = os.path.join(temp_dir, f'ytdlp_audio_{video_id}')

                # For platforms like Vimeo, try embed URL first (often publicly accessible)
                # Fall back to direct URL if embed fails
                urls_to_try = []

                if platform == 'vimeo':
                    # Try embed URL first for Vimeo (more likely to work without auth)
                    embed_url = f'https://player.vimeo.com/video/{video_id}'
                    direct_url = f'https://vimeo.com/{video_id}'
                    urls_to_try = [embed_url, direct_url]
                    self.logger.info(f"      🎵 [VIMEO] Will try embed URL first, then direct URL")
                elif platform == 'loom':
                    # Try embed URL first for Loom (more reliable)
                    embed_url = f'https://www.loom.com/embed/{video_id}'
                    direct_url = f'https://www.loom.com/share/{video_id}'
                    urls_to_try = [embed_url, direct_url]
                    self.logger.info(f"      🎵 [LOOM] Will try embed URL first, then direct URL")
                elif platform == 'html5_video':
                    # For HTML5 video, use the direct URL from the video object (e.g., Q4 Inc MP4 files)
                    video_url = video.get('url')
                    if video_url:
                        urls_to_try = [video_url]
                        self.logger.info(f"      🎵 [HTML5] Using direct video URL: {video_url[:80]}...")
                    else:
                        self.logger.error(f"      ❌ [HTML5] No URL found in video object")
                        urls_to_try = []
                else:
                    # For other platforms, use the standard URL
                    urls_to_try = [self._build_video_url(platform, video_id)]

                temp_path = None
                last_error = None

                for idx, video_url in enumerate(urls_to_try):
                    self.logger.info(f"      🎵 [FALLBACK] Attempt {idx + 1}/{len(urls_to_try)}: {video_url[:80]}...")

                    # Download using yt-dlp (handles HLS streams properly)
                    # Pass base_url as referer for embedded videos (helps with Vimeo)
                    temp_path = self._download_video_with_ytdlp(video_url, temp_template, referer=base_url)
                    if temp_path:
                        break  # Success! Stop trying
                    else:
                        last_error = f"Failed to download from {video_url[:50]}..."
                        self.logger.info(f"      ⚠️ Attempt {idx + 1} failed, trying next URL...")
                if temp_path:
                    # Check if file is empty
                    file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
                    if file_size_mb == 0:
                        self.logger.warning(f"      ✗ Downloaded file is empty (0MB)")
                    else:
                        # Transcribe the downloaded file
                        self.logger.info(f"      🎵 [FALLBACK] Transcribing audio with DeepGram...")

                        if not self.file_transcriber:
                            self.logger.warning("   ⚠️ File transcriber not available")
                        else:
                            # Use centralized transcription method with automatic size checking and chunking
                            result = await self._transcribe_audio_with_size_check(
                                temp_path,
                                media_type='video',
                                progress_callback=progress_callback
                            )

                            if result and result.get('transcript_data'):
                                transcript_data = result['transcript_data']

                                # Format to match expected structure for video transcripts
                                formatted_transcript = {
                                    'success': True,
                                    'type': 'deepgram',
                                    'text': transcript_data.get('text', ''),
                                    'segments': transcript_data.get('segments', []),
                                    'transcript': transcript_data.get('segments', []),  # Also use 'transcript' key for consistency
                                    'language': transcript_data.get('language', 'en'),
                                    'words': transcript_data.get('words', [])  # Include word-level data for frame extraction
                                }
                                transcripts[video_id] = formatted_transcript
                                self.logger.info(f"      ✓ Video transcription successful via DeepGram")
                            else:
                                self.logger.info(f"      ✗ DeepGram transcription failed")

                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                else:
                    self.logger.info(f"      ✗ Could not download audio from {platform} video")
                    self.logger.info(f"      ℹ️ [INFO] {platform.title()} videos may require authentication or may not be supported by yt-dlp")
            except Exception as e:
                self.logger.warning(f"      ✗ yt-dlp download/transcription failed: {e}")

        # Always extract article text content
        self.logger.info("   📄 [ARTICLE TEXT] Extracting article text content...")
        article_text = self._extract_article_text_content(soup)
        if article_text:
            word_count = len(article_text.split())
            self.logger.info(f"   📄 [ARTICLE TEXT] Extracted {word_count} words of article content")

            # Limit text size for prompt efficiency
            if word_count > Config.MAX_ARTICLE_WORDS:
                article_text = ' '.join(article_text.split()[:Config.MAX_ARTICLE_WORDS]) + '...'
                self.logger.info(f"   📄 [ARTICLE TEXT] Truncated to {Config.MAX_ARTICLE_WORDS} words for processing")
        else:
            self.logger.info("   ⚠️ [ARTICLE TEXT] No readable article content found")

        # Extract images from article (skip for YouTube - images are just other video thumbnails)
        images = [] if platform == 'youtube' else self._extract_article_images(soup, base_url)

        # IMPORTANT: _process_video_content_async should NOT be used for demo videos anymore.
        # Demo videos should use _process_demo_video_optimized directly for efficiency.
        # This code path is only for backward compatibility and will be removed.
        video_frames = []
        if extract_demo_frames:
            self.logger.warning("⚠️ [DEPRECATED] _process_video_content_async called with extract_demo_frames=True")
            self.logger.warning("⚠️ [DEPRECATED] Use _process_demo_video_optimized instead for better efficiency")
            # Still support it for now but log deprecation warning

        # Determine transcript method for frontend
        transcript_method = None
        if transcripts:
            # Check what type of transcript we got
            first_transcript = list(transcripts.values())[0] if transcripts else None
            if first_transcript:
                transcript_type = first_transcript.get('type', 'unknown')
                # Map internal type to frontend-expected method
                if transcript_type == 'youtube' or transcript_type == 'youtube_generated':
                    transcript_method = 'youtube'
                elif transcript_type == 'deepgram':
                    transcript_method = 'audio'  # DeepGram transcription
                else:
                    transcript_method = 'youtube'  # Default for videos

        # Emit completion event with transcript_method
        if progress_callback:
            await progress_callback("content_extracted", {
                "transcript_method": transcript_method
            })

        # Determine the key based on platform
        platform = video_urls[0].get('platform', 'youtube') if video_urls else 'youtube'
        media_key = f'{platform}_urls'

        return {
            'media_info': {media_key: video_urls},
            'transcripts': transcripts,
            'article_text': article_text or 'Content not available',
            'images': images,
            'video_frames': video_frames
        }

    async def _process_audio_content_async(
        self,
        audio_urls: List[Dict],
        soup,
        base_url: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None
    ) -> Dict:
        """
        Async version: Process content with embedded audio with progress callbacks

        Args:
            audio_urls: List of audio URLs detected
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            progress_callback: Optional async callback for progress updates

        Returns:
            Dict with transcripts, article_text, and images
        """
        self.logger.info("   Found embedded audio content...")

        # Signal start of content extraction (for UI progress)
        if progress_callback:
            await progress_callback("content_extract_start", {})

        # Try to transcribe audio if available
        transcripts = {}
        if audio_urls:
            for idx, audio in enumerate(audio_urls):
                audio_url = audio.get('url')
                if audio_url:
                    self.logger.info(f"   🎵 [AUDIO {idx+1}] Attempting transcription...")

                    if progress_callback:
                        await progress_callback("processing_audio", {
                            "audio_index": idx + 1,
                            "total_audios": len(audio_urls)
                        })

                    transcript_data = await self._download_and_transcribe_media_async(
                        audio_url,
                        "audio",
                        progress_callback=progress_callback
                    )
                    if transcript_data:
                        transcripts[f"audio_{idx}"] = transcript_data
                        self.logger.info(f"   ✓ Audio transcription successful")
                    else:
                        self.logger.info(f"   ✗ Audio transcription failed")

        # Always extract article text content
        self.logger.info("   📄 [ARTICLE TEXT] Extracting article text content...")
        article_text = self._extract_article_text_content(soup)
        if article_text:
            word_count = len(article_text.split())
            self.logger.info(f"   📄 [ARTICLE TEXT] Extracted {word_count} words of article content")

            # Limit text size for prompt efficiency
            if word_count > Config.MAX_ARTICLE_WORDS:
                article_text = ' '.join(article_text.split()[:Config.MAX_ARTICLE_WORDS]) + '...'
                self.logger.info(f"   📄 [ARTICLE TEXT] Truncated to {Config.MAX_ARTICLE_WORDS} words for processing")
        else:
            self.logger.info("   ⚠️ [ARTICLE TEXT] No readable article content found")

        # Extract images from article
        images = self._extract_article_images(soup, base_url)

        # Determine transcript method for frontend
        transcript_method = None
        if transcripts:
            # Check what type of transcript we got and if it was chunked
            first_transcript = list(transcripts.values())[0] if transcripts else None
            if first_transcript:
                # For audio content, check if chunking was used
                # (chunking info would be in the metadata, but we can infer from transcript structure)
                transcript_method = 'audio'  # Audio transcription

        # Emit completion event with transcript_method
        if progress_callback:
            await progress_callback("content_extracted", {
                "transcript_method": transcript_method
            })

        return {
            'media_info': {'audio_urls': audio_urls},
            'transcripts': transcripts if transcripts else {},
            'article_text': article_text or 'Content not available',
            'images': images
        }

    def _process_text_content(self, soup, base_url: str) -> Dict:
        """Process text-only content"""
        self.logger.info("   No media content found - extracting article text for text-only processing")

        article_text = self._extract_article_text_content(soup)
        if article_text:
            word_count = len(article_text.split())
            self.logger.info(f"   📄 [TEXT ARTICLE] Extracted {word_count} words of article content")

            # Limit text size for prompt efficiency
            if word_count > Config.MAX_ARTICLE_WORDS:
                article_text = ' '.join(article_text.split()[:Config.MAX_ARTICLE_WORDS]) + '...'
                self.logger.info(f"   📄 [TEXT ARTICLE] Truncated to {Config.MAX_ARTICLE_WORDS} words for processing")
        else:
            self.logger.info("   ⚠️ [TEXT ARTICLE] No readable article content found")

        # Extract images from article
        images = self._extract_article_images(soup, base_url)

        return {
            'article_text': article_text or 'Content not available',
            'images': images
        }

    def _enrich_frames_with_transcript(self, metadata: Dict) -> None:
        """
        Enrich video frames with transcript excerpts for AI analysis and UI display

        Modifies metadata['video_frames'] in-place to add:
        - transcript_excerpt: Full transcript text for this frame's time window
        - (summary will be added by AI later)

        Args:
            metadata: Article metadata containing video_frames and transcripts
        """
        video_frames = metadata.get('video_frames', [])
        if not video_frames:
            return

        # Get the first transcript (should only be one)
        transcripts = metadata.get('transcripts', {})
        if not transcripts:
            self.logger.info("   ℹ️ No transcript data available for frame enrichment")
            return

        # Get the transcript data (first entry)
        transcript_data = next(iter(transcripts.values()))

        # Debug: Check what data we have available
        has_words = bool(transcript_data.get('words'))
        has_segments = bool(transcript_data.get('segments') or transcript_data.get('transcript'))
        self.logger.info(f"   🔍 [FRAME ENRICHMENT] Transcript data - has_words: {has_words}, has_segments: {has_segments}")
        if has_words:
            self.logger.info(f"   🔍 [FRAME ENRICHMENT] Word-level data available: {len(transcript_data.get('words', []))} words")

        self.logger.info(f"   📝 Enriching {len(video_frames)} frames with transcript excerpts...")

        for i, frame in enumerate(video_frames):
            start_time = frame['timestamp_seconds']

            # Determine end time: use next frame's timestamp, or add reasonable window
            if i < len(video_frames) - 1:
                end_time = video_frames[i + 1]['timestamp_seconds']
            else:
                # For last frame, use 120 second window (2 minutes)
                end_time = start_time + 120

            # Extract transcript excerpt for this time window
            excerpt = self._extract_transcript_excerpt(transcript_data, start_time, end_time, max_words=100)

            if excerpt:
                frame['transcript_excerpt'] = excerpt
            else:
                frame['transcript_excerpt'] = ""

        self.logger.info(f"   ✅ Enriched {len(video_frames)} frames with transcript data")

    def _apply_frame_summaries(self, metadata: Dict, frame_summaries: List[Dict]) -> None:
        """
        Apply AI-generated summaries to video frames

        Modifies metadata['video_frames'] in-place to add:
        - transcript_summary: AI-generated 10-word summary of what happens at this timestamp

        Args:
            metadata: Article metadata containing video_frames
            frame_summaries: List of {"frame_index": 0, "summary": "..."} from AI response
        """
        video_frames = metadata.get('video_frames', [])
        if not video_frames:
            return

        self.logger.info(f"   📝 Applying AI-generated summaries to {len(video_frames)} frames...")

        # Create a mapping of frame_index to summary
        summary_map = {item['frame_index']: item['summary'] for item in frame_summaries}

        # Apply summaries to frames
        applied_count = 0
        for i, frame in enumerate(video_frames):
            if i in summary_map:
                frame['transcript_summary'] = summary_map[i]
                applied_count += 1

        self.logger.info(f"   ✅ Applied {applied_count} AI summaries to frames")

    async def _generate_summary_async(self, url: str, metadata: Dict) -> Dict:
        """
        Async wrapper for AI summary generation.

        Runs the synchronous Claude API call in a thread pool to avoid blocking
        the event loop, enabling real-time SSE streaming.
        """
        import asyncio

        # Enrich video frames with transcript excerpts BEFORE sending to AI
        if metadata.get('video_frames'):
            self._enrich_frames_with_transcript(metadata)

        # Run the synchronous method in a thread pool
        return await asyncio.to_thread(self._generate_summary_with_ai, url, metadata)

    def _generate_summary_with_ai(self, url: str, metadata: Dict) -> Dict:
        """Generate AI summary based on content type"""
        content_type = metadata['content_type']

        # Build context based on content type using prompt builders
        if content_type.has_embedded_video:
            media_context = VideoContextBuilder.build(metadata, Config.MAX_TRANSCRIPT_CHARS)
        elif content_type.has_embedded_audio:
            media_context = AudioContextBuilder.build(metadata, Config.MAX_TRANSCRIPT_CHARS)
        else:
            media_context = TextContextBuilder.build(metadata)

        # Generate prompt using ArticleAnalysisPrompt
        simplified_metadata = create_metadata_for_prompt(metadata)
        prompt = ArticleAnalysisPrompt.build(url, media_context, simplified_metadata)

        # Call Claude API
        response = self._call_claude_api(prompt)

        # Parse response
        parsed_json = self._extract_json_from_response(response)

        if parsed_json:
            # Ensure summary is properly formatted as HTML
            if 'summary' in parsed_json:
                summary = parsed_json['summary']

                # Check if summary itself is a JSON string (sometimes Claude wraps incorrectly)
                if isinstance(summary, str) and summary.strip().startswith('{'):
                    try:
                        nested_json = json.loads(summary)
                        if isinstance(nested_json, dict) and 'summary' in nested_json:
                            self.logger.warning("   ⚠️ [JSON] Summary contained nested JSON - extracting inner summary")
                            summary = nested_json['summary']
                            parsed_json['summary'] = summary
                    except json.JSONDecodeError:
                        pass  # Not actually JSON, continue normally

                # Format as HTML if not already formatted
                if not any(tag in summary for tag in ['<p>', '<div>', '<h1>', '<h2>', '<h3>']):
                    parsed_json['summary'] = self._format_summary_as_html(summary)

            # Apply frame summaries to video_frames in metadata if present
            if 'frame_summaries' in parsed_json and metadata.get('video_frames'):
                self._apply_frame_summaries(metadata, parsed_json['frame_summaries'])

            self.logger.info("   ✅ [JSON] Successfully parsed Claude response")
            return parsed_json
        else:
            # Log JSON parsing failure for debugging
            self.logger.warning("   ⚠️ [JSON] Failed to parse Claude response as JSON")
            self.logger.warning(f"   📝 [JSON] Response preview: {response[:200]}...")

            # Fallback formatting
            formatted_summary = self._format_summary_as_html(response)
            return {
                "summary": formatted_summary,
                "key_insights": [{"insight": "Content analyzed - see summary for details", "timestamp": ""}],
                "media_timestamps": [],
                "summary_sections": []
            }

    # Prompt building methods moved to core/prompts.py for Braintrust versioning
    # See: VideoContextBuilder, AudioContextBuilder, TextContextBuilder, ArticleAnalysisPrompt

    async def _generate_themed_insights_async(self, user_id: str, metadata: Dict, ai_summary: Dict) -> Optional[Dict]:
        """
        Generate theme-specific insights for private articles.

        Fetches the organization's themes and asks Claude to generate insights
        relevant to each theme. Only called for private articles.

        Args:
            user_id: User ID to look up organization
            metadata: Article metadata including transcripts
            ai_summary: Already-generated general insights

        Returns:
            Dict with themed insights and theme mapping, or None if no themes
        """
        if not self.supabase:
            return None

        try:
            # Get user's organization_id
            user_data = self.supabase.table('users').select('organization_id').eq('id', user_id).single().execute()
            organization_id = user_data.data.get('organization_id') if user_data.data else None

            if not organization_id:
                self.logger.info("   ℹ️ No organization found for user - skipping themed insights")
                return None

            # Fetch organization's themes (including description for AI context)
            themes_data = self.supabase.table('themes').select('id, name, description').eq('organization_id', organization_id).execute()
            themes = themes_data.data if themes_data.data else []

            if not themes:
                self.logger.info("   ℹ️ No organizational themes configured - skipping themed insights")
                return None

            self.logger.info(f"   📊 Generating themed insights for {len(themes)} themes...")

            # Build transcript text for the prompt WITH timestamps
            # Use the same formatting as general insights so Claude can find timestamps
            transcript_text = ""
            transcripts = metadata.get('transcripts', {})
            if transcripts:
                for video_id, transcript_data in transcripts.items():
                    if transcript_data.get('success'):
                        # Use MediaContextBuilder's _format_transcript for timestamp-annotated text
                        formatted = MediaContextBuilder._format_transcript(transcript_data)
                        if formatted:
                            transcript_text += formatted + "\n"

            # Fallback to article text if no transcript
            if not transcript_text:
                transcript_text = metadata.get('article_text', '')

            # Build and call the themed insights prompt
            # Pass theme objects with name and description for better AI context
            theme_objects = [{'name': t['name'], 'description': t.get('description')} for t in themes]
            prompt = ThemedInsightsPrompt.build(
                themes=theme_objects,
                transcript_text=transcript_text,
                article_summary=ai_summary.get('summary', '')
            )

            # Run in thread pool to avoid blocking
            response = await asyncio.to_thread(self._call_claude_api, prompt)
            parsed = self._extract_json_from_response(response)

            if parsed and 'themed_insights' in parsed:
                # Create theme name to ID mapping
                theme_name_to_id = {t['name']: t['id'] for t in themes}

                # Count total insights generated
                total_insights = sum(len(insights) for insights in parsed['themed_insights'].values())
                self.logger.info(f"   ✅ Generated {total_insights} themed insights across {len(themes)} themes")

                return {
                    'themed_insights': parsed['themed_insights'],
                    'theme_mapping': theme_name_to_id
                }
            else:
                self.logger.warning("   ⚠️ Failed to parse themed insights response")
                return None

        except Exception as e:
            self.logger.warning(f"   ⚠️ Failed to generate themed insights: {e}")
            return None

    def _save_themed_insights(self, article_id: int, themed_data: Dict):
        """
        Save themed insights to the database.

        Args:
            article_id: Private article ID
            themed_data: Dict containing themed_insights and theme_mapping
        """
        if not self.supabase or not themed_data:
            return

        insights_by_theme = themed_data.get('themed_insights', {})
        theme_mapping = themed_data.get('theme_mapping', {})

        saved_count = 0
        for theme_name, insights in insights_by_theme.items():
            theme_id = theme_mapping.get(theme_name)
            if not theme_id or not insights:
                continue

            for insight in insights:
                try:
                    self.supabase.table('private_article_themed_insights').insert({
                        'private_article_id': article_id,
                        'theme_id': theme_id,
                        'insight_text': insight.get('insight_text', ''),
                        'timestamp_seconds': insight.get('timestamp_seconds'),
                        'time_formatted': insight.get('time_formatted')
                    }).execute()
                    saved_count += 1
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Failed to save themed insight: {e}")

        if saved_count > 0:
            self.logger.info(f"   ✅ Saved {saved_count} themed insights to database")

    def _call_claude_api(self, prompt: str) -> str:
        """Call Claude Code API for AI-powered analysis"""
        return self.claude_client.call_api(prompt)

    def _extract_json_from_response(self, response: str) -> Optional[Dict]:
        """Extract and parse JSON from Claude's response"""
        import re

        # Method 1: Try to extract JSON from code blocks first
        code_block_patterns = [
            (r'```json\s*(.*?)\s*```', 'json code block'),
            (r'```\s*(.*?)\s*```', 'generic code block'),
        ]

        for pattern, pattern_name in code_block_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if content.startswith('{'):
                    try:
                        self.logger.debug(f"   🔍 [JSON] Trying {pattern_name} - found {len(content)} chars")
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        self.logger.debug(f"   ❌ [JSON] {pattern_name} failed: {e}")

        # Method 2: Find JSON by matching balanced braces
        # Find the first '{' and try to parse from there
        start_idx = response.find('{')
        if start_idx != -1:
            # Try progressively larger substrings from first '{' to find valid JSON
            brace_count = 0
            for i, char in enumerate(response[start_idx:], start=start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found matching closing brace
                        json_candidate = response[start_idx:i+1]
                        try:
                            self.logger.debug(f"   🔍 [JSON] Trying balanced braces - found {len(json_candidate)} chars")
                            return json.loads(json_candidate)
                        except json.JSONDecodeError as e:
                            self.logger.debug(f"   ❌ [JSON] Balanced braces failed: {e}")
                            break

        self.logger.warning(f"   ⚠️ [JSON] No valid JSON found in {len(response)} char response")
        return None

    # HTML generation removed - web-app (Next.js) handles all display via React components
    # The Python script only processes content and saves to Supabase database

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text using OpenAI API

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector (384 dimensions) or None if generation fails
        """
        if not self.openai_client:
            return None

        try:
            # Truncate text to avoid token limits (8191 tokens max for text-embedding-3-small)
            # Approximately 4 characters per token, so limit to ~32000 characters
            if len(text) > 32000:
                text = text[:32000]
                self.logger.info(f"   📊 [EMBEDDING] Truncated text to 32000 characters for embedding")

            self.logger.info(f"   📊 [EMBEDDING] Generating embedding for {len(text)} characters...")

            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=384  # Use 384 dimensions for performance
            )

            embedding = response.data[0].embedding
            self.logger.info(f"   ✅ [EMBEDDING] Generated {len(embedding)}-dimensional embedding")
            return embedding

        except Exception as e:
            self.logger.error(f"   ❌ [EMBEDDING] Failed to generate embedding: {e}")
            return None

    def _extract_transcript_excerpt(self, transcript_data: Dict, start_seconds: float, end_seconds: float, max_words: int = 100) -> str:
        """
        Extract transcript text between two timestamps using word-level data

        Args:
            transcript_data: Transcript data from DeepGram (with 'words' array)
            start_seconds: Start timestamp in seconds
            end_seconds: End timestamp in seconds
            max_words: Maximum words to include in excerpt (default: 100)

        Returns:
            Transcript text excerpt (truncated to max_words)
        """
        if not transcript_data or not transcript_data.get('success'):
            return ""

        # Try to use word-level data for precision
        words = transcript_data.get('words', [])

        if words:
            # Extract words within the time window
            excerpt_words = []
            for word_data in words:
                word_start = word_data.get('start', 0)
                word = word_data.get('word', '')

                if start_seconds <= word_start < end_seconds:
                    excerpt_words.append(word)

                # Stop early if we've hit max_words
                if len(excerpt_words) >= max_words:
                    break

            return ' '.join(excerpt_words)

        else:
            # Fallback to segment-level data if word-level not available
            # When using segments, we need to check if ANY part of the segment overlaps with our time window
            segments = transcript_data.get('segments', transcript_data.get('transcript', []))
            excerpt_text = []

            for i, segment in enumerate(segments):
                seg_start = segment.get('start', 0)
                seg_text = segment.get('text', '')

                # Determine segment end time (start of next segment, or use a default duration)
                if i < len(segments) - 1:
                    seg_end = segments[i + 1].get('start', seg_start + 30)
                else:
                    seg_end = seg_start + 30  # Assume 30 second duration for last segment

                # Include segment if it overlaps with our time window at all
                # Segment overlaps if: segment starts before window ends AND segment ends after window starts
                if seg_start < end_seconds and seg_end > start_seconds:
                    excerpt_text.append(seg_text)

            full_text = ' '.join(excerpt_text)
            # Truncate to max_words
            words_list = full_text.split()
            if len(words_list) > max_words:
                return ' '.join(words_list[:max_words])
            return full_text

    def _build_embedding_text(self, metadata: Dict, ai_summary: Dict) -> str:
        """
        Build comprehensive text for embedding generation

        Combines title, summary, key insights, and topics into a single text
        that represents the article's content for semantic search.
        """
        parts = []

        # Add title (most important)
        if metadata.get('title'):
            parts.append(f"Title: {metadata['title']}")

        # Add summary
        if ai_summary.get('summary'):
            parts.append(f"Summary: {ai_summary['summary']}")

        # Add key insights
        key_insights = ai_summary.get('key_insights', [])
        if key_insights:
            insights_text = " ".join([insight.get('insight', '') for insight in key_insights])
            parts.append(f"Key Insights: {insights_text}")

        # Add topics
        topics = ai_summary.get('topics', [])
        if topics:
            parts.append(f"Topics: {', '.join(topics)}")

        # Add quotes
        quotes = ai_summary.get('quotes', [])
        if quotes:
            quotes_text = " ".join([quote.get('quote', '') for quote in quotes])
            parts.append(f"Notable Quotes: {quotes_text}")

        return "\n\n".join(parts)

    def check_article_exists(self, url: str) -> Optional[Dict]:
        """
        Check if an article with the given URL already exists in the database

        Args:
            url: Article URL to check

        Returns:
            Dict with article info if exists (id, title, created_at), None otherwise
        """
        if not self.supabase:
            return None

        try:
            result = self.supabase.table('articles').select('id, title, created_at, updated_at').eq('url', url).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            self.logger.warning(f"   ⚠️ Error checking for existing article: {e}")
            return None

    async def _try_youtube_discovery(self, url: str) -> str:
        """
        Attempt to discover YouTube URL from content_queue.
        Returns the discovered YouTube URL if found, otherwise returns the original URL.

        This is the SINGLE source of truth for YouTube discovery in article processing.
        Both process_article() and SSE endpoint should call this method.

        Args:
            url: Original content URL (e.g., PocketCasts episode page)

        Returns:
            YouTube URL if discovered, otherwise the original URL
        """
        self.logger.info("🔍 [YOUTUBE DISCOVERY] Attempting to discover YouTube URL...")

        # Look up content in queue
        queue_item = self._get_queue_item(url)
        if not queue_item:
            self.logger.info("   ℹ️ [YOUTUBE DISCOVERY] No queue item found, skipping discovery")
            return url

        channel_url = queue_item.get('channel_url')
        title = queue_item.get('title')
        published_date = queue_item.get('published_date')
        self.logger.info(f"   📋 [YOUTUBE DISCOVERY] Found queue item - channel: {channel_url}, title: {title}")

        # Attempt discovery
        discovered_youtube_url = await self._discover_youtube_url(
            content_url=url,
            channel_url=channel_url,
            title=title,
            published_date=published_date
        )

        if discovered_youtube_url:
            self.logger.info(f"   🎬 [YOUTUBE DISCOVERY] Success! Using: {discovered_youtube_url}")
            return discovered_youtube_url
        else:
            self.logger.info(f"   ℹ️ [YOUTUBE DISCOVERY] No YouTube URL found, using original URL")
            return url

    def _get_queue_item(self, url: str) -> Optional[Dict]:
        """Lookup content_queue item by URL to get channel information"""
        if not self.supabase:
            self.logger.debug("   [QUEUE LOOKUP] No Supabase client available")
            return None

        try:
            self.logger.info(f"   🔍 [QUEUE LOOKUP] Checking content_queue for URL...")
            result = self.supabase.table('content_queue')\
                .select('*')\
                .eq('url', url)\
                .single()\
                .execute()

            if result.data:
                self.logger.info(f"   ✅ [QUEUE LOOKUP] Found queue item with channel_url: {result.data.get('channel_url')}")
                return result.data
            else:
                self.logger.info(f"   ℹ️ [QUEUE LOOKUP] No queue item found for this URL")
                return None
        except Exception as e:
            self.logger.debug(f"Queue item not found for {url}: {e}")
            return None

    def _classify_youtube_url(self, url: str) -> Optional[str]:
        """
        Classify a YouTube URL as a direct video, channel, or playlist

        Args:
            url: YouTube URL to classify

        Returns:
            'video' - Direct video URL
            'channel_or_playlist' - Channel or playlist URL
            None - Invalid or no URL
        """
        if not url:
            return None

        # Check for direct video URLs
        if '/watch?v=' in url or 'youtu.be/' in url:
            return 'video'

        # Check for channel/playlist URLs
        if any(x in url for x in ['/playlist', '/channel/', '/@', '/c/', '/user/', '/videos']):
            return 'channel_or_playlist'

        return None

    async def _is_video_match_for_podcast(
        self,
        video_url: str,
        video_title: Optional[str],
        episode_title: str,
        episode_published_date: Optional[str] = None,
        video_published_date: Optional[str] = None
    ) -> tuple[bool, float]:
        """
        Check if a YouTube video matches a podcast episode using fuzzy matching with date-based thresholds

        Args:
            video_url: YouTube video URL
            video_title: Video title (if already known, otherwise will fetch)
            episode_title: Podcast episode title
            episode_published_date: Episode published date (ISO format)
            video_published_date: Video published date (ISO format or relative like "2 days ago")

        Returns:
            Tuple of (is_match, confidence_ratio)
        """
        from difflib import SequenceMatcher
        from datetime import datetime, timedelta
        import re

        # If video title not provided, we'd need to fetch it from YouTube
        # For now, require it to be passed in
        if not video_title:
            self.logger.warning(f"   ⚠️ [MATCH] No video title provided for comparison")
            return False, 0.0

        # Calculate character-level similarity ratio
        ratio = SequenceMatcher(None, episode_title.lower(), video_title.lower()).ratio()

        # Default threshold is 70%
        threshold = 0.70

        # Use relaxed threshold (40%) if published within 1 day of each other
        if episode_published_date and video_published_date:
            self.logger.info(f"         [DATE CHECK] Episode: '{episode_published_date}' | Video: '{video_published_date}'")
            try:
                from dateutil import parser

                # Parse episode date
                episode_date = parser.parse(episode_published_date)

                # Parse video date (handle relative dates like "2 days ago")
                video_date = None
                if 'ago' in video_published_date.lower():
                    match = re.search(r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago', video_published_date.lower())
                    if match:
                        amount = int(match.group(1))
                        unit = match.group(2)

                        now = datetime.now()
                        if unit == 'second':
                            video_date = now - timedelta(seconds=amount)
                        elif unit == 'minute':
                            video_date = now - timedelta(minutes=amount)
                        elif unit == 'hour':
                            video_date = now - timedelta(hours=amount)
                        elif unit == 'day':
                            video_date = now - timedelta(days=amount)
                        elif unit == 'week':
                            video_date = now - timedelta(weeks=amount)
                        elif unit == 'month':
                            video_date = now - timedelta(days=amount*30)
                        elif unit == 'year':
                            video_date = now - timedelta(days=amount*365)
                else:
                    # Try to parse as ISO format
                    try:
                        video_date = parser.parse(video_published_date)
                    except:
                        pass

                if video_date:
                    # Compare dates
                    days_apart = abs((episode_date.replace(tzinfo=None) - video_date.replace(tzinfo=None)).days)
                    self.logger.info(f"         [DATE COMPARE] {days_apart} days apart (episode: {episode_date.date()}, video: {video_date.date()})")
                    if days_apart <= 1:
                        threshold = 0.40
                        self.logger.info(f"         ✅ [DATE MATCH] Within 1 day! Using relaxed 40% threshold")
                    else:
                        self.logger.info(f"         ⚠️ [DATE DIFF] More than 1 day apart, using standard 70% threshold")
                else:
                    self.logger.info(f"         ⚠️ [DATE PARSE] Could not parse video date: '{video_published_date}'")
            except Exception as e:
                self.logger.warning(f"         ⚠️ [DATE ERROR] Error parsing dates: {e}")
        else:
            if not episode_published_date:
                self.logger.info(f"         ℹ️ [NO DATE] No episode published date available")
            if not video_published_date:
                self.logger.info(f"         ℹ️ [NO DATE] No video published date available")

        is_match = ratio >= threshold
        return is_match, ratio

    async def _discover_youtube_url(
        self,
        content_url: str,
        channel_url: Optional[str],
        title: Optional[str],
        published_date: Optional[str] = None
    ) -> Optional[str]:
        """
        Unified YouTube discovery - uses channel_url as lookup key
        This is where ALL YouTube discovery happens now (moved from Content Checker)

        Args:
            content_url: The content URL (PocketCasts episode page, article URL, etc.)
            channel_url: Channel URL from content_queue (RSS feed, PocketCasts channel, etc.)
            title: Content title for matching videos in playlists
            published_date: Content published date (for date-based matching)

        Returns:
            YouTube video URL if found, None otherwise
        """
        self.logger.info(f"")
        self.logger.info(f"🔍 [YOUTUBE DISCOVERY] Starting discovery...")
        if title:
            self.logger.info(f"   📝 Title: {title[:80]}")

        youtube_discovery = YouTubeDiscoveryService(self.logger)
        youtube_url = None

        # Step 1: Check public_channels table using channel_url
        if channel_url:
            self.logger.info(f"   [STEP 1] Checking public_channels for: {channel_url[:60]}")
            try:
                result = self.supabase.table('public_channels')\
                    .select('youtube_channel_url, channel_name')\
                    .eq('pocketcasts_channel_url', channel_url)\
                    .eq('is_active', True)\
                    .single()\
                    .execute()

                if result.data and result.data.get('youtube_channel_url'):
                    youtube_url = result.data['youtube_channel_url']
                    channel_name = result.data.get('channel_name', 'Unknown')
                    self.logger.info(f"   ✅ [PUBLIC CHANNEL] Found for '{channel_name}': {youtube_url[:60]}")

                    # Classify the URL
                    url_type = self._classify_youtube_url(youtube_url)

                    if url_type == 'video':
                        # Data error: public_channels should only have channel URLs
                        self.logger.warning(f"   ⚠️ [DATA ERROR] public_channels contains a video URL, not a channel. Skipping.")
                        youtube_url = None  # Continue to Step 2
                    elif url_type == 'channel_or_playlist':
                        # Expected - will handle in Step 3
                        pass
                    else:
                        self.logger.warning(f"   ⚠️ [UNKNOWN TYPE] Could not classify YouTube URL: {youtube_url[:60]}")
                        youtube_url = None

            except Exception as e:
                if 'PGRST116' not in str(e):  # Ignore "no rows returned"
                    self.logger.debug(f"   ℹ️ Not in public_channels: {e}")

        # Step 2: Scrape the content page for YouTube links
        if not youtube_url:
            self.logger.info(f"   [STEP 2] Scraping page for YouTube link...")
            youtube_url = youtube_discovery.extract_youtube_url_from_page(
                content_url,
                'podcast'  # Could detect from content_type in future
            )

            if youtube_url:
                # Classify what we found
                url_type = self._classify_youtube_url(youtube_url)

                if url_type == 'video':
                    # Direct video URL - this shouldn't need verification for scraped URLs
                    # (If it's embedded on the page, it's likely correct)
                    self.logger.info(f"   ✅ [STEP 2] Found direct video URL: {youtube_url[:60]}")
                    return youtube_url
                elif url_type == 'channel_or_playlist':
                    # Will handle in Step 3
                    pass
                else:
                    self.logger.warning(f"   ⚠️ [UNKNOWN TYPE] Could not classify scraped URL")
                    youtube_url = None

        # Step 3: If it's a channel/playlist, find the specific video (expensive operation)
        if youtube_url and title:
            url_type = self._classify_youtube_url(youtube_url)

            if url_type == 'channel_or_playlist':
                self.logger.info(f"   [STEP 3] Found channel/playlist, searching for specific video...")

                # For channels, append /videos to get videos tab
                if any(x in youtube_url for x in ['/channel/', '/@', '/c/', '/user/']):
                    if not youtube_url.endswith('/videos'):
                        youtube_url = youtube_url.rstrip('/') + '/videos'
                        self.logger.info(f"   💡 Appending /videos for better scraping")

                # Scrape playlist/channel to find specific video
                specific_video_url = await self._scrape_youtube_channel_for_video(
                    youtube_url,
                    title,
                    published_date
                )

                if specific_video_url:
                    self.logger.info(f"   ✅ [CHANNEL SCRAPING] Found specific video!")
                    return specific_video_url
                else:
                    self.logger.info(f"   ℹ️ [CHANNEL SCRAPING] No confident match found, will use original content URL")
                    return None

        # If we get here, no YouTube URL was found
        self.logger.info(f"ℹ️ [YOUTUBE DISCOVERY] No YouTube URL found")
        return None

    async def _scrape_youtube_channel_for_video(
        self,
        channel_url: str,
        episode_title: str,
        episode_published_date: Optional[str] = None
    ) -> Optional[str]:
        """
        Scrape YouTube channel/playlist to find specific video matching episode title

        Args:
            channel_url: YouTube channel or playlist URL
            episode_title: Episode title to match against
            episode_published_date: Episode published date (for date-based matching)

        Returns:
            YouTube video URL if confident match found, None otherwise
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            import re
            import json

            self.logger.info(f"      🔍 [SCRAPING] Fetching channel page...")

            response = requests.get(channel_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract videos from ytInitialData
            videos = []

            def find_videos_recursive(obj, videos_list):
                """Recursively search for video renderers in YouTube data"""
                if isinstance(obj, dict):
                    # Channel video (most common)
                    if 'richItemRenderer' in obj:
                        try:
                            video_data = obj['richItemRenderer']['content']['videoRenderer']
                            video_title = video_data.get('title', {}).get('runs', [{}])[0].get('text', '')
                            video_id = video_data.get('videoId', '')
                            # Extract published date (e.g., "2 days ago")
                            video_published = video_data.get('publishedTimeText', {}).get('simpleText', '')
                            if video_title and video_id:
                                videos_list.append({
                                    'title': video_title,
                                    'url': f'https://www.youtube.com/watch?v={video_id}',
                                    'published': video_published
                                })
                        except (KeyError, TypeError):
                            pass

                    # Playlist video
                    elif 'playlistVideoRenderer' in obj:
                        video_data = obj['playlistVideoRenderer']
                        video_title = video_data.get('title', {}).get('runs', [{}])[0].get('text', '')
                        video_id = video_data.get('videoId', '')
                        # Extract published date from playlist format
                        video_info_runs = video_data.get('videoInfo', {}).get('runs', [])
                        video_published = video_info_runs[-1].get('text', '') if video_info_runs else ''
                        if video_title and video_id:
                            videos_list.append({
                                'title': video_title,
                                'url': f'https://www.youtube.com/watch?v={video_id}',
                                'published': video_published
                            })

                    # Recurse into dictionary values
                    for value in obj.values():
                        find_videos_recursive(value, videos_list)

                elif isinstance(obj, list):
                    # Recurse into list items
                    for item in obj:
                        find_videos_recursive(item, videos_list)

            # Find ytInitialData in page scripts
            for script in soup.find_all('script'):
                if not script.string or 'ytInitialData' not in script.string:
                    continue

                match = re.search(r'var ytInitialData = ({.*?});', script.string)
                if not match:
                    continue

                try:
                    data = json.loads(match.group(1))
                    find_videos_recursive(data, videos)
                    if videos:
                        break
                except json.JSONDecodeError:
                    continue

            if not videos:
                self.logger.warning(f"      ⚠️ [SCRAPING] No videos found in channel/playlist")
                return None

            self.logger.info(f"      📊 [SCRAPING] Found {len(videos)} videos, matching against title...")
            self.logger.info(f"      📝 [EPISODE TITLE] '{episode_title}'")

            # Find best match using the unified matching method
            best_match = None
            best_ratio = 0.0

            for idx, video in enumerate(videos, 1):
                # Use the unified matching method with date-based thresholds
                video_published = video.get('published', '')
                is_match, ratio = await self._is_video_match_for_podcast(
                    video_url=video['url'],
                    video_title=video['title'],
                    episode_title=episode_title,
                    episode_published_date=episode_published_date,
                    video_published_date=video_published
                )

                # Log EVERY comparison with published date
                pub_info = f" (published: {video_published})" if video_published else ""
                self.logger.info(f"         [{idx}/{len(videos)}] {ratio:.1%}{pub_info} - '{video['title'][:80]}...'")

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = video
                    best_is_match = is_match

            if best_match and best_is_match:
                self.logger.info(f"      ✅ [MATCH] Found with {best_ratio:.1%} confidence: {best_match['title'][:80]}...")
                return best_match['url']
            elif best_match:
                self.logger.info(f"      ⚠️ [LOW CONFIDENCE] Best match only {best_ratio:.1%}: {best_match['title'][:80]}...")
                return None
            else:
                self.logger.info(f"      ℹ️ [NO MATCH] No videos passed threshold")
                return None

        except Exception as e:
            self.logger.error(f"      ❌ [SCRAPING] Failed: {e}")
            return None

    def _is_public_channel(self, url: str) -> bool:
        """
        Check if a URL matches any known public channel.

        All YouTube URLs are automatically considered public.

        For other URLs, queries the public_channels table across all URL columns:
        - pocketcasts_channel_url
        - podcast_feed_url
        - rss_feed_url
        - newsletter_url

        Also checks domain-level matches for newsletters/blogs.

        Args:
            url: The article/content URL to check

        Returns:
            True if the URL matches a public channel, False otherwise (private)
        """
        if not self.supabase:
            self.logger.warning("   ⚠️ Supabase not initialized - defaulting to private")
            return False

        try:
            from urllib.parse import urlparse

            # Normalize the URL for comparison
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]

            # All YouTube URLs are automatically public
            if 'youtube.com' in domain or 'youtu.be' in domain:
                self.logger.info(f"   ✅ [PUBLIC] YouTube URL - automatically public: {url[:60]}...")
                return True

            self.logger.info(f"🔍 [PRIVACY CHECK] Checking if URL is from public channel: {url[:60]}...")

            # Query public_channels table - check all URL columns
            result = self.supabase.table('public_channels')\
                .select('id, channel_name, pocketcasts_channel_url, youtube_channel_url, podcast_feed_url, rss_feed_url, newsletter_url')\
                .eq('is_active', True)\
                .execute()

            if not result.data:
                self.logger.info(f"   ℹ️ No public channels found - article is private")
                return False

            # Check each public channel for a match
            for channel in result.data:
                channel_name = channel.get('channel_name', 'Unknown')

                # Check exact URL matches for podcast/YouTube URLs
                if channel.get('pocketcasts_channel_url'):
                    if self._urls_match(url, channel['pocketcasts_channel_url']):
                        self.logger.info(f"   ✅ [PUBLIC] Matched pocketcasts_channel_url for '{channel_name}'")
                        return True

                if channel.get('youtube_channel_url'):
                    # For YouTube, check if the URL contains the channel/playlist
                    yt_channel = channel['youtube_channel_url']
                    if self._youtube_urls_match(url, yt_channel):
                        self.logger.info(f"   ✅ [PUBLIC] Matched youtube_channel_url for '{channel_name}'")
                        return True

                if channel.get('podcast_feed_url'):
                    if self._urls_match(url, channel['podcast_feed_url']):
                        self.logger.info(f"   ✅ [PUBLIC] Matched podcast_feed_url for '{channel_name}'")
                        return True

                # For RSS feeds and newsletters, check domain-level match
                if channel.get('rss_feed_url'):
                    channel_domain = self._extract_domain(channel['rss_feed_url'])
                    if channel_domain and domain == channel_domain:
                        self.logger.info(f"   ✅ [PUBLIC] Domain matched rss_feed_url for '{channel_name}'")
                        return True

                if channel.get('newsletter_url'):
                    channel_domain = self._extract_domain(channel['newsletter_url'])
                    if channel_domain and domain == channel_domain:
                        self.logger.info(f"   ✅ [PUBLIC] Domain matched newsletter_url for '{channel_name}'")
                        return True

            self.logger.info(f"   ℹ️ No public channel match found - article is private")
            return False

        except Exception as e:
            self.logger.error(f"   ❌ Error checking public channels: {e}")
            # Default to private if there's an error
            return False

    def _urls_match(self, url1: str, url2: str) -> bool:
        """Compare two URLs after normalization"""
        from urllib.parse import urlparse

        try:
            p1 = urlparse(url1.lower())
            p2 = urlparse(url2.lower())

            # Normalize domains (remove www.)
            d1 = p1.netloc.replace('www.', '')
            d2 = p2.netloc.replace('www.', '')

            # Normalize paths (remove trailing slashes)
            path1 = p1.path.rstrip('/')
            path2 = p2.path.rstrip('/')

            return d1 == d2 and path1 == path2
        except Exception:
            return False

    def _youtube_urls_match(self, content_url: str, channel_url: str) -> bool:
        """Check if a content URL belongs to a YouTube channel/playlist"""
        try:
            # Extract channel/playlist identifier from the channel_url
            if '@' in channel_url:
                # Handle @username format
                import re
                match = re.search(r'@([\w-]+)', channel_url)
                if match:
                    handle = match.group(1).lower()
                    return f'@{handle}' in content_url.lower()

            if '/channel/' in channel_url:
                # Handle /channel/UCxxxxx format
                import re
                match = re.search(r'/channel/([\w-]+)', channel_url)
                if match:
                    channel_id = match.group(1)
                    return channel_id in content_url

            if '/playlist' in channel_url:
                # Handle playlist URLs
                import re
                match = re.search(r'list=([\w-]+)', channel_url)
                if match:
                    playlist_id = match.group(1)
                    return playlist_id in content_url

            # Fallback: check if the channel URL is a substring
            return channel_url.lower().rstrip('/') in content_url.lower()
        except Exception:
            return False

    def _extract_domain(self, url: str) -> str:
        """Extract normalized domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ''

    def _save_to_database(self, metadata: Dict, ai_summary: Dict, user_id: Optional[str] = None, is_private: bool = False, themed_insights_data: Optional[Dict] = None):
        """Save article data to Supabase database

        Args:
            metadata: Article metadata
            ai_summary: AI-generated summary
            user_id: Optional user ID for authentication (Supabase auth user)
            is_private: If True, save to private_articles table (org-scoped)
            themed_insights_data: Optional themed insights data for private articles
        """
        if not self.supabase:
            self.logger.warning("   ⚠️ Supabase not initialized - skipping database save")
            return None

        try:
            content_type = metadata['content_type']

            # Extract transcript text if available
            # Use grouped format for display (30+ second sections)
            transcript_text = None
            transcripts = metadata.get('transcripts', {})
            if transcripts:
                transcript_parts = []
                for video_id, transcript_data in transcripts.items():
                    if transcript_data.get('success'):
                        formatted = self._format_transcript_for_display(transcript_data)
                        if formatted:
                            transcript_parts.append(formatted)
                if transcript_parts:
                    transcript_text = "\n\n".join(transcript_parts)

            # For text-only articles, use the article text as transcript
            # This ensures UI consistency - all articles show original source content
            article_text = metadata.get('article_text', '')
            if (not transcript_text and
                article_text and
                article_text != 'Content not available' and
                not content_type.has_embedded_video and
                not content_type.has_embedded_audio):
                transcript_text = article_text

            # Get video ID and platform if available (support all platforms)
            video_id = None
            platform = None
            audio_url = None

            if content_type.has_embedded_video:
                media_info = metadata.get('media_info', {})
                # Check for any platform URLs (youtube_urls, video_urls, etc.)
                for key in media_info.keys():
                    if key.endswith('_urls') and media_info[key]:
                        video_id = media_info[key][0].get('video_id')
                        # Extract platform from key (e.g., 'youtube_urls' -> 'youtube')
                        platform = key.replace('_urls', '')
                        break

                # For direct video files (HTML5 <video> tags or direct file URLs),
                # set video_id='direct_file' and save URL in audio_url for web app video player
                if platform == 'html5_video' and media_info.get('html5_video_urls'):
                    # HTML5 video tag (e.g., Q4 Inc events)
                    video_id = 'direct_file'
                    audio_url = media_info['html5_video_urls'][0].get('url')
                elif video_id == 'direct_file' and media_info.get('video_urls'):
                    # Generic direct video file
                    audio_url = media_info['video_urls'][0].get('url')

            # Get audio URL if available (for audio-only content)
            if content_type.has_embedded_audio and not audio_url:
                if metadata.get('media_info', {}).get('audio_urls'):
                    audio_url = metadata['media_info']['audio_urls'][0].get('url')
                elif content_type.audio_urls:
                    audio_url = content_type.audio_urls[0].get('url')

            # Determine content source based on what media is present
            if content_type.has_embedded_video and content_type.has_embedded_audio:
                content_source = 'mixed'
            elif content_type.has_embedded_video:
                content_source = 'video'
            elif content_type.has_embedded_audio:
                content_source = 'audio'
            else:
                content_source = 'article'

            # Generate embedding for semantic search
            embedding = None
            if self.openai_client:
                embedding_text = self._build_embedding_text(metadata, ai_summary)
                embedding = self._generate_embedding(embedding_text)

            # Extract source name
            source = extract_source(metadata['url'], metadata, self.session)

            # Convert duration_minutes to integer (database expects INTEGER, AI may return float string)
            duration_minutes = ai_summary.get('duration_minutes')
            if duration_minutes is not None:
                try:
                    # Convert to float first (handles string "2.25"), then round to integer
                    duration_minutes = round(float(duration_minutes))
                except (ValueError, TypeError):
                    self.logger.warning(f"   ⚠️ Invalid duration_minutes value: {duration_minutes}")
                    duration_minutes = None

            # Build article record
            article_data = {
                'title': metadata['title'],
                'url': metadata['url'],
                'source': source,
                'summary_text': ai_summary.get('summary', ''),
                'transcript_text': transcript_text,
                'original_article_text': metadata.get('article_text'),
                'content_source': content_source,
                'video_id': video_id,
                'audio_url': audio_url,
                'platform': platform,
                'tags': [],

                # Structured data
                'key_insights': ai_summary.get('key_insights', []),
                'quotes': ai_summary.get('quotes', []),
                'images': metadata.get('images', []),
                'video_frames': metadata.get('video_frames', []),

                # Metadata
                'duration_minutes': duration_minutes,
                'word_count': ai_summary.get('word_count'),
                'topics': ai_summary.get('topics', []),
            }

            # Add embedding if generated
            if embedding:
                article_data['embedding'] = embedding

            # Route to appropriate table based on privacy setting
            if is_private:
                # Save to private_articles table (org-scoped)
                article_id = self._save_private_article(article_data, user_id, themed_insights_data)
            else:
                # Save to public articles table (globally deduplicated)
                article_id = self._save_public_article(article_data, user_id)

            return article_id

        except Exception as e:
            self.logger.error(f"   ❌ Database save failed: {e}")
            return None

    def _save_public_article(self, article_data: Dict, user_id: Optional[str] = None) -> Optional[int]:
        """Save article to public articles table (globally deduplicated)"""
        try:
            # Try to update existing article or insert new one
            # Note: user_id is no longer on articles table (moved to article_users junction table)
            result = self.supabase.table('articles').upsert(
                article_data,
                on_conflict='url'
            ).execute()

            if result.data:
                article_id = result.data[0]['id']
                self.logger.info(f"   ✅ Saved to public articles (article ID: {article_id})")

                # Associate article with user in junction table (if user_id provided)
                if user_id:
                    try:
                        self.supabase.table('article_users').upsert(
                            {
                                'article_id': article_id,
                                'user_id': user_id
                            },
                            on_conflict='article_id,user_id'
                        ).execute()
                        self.logger.info(f"   ✅ Associated article with user: {user_id}")
                    except Exception as e:
                        self.logger.warning(f"   ⚠️ Failed to associate article with user: {e}")

                return article_id
            else:
                self.logger.warning("   ⚠️ Database save completed but no data returned")
                return None
        except Exception as e:
            self.logger.error(f"   ❌ Failed to save public article: {e}")
            return None

    def _save_private_article(self, article_data: Dict, user_id: Optional[str], themed_insights_data: Optional[Dict] = None) -> Optional[int]:
        """Save article to private_articles table (org-scoped)

        Args:
            article_data: Article data to save
            user_id: User ID for authentication
            themed_insights_data: Optional themed insights data from AI generation
        """
        if not user_id:
            self.logger.error("   ❌ Cannot save private article without user_id")
            return None

        try:
            # Get user's organization_id
            user_data = self.supabase.table('users').select('organization_id').eq('id', user_id).single().execute()
            organization_id = user_data.data.get('organization_id') if user_data.data else None

            if not organization_id:
                self.logger.error("   ❌ User must belong to an organization to create private articles")
                return None

            # Add organization_id to article data
            article_data['organization_id'] = organization_id

            # Check if private article already exists for this org+url
            existing = self.supabase.table('private_articles') \
                .select('id') \
                .eq('organization_id', organization_id) \
                .eq('url', article_data['url']) \
                .execute()

            if existing.data:
                # Update existing private article
                article_id = existing.data[0]['id']
                result = self.supabase.table('private_articles').update(article_data).eq('id', article_id).execute()
                self.logger.info(f"   ✅ Updated existing private article (article ID: {article_id})")

                # Delete existing themed insights before re-saving (for reprocessing)
                try:
                    self.supabase.table('private_article_themed_insights') \
                        .delete() \
                        .eq('private_article_id', article_id) \
                        .execute()
                except Exception as e:
                    self.logger.warning(f"   ⚠️ Failed to clear existing themed insights: {e}")
            else:
                # Create new private article
                result = self.supabase.table('private_articles').insert(article_data).execute()
                if result.data:
                    article_id = result.data[0]['id']
                    self.logger.info(f"   ✅ Saved to private articles (article ID: {article_id})")
                else:
                    self.logger.warning("   ⚠️ Database save completed but no data returned")
                    return None

            # Associate article with user in junction table
            try:
                self.supabase.table('private_article_users').upsert(
                    {
                        'private_article_id': article_id,
                        'user_id': user_id
                    },
                    on_conflict='private_article_id,user_id'
                ).execute()
                self.logger.info(f"   ✅ Associated private article with user: {user_id}")
            except Exception as e:
                self.logger.warning(f"   ⚠️ Failed to associate private article with user: {e}")

            # Save themed insights if available
            if themed_insights_data:
                self._save_themed_insights(article_id, themed_insights_data)

            return article_id
        except Exception as e:
            self.logger.error(f"   ❌ Failed to save private article: {e}")
            return None

    # Utility methods
    def _get_soup(self, content):
        """Create BeautifulSoup object from content"""
        from bs4 import BeautifulSoup
        return BeautifulSoup(content, 'html.parser')

    def _extract_title(self, soup, url: str) -> str:
        """Extract title from page"""
        # Try Open Graph title first (most reliable for modern sites)
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content'].strip()
            if title:
                return title

        # Try Twitter card title
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            title = twitter_title['content'].strip()
            if title:
                return title

        # Try multiple selectors
        title_selectors = [
            'h1', 'title',
            '.entry-title', '.post-title', '.article-title',
            '[data-testid="post-title"]'
        ]

        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                title = element.get_text(strip=True)
                # Skip generic/placeholder titles
                if title.lower() not in ['search results', 'loading...', 'article']:
                    return title

        # Fallback to URL
        return f"Article from {extract_domain(url)}"

    def _build_video_url(self, platform: str, video_id: str) -> str:
        """
        Build the full video URL from platform and video_id

        Args:
            platform: Video platform (youtube, loom, vimeo, etc.)
            video_id: Video identifier

        Returns:
            Full video URL
        """
        platform_urls = {
            'youtube': f"https://www.youtube.com/watch?v={video_id}",
            'loom': f"https://www.loom.com/share/{video_id}",
            'vimeo': f"https://vimeo.com/{video_id}",
            'wistia': f"https://fast.wistia.net/embed/iframe/{video_id}",
            'dailymotion': f"https://www.dailymotion.com/video/{video_id}",
        }

        return platform_urls.get(platform.lower(), f"https://{platform}.com/{video_id}")

    def _download_video_with_ytdlp(
        self,
        video_url: str,
        output_template: str,
        referer: Optional[str] = None,
        download_video: bool = False
    ) -> Optional[str]:
        """
        Download video/audio using yt-dlp (handles HLS streams, not just direct URLs)

        Args:
            video_url: Video URL to download
            output_template: Path template where to save the file (extension will be added by yt-dlp)
            referer: Optional referer URL for platforms that require it (e.g., embedded Vimeo)
            download_video: If True, download full video. If False, download audio only (default)

        Returns:
            Path to downloaded file if successful, None otherwise
        """
        try:
            import yt_dlp
            import glob
            import shutil
            from pathlib import Path
            from urllib.parse import urlparse, unquote

            # Handle local file:// URLs - copy directly instead of using yt-dlp
            if video_url.startswith('file://'):
                self.logger.info(f"      📁 [LOCAL FILE] Detected file:// URL, copying directly...")
                # Extract local path from file:// URL
                parsed = urlparse(video_url)
                local_path = unquote(parsed.path)

                # Get file extension
                file_ext = Path(local_path).suffix
                output_path = output_template + file_ext

                # Copy the file
                shutil.copy2(local_path, output_path)
                self.logger.info(f"      ✅ [LOCAL FILE] Copied to: {output_path}")

                return output_path

            # Clean up any existing files matching this output template
            pattern = output_template + "*"
            existing_files = glob.glob(pattern)
            for f in existing_files:
                try:
                    os.unlink(f)
                    self.logger.info(f"      🧹 Cleaned up existing file: {f}")
                except Exception as e:
                    self.logger.warning(f"      ⚠️ Could not clean up existing file {f}: {e}")

            # Determine if this is a YouTube URL (for fallback strategy)
            is_youtube = 'youtube.com' in video_url or 'youtu.be' in video_url

            if download_video:
                # For frame extraction, we don't need high quality - use lower quality formats
                # This significantly reduces download size and processing time
                # Prioritize lowest quality first for all platforms - we only need video
                # for frame extraction/timestamps, not for viewing quality
                # Different platforms support different format selectors:
                # - YouTube: supports 'worst', 'best', height filters
                # - Loom: supports 'worst', 'best', 'bestvideo+bestaudio' (no height filters)
                # - Vimeo: supports height filters and bestvideo+bestaudio
                # - Wistia: supports height<=480, worst/best
                format_options = [
                    'worst',  # Lowest quality - ideal for frame extraction
                    'worstvideo+worstaudio/worst',  # Explicit worst video+audio
                    'bestvideo[height<=360]+bestaudio/best[height<=360]',  # 360p fallback
                    'bestvideo[height<=480]+bestaudio/best[height<=480]',  # 480p fallback
                    'bestvideo+bestaudio',  # Full quality fallback (Loom often needs this)
                    'best',  # Final fallback
                ]

                last_error = None
                for format_str in format_options:
                    try:
                        # Log which format we're trying
                        if format_str == 'worst':
                            self.logger.info(f"      🔄 [YT-DLP] Trying format: '{format_str}' (lowest quality)")
                        elif format_str == 'best':
                            self.logger.info(f"      🔄 [YT-DLP] Trying format: '{format_str}' (fallback)")
                        else:
                            self.logger.info(f"      🔧 [YT-DLP] Trying format: '{format_str}'")

                        ydl_opts = {
                            'format': format_str,
                            'outtmpl': output_template,
                            'quiet': True,
                            'no_warnings': True,
                            'nocheckcertificate': True,
                            'no_check_certificate': True,
                            'ignoreerrors': False,
                            'merge_output_format': 'mp4',  # Merge to MP4 if separate video/audio streams
                        }

                        # Add referer if provided (helps with embedded videos like Vimeo)
                        if referer:
                            ydl_opts['http_headers'] = {'Referer': referer, 'Origin': referer}
                            if format_str == format_options[0]:  # Only log once
                                self.logger.info(f"      🔧 [YT-DLP] Using referer/origin: {referer[:80]}...")

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([video_url])

                        # If we get here, download succeeded
                        self.logger.info(f"      ✅ [YT-DLP] Successfully downloaded using format: '{format_str}'")
                        break

                    except Exception as e:
                        last_error = e
                        error_msg = str(e)

                        # Check if we should try next format (on format errors or 403)
                        # Common errors: "Requested format is not available", "403 Forbidden"
                        should_retry = (
                            ('not available' in error_msg.lower() or '403' in error_msg)
                            and format_str != format_options[-1]
                        )

                        if should_retry:
                            self.logger.warning(f"      ⚠️ [YT-DLP] Format '{format_str}' failed: {error_msg[:100]}")
                            self.logger.info(f"      🔄 [YT-DLP] Trying next fallback format...")
                            # Clean up any partial downloads before retry
                            pattern = output_template + "*"
                            for f in glob.glob(pattern):
                                try:
                                    os.unlink(f)
                                except:
                                    pass
                            continue
                        else:
                            # No more formats to try - raise the error
                            raise

                # If we exhausted all format options, raise the last error
                if last_error and not glob.glob(output_template + "*"):
                    raise last_error

            else:
                self.logger.info(f"      🔧 [YT-DLP] Downloading audio with yt-dlp...")
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': output_template,
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,  # Bypass SSL certificate verification
                    'no_check_certificate': True,  # Alternative flag
                    'ignoreerrors': False,  # We want to see errors to handle them
                    # Use postprocessor to extract audio if downloaded file contains video
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }

                # Add referer if provided (helps with embedded videos like Vimeo)
                if referer:
                    ydl_opts['http_headers'] = {'Referer': referer, 'Origin': referer}
                    self.logger.info(f"      🔧 [YT-DLP] Using referer/origin: {referer[:80]}...")

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

            # yt-dlp adds the extension, so we need to find the actual file
            # It could be .m4a, .webm, .opus, etc.
            pattern = output_template + "*"
            matching_files = glob.glob(pattern)

            if matching_files:
                actual_path = matching_files[0]
                file_size_mb = os.path.getsize(actual_path) / (1024 * 1024)
                file_ext = os.path.splitext(actual_path)[1]
                self.logger.info(f"      ✅ [YT-DLP] Download successful: {actual_path}")
                self.logger.info(f"      📊 [DOWNLOADED FILE] Size: {file_size_mb:.1f}MB, Format: {file_ext}")

                # Note: file_transcriber._extract_audio_if_needed() will validate and extract audio if needed
                # before transcription. No need for duplicate validation here.

                return actual_path
            else:
                # Maybe no extension was added
                if os.path.exists(output_template):
                    return output_template
                self.logger.error(f"      ❌ [YT-DLP] Downloaded file not found")
                return None

        except Exception as e:
            self.logger.error(f"      ❌ [YT-DLP] Download failed: {e}")
            return None

    def _extract_youtube_audio_url(self, video_id: str) -> Optional[str]:
        """
        Extract audio stream URL from YouTube video using yt-dlp

        Args:
            video_id: YouTube video ID

        Returns:
            Audio stream URL or None if extraction fails
        """
        try:
            import yt_dlp

            video_url = f"https://www.youtube.com/watch?v={video_id}"
            self.logger.info(f"      🔧 [YT-DLP] Extracting audio URL from YouTube...")

            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

                # Get the best audio format URL
                if 'url' in info:
                    audio_url = info['url']
                    self.logger.info(f"      ✅ [YT-DLP] Extracted audio URL successfully")
                    return audio_url
                elif 'formats' in info:
                    # Find best audio format
                    audio_formats = [f for f in info['formats'] if f.get('acodec') != 'none']
                    if audio_formats:
                        # Sort by audio bitrate, get best quality
                        best_audio = max(audio_formats, key=lambda x: x.get('abr', 0))
                        audio_url = best_audio.get('url')
                        if audio_url:
                            self.logger.info(f"      ✅ [YT-DLP] Extracted audio URL successfully")
                            return audio_url

            self.logger.warning(f"      ⚠️ [YT-DLP] No audio URL found in video info")
            return None

        except Exception as e:
            self.logger.error(f"      ❌ [YT-DLP] Failed to extract audio URL: {e}")
            return None

    async def _download_and_transcribe_media_async(
        self,
        media_url: str,
        media_type: str = "audio",
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None
    ) -> Optional[Dict]:
        """
        Async version: Download and transcribe audio/video file using DeepGram with progress callbacks

        Args:
            media_url: URL of the audio/video file
            media_type: Type of media (audio or video)
            progress_callback: Optional async callback for progress updates

        Returns:
            Transcript data dict or None if transcription fails
        """
        if not self.file_transcriber:
            self.logger.warning("   ⚠️ File transcriber not available")
            return None

        try:
            import tempfile
            import requests
            import os

            self.logger.info(f"   🎵 [DEEPGRAM] Attempting to transcribe {media_type} from URL...")

            if progress_callback:
                await progress_callback("downloading_audio", {"media_type": media_type})

            # Download media file to temp location (run in thread pool - blocking I/O)
            def download_file():
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_path = temp_file.name
                    self.logger.info(f"   📥 [DOWNLOAD] Downloading {media_type} file...")

                    response = requests.get(media_url, stream=True, timeout=60)
                    response.raise_for_status()

                    # Write to temp file
                    for chunk in response.iter_content(chunk_size=8192):
                        temp_file.write(chunk)

                    return temp_path

            temp_path = await asyncio.to_thread(download_file)
            self.logger.info(f"   ✅ [DOWNLOAD] Downloaded to {temp_path}")

            # Use centralized transcription method with automatic size checking and chunking
            result = await self._transcribe_audio_with_size_check(
                temp_path,
                media_type=media_type,
                progress_callback=progress_callback
            )

            if not result:
                self.logger.warning(f"   ❌ Transcription failed")
                return None

            transcript_data = result['transcript_data']
            transcript_json_file = result.get('output_file')

            # Format for our use - convert to same format as YouTube transcripts
            segments = transcript_data.get('segments', [])
            transcript_list = []
            for segment in segments:
                transcript_list.append({
                    'start': segment.get('start', 0),
                    'text': segment.get('text', ''),
                    'duration': segment.get('end', 0) - segment.get('start', 0) if segment.get('end') else segment.get('duration', 0)
                })

            formatted_transcript = {
                'success': True,
                'transcript': transcript_list,  # Use 'transcript' key to match YouTube format
                'segments': transcript_list,  # Also use 'segments' key for consistency
                'text': transcript_data.get('text', ''),
                'language': transcript_data.get('language', 'unknown'),
                'type': transcript_data.get('type', 'deepgram_transcription'),
                'source': media_type,
                'total_entries': len(transcript_list),
                'words': transcript_data.get('words', [])  # Include word-level timestamps for frame extraction
            }

            self.logger.info(f"   ✅ [DEEPGRAM] Transcription successful ({len(formatted_transcript['text'])} chars)")

            # Clean up temp files
            try:
                await asyncio.to_thread(os.unlink, temp_path)  # Delete downloaded audio file
                if transcript_json_file:  # Only delete if not None (chunking sets it to None)
                    await asyncio.to_thread(os.unlink, transcript_json_file)  # Delete transcript JSON file
                self.logger.info(f"   🧹 Cleaned up temp files")
            except Exception as cleanup_error:
                self.logger.warning(f"   ⚠️ Could not clean up temp files: {cleanup_error}")

            return formatted_transcript

        except Exception as e:
            self.logger.warning(f"   ⚠️ [DEEPGRAM] Transcription failed: {str(e)}")
            return None

    async def _transcribe_audio_with_size_check(
        self,
        audio_path: str,
        media_type: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None
    ) -> Optional[Dict]:
        """
        Centralized method to transcribe audio with automatic chunking for large files.

        This is the SINGLE entry point for all DeepGram transcription, ensuring consistent
        file size checking and chunking logic across all code paths.

        Args:
            audio_path: Path to the audio file
            media_type: Type of media (audio, video, direct_file, etc.)
            progress_callback: Optional async callback for progress updates

        Returns:
            Transcript data dict with 'transcript_data' key, or None if transcription fails
        """
        import os

        # Check file size
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        file_ext = os.path.splitext(audio_path)[1]
        self.logger.info(f"   📊 [AUDIO FILE] Size: {file_size_mb:.1f}MB, Format: {file_ext}")

        # If file exceeds limit, use chunking
        if file_size_mb > Config.MAX_DEEPGRAM_FILE_SIZE_MB:
            self.logger.info(f"   ✂️ [CHUNKING] File exceeds {Config.MAX_DEEPGRAM_FILE_SIZE_MB}MB limit, splitting into chunks...")
            if progress_callback:
                await progress_callback("audio_chunking_required", {
                    "file_size_mb": file_size_mb
                })

            # Use async chunking method
            formatted_transcript = await self._transcribe_large_audio_file_async(
                audio_path,
                media_type,
                progress_callback=progress_callback
            )

            if not formatted_transcript:
                self.logger.warning(f"   ❌ Chunked transcription failed")
                return None

            # Format result to match expected structure
            return {
                'transcript_data': {
                    'text': formatted_transcript.get('text', ''),
                    'segments': formatted_transcript.get('transcript', []),
                    'language': formatted_transcript.get('language', 'en'),
                    'duration': max([seg.get('start', 0) + seg.get('duration', 0)
                                   for seg in formatted_transcript.get('transcript', [])] or [0]),
                    'provider': 'deepgram',
                    'type': formatted_transcript.get('type', 'deepgram'),
                    'words': formatted_transcript.get('words', [])  # Include word-level data for frame extraction
                },
                'output_file': None  # Chunking method handles cleanup
            }
        else:
            # File is small enough, transcribe directly
            self.logger.info(f"   🎤 [DIRECT] Transcribing with DeepGram (no chunking needed)...")
            return await asyncio.to_thread(
                self.file_transcriber.transcribe_file,
                audio_path
            )

    async def _transcribe_large_audio_file_async(
        self,
        audio_path: str,
        media_type: str,
        max_duration_minutes: int = 30,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None
    ) -> Optional[Dict]:
        """
        Async version: Transcribe large audio files by splitting into chunks with progress callbacks

        Args:
            audio_path: Path to the audio file
            media_type: Type of media (audio or video)
            max_duration_minutes: Maximum time to spend on transcription (default: 30 minutes)
            progress_callback: Optional async callback for progress updates

        Returns:
            Transcript data dict or None if transcription fails
        """
        try:
            from pydub import AudioSegment
            import tempfile
            import os
            import time

            self.logger.info(f"   🎵 [CHUNKING] Loading audio file for splitting...")
            start_time = time.time()
            timeout_seconds = max_duration_minutes * 60

            # Load audio file (run in thread pool since it's I/O bound)
            audio = await asyncio.to_thread(AudioSegment.from_file, audio_path)
            duration_ms = len(audio)
            duration_min = duration_ms / 1000 / 60

            self.logger.info(f"   ⏱️ [DURATION] Audio is {duration_min:.1f} minutes")
            self.logger.info(f"   ⏰ [TIMEOUT] Will process for max {max_duration_minutes} minutes")

            # Split into 20-minute chunks
            chunk_length_ms = 20 * 60 * 1000  # 20 minutes
            chunks = []

            for i in range(0, duration_ms, chunk_length_ms):
                chunk = audio[i:i + chunk_length_ms]
                chunks.append((i / 1000, chunk))  # Store start time in seconds

            self.logger.info(f"   ✂️ [CHUNKS] Split into {len(chunks)} chunks of ~20 minutes each")

            if progress_callback:
                await progress_callback("audio_split", {
                    "total_chunks": len(chunks),
                    "duration_minutes": duration_min
                })

            # Transcribe each chunk
            all_segments = []
            all_words = []
            all_text = []
            chunks_completed = 0

            for chunk_idx, (start_offset, chunk) in enumerate(chunks):
                # Check if we've exceeded timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    self.logger.warning(f"   ⏰ [TIMEOUT] Reached {max_duration_minutes} minute limit after {chunk_idx}/{len(chunks)} chunks")
                    self.logger.info(f"   📦 [PARTIAL] Processing {chunks_completed} completed chunks...")
                    break

                self.logger.info(f"   🎙️ [CHUNK {chunk_idx + 1}/{len(chunks)}] Transcribing... ({elapsed/60:.1f}/{max_duration_minutes} min elapsed)")

                if progress_callback:
                    await progress_callback("transcribing_chunk", {
                        "current": chunk_idx + 1,
                        "total": len(chunks),
                        "elapsed_minutes": elapsed / 60
                    })

                # Save chunk to temp file
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as chunk_file:
                    chunk_path = chunk_file.name
                    await asyncio.to_thread(chunk.export, chunk_path, format='mp3')

                try:
                    # Transcribe this chunk (run in thread pool - blocking I/O)
                    result = await asyncio.to_thread(
                        self.file_transcriber.transcribe_file,
                        chunk_path
                    )
                    transcript_data = result['transcript_data']
                    transcript_json_file = result['output_file']

                    # Adjust timestamps to account for chunk offset
                    segments = transcript_data.get('segments', [])
                    for segment in segments:
                        all_segments.append({
                            'start': segment.get('start', 0) + start_offset,
                            'text': segment.get('text', ''),
                            'duration': segment.get('end', 0) - segment.get('start', 0)
                        })

                    # Also collect word-level data with adjusted timestamps
                    words = transcript_data.get('words', [])
                    for word in words:
                        all_words.append({
                            'word': word.get('word', ''),
                            'start': word.get('start', 0) + start_offset,
                            'end': word.get('end', 0) + start_offset,
                            'confidence': word.get('confidence', 0)
                        })

                    all_text.append(transcript_data.get('text', ''))
                    chunks_completed += 1

                    self.logger.info(f"   ✅ [CHUNK {chunk_idx + 1}/{len(chunks)}] Complete ({len(segments)} segments, {len(words)} words)")

                    # Clean up chunk files
                    await asyncio.to_thread(os.unlink, chunk_path)
                    await asyncio.to_thread(os.unlink, transcript_json_file)

                except Exception as chunk_error:
                    self.logger.warning(f"   ⚠️ [CHUNK {chunk_idx + 1}/{len(chunks)}] Failed: {chunk_error}")
                    # Continue with other chunks even if one fails
                    try:
                        await asyncio.to_thread(os.unlink, chunk_path)
                    except:
                        pass

            # Clean up original file
            await asyncio.to_thread(os.unlink, audio_path)

            if not all_segments:
                self.logger.warning(f"   ❌ [CHUNKING] No segments transcribed successfully")
                return None

            # Combine all transcripts
            is_partial = chunks_completed < len(chunks)
            formatted_transcript = {
                'success': True,
                'transcript': all_segments,
                'segments': all_segments,  # Also use 'segments' key for consistency
                'text': ' '.join(all_text),
                'language': 'unknown',
                'type': 'deepgram_transcription_chunked' + ('_partial' if is_partial else ''),
                'source': media_type,
                'total_entries': len(all_segments),
                'chunks_processed': chunks_completed,
                'total_chunks': len(chunks),
                'is_partial': is_partial,
                'words': all_words  # Include combined word-level data for frame extraction
            }

            if is_partial:
                self.logger.warning(f"   ⚠️ [PARTIAL] Transcription incomplete: {chunks_completed}/{len(chunks)} chunks processed")
                self.logger.info(f"   📊 [PARTIAL] Returning partial transcript ({len(formatted_transcript['text'])} chars)")
            else:
                self.logger.info(f"   ✅ [DEEPGRAM] Chunked transcription successful ({len(formatted_transcript['text'])} chars, {len(chunks)} chunks)")

            return formatted_transcript

        except ImportError:
            self.logger.error(f"   ❌ [CHUNKING] pydub library not installed. Install with: pip install pydub")
            self.logger.error(f"   ❌ [CHUNKING] Also requires ffmpeg: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)")
            return None
        except Exception as e:
            self.logger.error(f"   ❌ [CHUNKING] Failed to process large audio file: {e}")
            return None

    def _extract_article_text_content(self, soup) -> str:
        """Extract main article text content with preserved structure"""
        # Try multiple content selectors (including Substack-specific)
        content_selectors = [
            '.available-content',  # Substack main content
            '.body',  # Substack body
            'article', '.entry-content', '.post-content', '.content',
            '.post-body', 'main', '[role="main"]'
        ]

        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                return self._extract_readable_text(element)

        # Fallback to body
        body = soup.find('body')
        if body:
            return self._extract_readable_text(body)

        return ""

    def _extract_readable_text(self, element) -> str:
        """
        Extract text with preserved structure and filtered UI elements.

        Removes:
        - Navigation, header, footer, sidebar elements
        - Buttons, forms, and interactive UI
        - Script and style tags

        Preserves:
        - Paragraph breaks
        - Heading hierarchy
        - List structure
        """
        from bs4 import BeautifulSoup
        from copy import copy

        # Create a copy to avoid modifying original
        element = copy(element)

        # Remove unwanted elements
        unwanted_tags = [
            'script', 'style', 'nav', 'header', 'footer', 'aside',
            'form', 'button', 'input', 'select', 'textarea',
            'iframe', 'noscript', 'svg'
        ]
        for tag in unwanted_tags:
            for el in element.find_all(tag):
                el.decompose()

        # Remove common UI class patterns
        ui_patterns = [
            'nav', 'menu', 'header', 'footer', 'sidebar', 'widget',
            'button', 'btn', 'toolbar', 'modal', 'popup', 'dropdown',
            'search', 'filter', 'pagination', 'breadcrumb',
            'social', 'share', 'comment', 'reply', 'subscribe',
            'advertisement', 'promo', 'banner'
        ]

        for pattern in ui_patterns:
            # Find by class
            for el in element.find_all(class_=lambda x: x and pattern in x.lower()):
                el.decompose()
            # Find by id
            for el in element.find_all(id=lambda x: x and pattern in x.lower()):
                el.decompose()

        # Extract text with paragraph breaks preserved
        # Use separator to add double line breaks between block elements
        text = element.get_text(separator='\n\n', strip=True)

        # Clean up excessive whitespace
        import re
        # Replace 3+ newlines with 2 newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove lines that are just whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)

        return text

    def _extract_article_images(self, soup, base_url: str) -> list:
        """Extract image URLs from article content"""
        from urllib.parse import urljoin, urlparse, urlunparse

        image_urls = []

        # Try to find content container first
        content_selectors = [
            '.available-content',  # Substack main content
            '.body',  # Substack body
            'article', '.entry-content', '.post-content', '.content',
            '.post-body', 'main', '[role="main"]'
        ]

        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break

        # If no content element found, search whole page
        if not content_element:
            content_element = soup

        # Find all images in content
        img_tags = content_element.find_all('img')

        for img in img_tags:
            src = img.get('src', '')

            # Skip small icons, tracking pixels, and invalid images
            if not src:
                continue

            # Skip data URIs, tracking pixels, and very small images
            if src.startswith('data:'):
                continue
            if 'tracking' in src.lower() or 'pixel' in src.lower():
                continue
            if 'icon' in src.lower() or 'logo' in src.lower():
                continue

            # Try to get dimensions to skip small images (likely icons)
            width = img.get('width', '')
            height = img.get('height', '')
            try:
                if width and int(width) < 100:
                    continue
                if height and int(height) < 100:
                    continue
            except (ValueError, TypeError):
                pass

            # Make relative URLs absolute
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                # Construct absolute URL from base_url
                src = urljoin(base_url, src)

            # Check for srcset for higher quality images
            srcset = img.get('srcset', '')
            if srcset:
                # Parse srcset and get the highest resolution version
                srcset_parts = srcset.split(',')
                if srcset_parts:
                    # Take the last one (usually highest resolution)
                    largest = srcset_parts[-1].strip().split()[0]
                    if largest:
                        # Clean up CDN transformations (e.g., Substack's fl_progressive:steep/)
                        # and decode URL-encoded URLs
                        from urllib.parse import unquote

                        # Remove CDN transformation prefixes
                        if '/' in largest and not largest.startswith(('http://', 'https://', '//', '/')):
                            # Check if it has a CDN prefix like "fl_progressive:steep/https%3A..."
                            parts = largest.split('/', 1)
                            if len(parts) == 2 and (':' in parts[0] or parts[1].startswith('http')):
                                largest = parts[1]

                        # Decode URL-encoded URLs (e.g., https%3A%2F%2F -> https://)
                        if '%' in largest and not largest.startswith(('http://', 'https://', '//')):
                            largest = unquote(largest)

                        src = largest
                        # Make absolute if needed
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = urljoin(base_url, src)

            # Clean up image URLs for full resolution
            # Seeking Alpha: Remove query parameters to get full-size images
            if 'seekingalpha.com' in src:
                parsed = urlparse(src)
                # Remove query parameters to get original full-size image
                src = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

            # Add to list if not already present
            if src and src not in image_urls:
                image_urls.append(src)

        if image_urls:
            self.logger.info(f"   📸 [IMAGES] Extracted {len(image_urls)} images from article")

        return image_urls

    # _format_transcript_for_analysis moved to core/prompts.py (VideoContextBuilder._format_transcript and AudioContextBuilder._format_transcript)

    def _format_transcript_for_display(self, transcript_data: Dict) -> str:
        """
        Format transcript for display.
        - DeepGram transcripts: Use natural paragraph segments as-is
        - YouTube transcripts: Group into minimum 30-second chunks for better readability
        """
        if not transcript_data or not transcript_data.get('success'):
            return ""

        # Handle both YouTube API format ('transcript') and DeepGram format ('segments')
        transcript = transcript_data.get('transcript', transcript_data.get('segments', []))

        # Check if this is a YouTube transcript (has 'type' field set to 'manual' or 'auto_generated')
        # or if it's a DeepGram transcript (will have paragraph-level segments already)
        is_youtube = transcript_data.get('type') in ['manual', 'auto_generated']

        formatted_sections = []

        if is_youtube:
            # YouTube transcripts: Group into minimum 30-second chunks
            current_group_start = None
            current_group_text = []

            for entry in transcript:
                start_time = entry.get('start', 0)
                text = entry.get('text', '').strip()

                if not text:
                    continue

                # Start new group if this is the first entry
                if current_group_start is None:
                    current_group_start = start_time
                    current_group_text = [text]
                # Check if we should start a new group (30 seconds elapsed)
                elif start_time - current_group_start >= 30:
                    # Save the current group
                    self._add_formatted_section(formatted_sections, current_group_start, ' '.join(current_group_text))
                    # Start new group
                    current_group_start = start_time
                    current_group_text = [text]
                else:
                    # Add to current group
                    current_group_text.append(text)

            # Add the final group
            if current_group_start is not None and current_group_text:
                self._add_formatted_section(formatted_sections, current_group_start, ' '.join(current_group_text))
        else:
            # DeepGram transcripts: Use natural paragraph boundaries (no regrouping)
            for entry in transcript:
                start_time = entry.get('start', 0)
                text = entry.get('text', '').strip()

                if not text:
                    continue

                self._add_formatted_section(formatted_sections, start_time, text)

        return "\n\n".join(formatted_sections)

    def _add_formatted_section(self, sections: List[str], start_time: float, text: str) -> None:
        """Helper to format and add a timestamped section"""
        # Format timestamp as [MM:SS] or [H:MM:SS]
        hours = int(start_time // 3600)
        minutes = int((start_time % 3600) // 60)
        seconds = int(start_time % 60)

        if hours > 0:
            timestamp = f"[{hours}:{minutes:02d}:{seconds:02d}]"
        else:
            timestamp = f"[{minutes}:{seconds:02d}]"

        sections.append(f"{timestamp} {text}")

    # _create_metadata_for_prompt moved to core/prompts.py (create_metadata_for_prompt function)

    def _format_summary_as_html(self, summary_text: str) -> str:
        """Convert plain text summary to formatted HTML"""
        html = summary_text.replace('\n\n', '</p><p>')
        html = html.replace('\n• ', '<br>• ')
        html = html.replace('\n## ', '</p><h3>')
        html = html.replace('\n### ', '</p><h4>')

        if not html.startswith('<'):
            html = '<p>' + html
        if not html.endswith('>'):
            html = html + '</p>'

        return html

    async def _extract_audio_from_video(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None
    ) -> Optional[str]:
        """
        Extract audio from video file using ffmpeg

        Args:
            video_path: Path to video file
            progress_callback: Optional callback to send keepalive events during processing

        Returns:
            Path to extracted audio file (MP3), or None if failed
        """
        import tempfile
        import subprocess

        try:
            # Create temp audio file
            temp_dir = os.path.dirname(video_path)
            audio_path = os.path.join(temp_dir, "extracted_audio.mp3")

            self.logger.info(f"🎵 [AUDIO EXTRACTION] Extracting audio from video using ffmpeg...")

            # Use ffmpeg to extract audio
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vn",  # No video
                "-acodec", "libmp3lame",  # MP3 codec
                "-b:a", "192k",  # 192kbps bitrate
                "-y",  # Overwrite output file
                audio_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Send keepalive events while ffmpeg is running to prevent SSE timeout
            keepalive_task = None
            if progress_callback:
                async def send_keepalive():
                    """Send periodic keepalive events during long-running ffmpeg operation"""
                    count = 0
                    while True:
                        await asyncio.sleep(5)  # Send keepalive every 5 seconds
                        count += 1
                        await progress_callback("extracting_audio_progress", {
                            "message": f"Extracting audio from video... ({count * 5}s elapsed)"
                        })

                keepalive_task = asyncio.create_task(send_keepalive())

            try:
                stdout, stderr = await process.communicate()
            finally:
                # Cancel keepalive task when ffmpeg completes
                if keepalive_task:
                    keepalive_task.cancel()
                    try:
                        await keepalive_task
                    except asyncio.CancelledError:
                        pass

            if process.returncode == 0 and os.path.exists(audio_path):
                file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
                self.logger.info(f"✅ [AUDIO EXTRACTION] Extracted audio: {file_size_mb:.1f}MB")
                return audio_path
            else:
                error_msg = stderr.decode('utf-8', errors='ignore')[:500]
                self.logger.error(f"❌ [AUDIO EXTRACTION] Failed: {error_msg}")
                return None

        except Exception as e:
            self.logger.error(f"❌ [AUDIO EXTRACTION] Error: {e}", exc_info=True)
            return None

    async def _download_video_for_frames(self, url: str) -> Optional[str]:
        """
        Download full video file for frame extraction

        This is a wrapper around _download_video_with_ytdlp that creates
        a temp directory and downloads the full video (not just audio).

        Args:
            url: Video URL

        Returns:
            Path to downloaded video file, or None if failed
        """
        import tempfile
        import glob

        try:
            # TODO: TEMPORARY - Disabled cleanup to preserve videos for testing
            # Clean up any old video_frames_* temp directories first
            # temp_base = tempfile.gettempdir()
            # old_temp_dirs = glob.glob(os.path.join(temp_base, "video_frames_*"))
            # for old_dir in old_temp_dirs:
            #     try:
            #         import shutil
            #         shutil.rmtree(old_dir)
            #         self.logger.info(f"🧹 Cleaned up old temp directory: {old_dir}")
            #     except Exception as e:
            #         self.logger.warning(f"⚠️ Could not clean up old temp directory {old_dir}: {e}")

            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="video_frames_")
            temp_template = os.path.join(temp_dir, f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

            self.logger.info(f"📥 [VIDEO DOWNLOAD] Downloading video from: {url[:100]}...")

            # Use unified download method with download_video=True
            downloaded_path = self._download_video_with_ytdlp(
                url,
                temp_template,
                referer=url,
                download_video=True  # Download full video, not audio
            )

            if downloaded_path:
                self.logger.info(f"✅ Downloaded video for frames: {downloaded_path}")
                return downloaded_path
            else:
                self.logger.error(f"❌ Video download failed")
                # Clean up temp directory
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except:
                    pass
                return None

        except Exception as e:
            self.logger.error(f"❌ Error downloading video: {e}", exc_info=True)
            return None

    async def _extract_and_upload_frames(
        self,
        video_path: str,
        article_url: str,
        article_id: Optional[int] = None
    ) -> List[Dict[str, any]]:
        """
        Extract frames from video and upload to Supabase storage

        Args:
            video_path: Path to video file
            article_url: URL of the article (for logging)
            article_id: Article ID for storage path (optional, will use temp ID if not provided)

        Returns:
            List of frame dictionaries with URLs and timestamps
        """
        from processors.frame_extractor import FrameExtractor
        from core.storage_manager import StorageManager

        try:
            # Use a temporary article ID if not provided (will be updated later)
            temp_article_id = article_id or 0

            # Extract frames
            extractor = FrameExtractor(min_interval_seconds=30)
            frames = await extractor.extract_frames(video_path)

            if not frames:
                self.logger.warning("⚠️ No frames extracted from video")
                extractor.cleanup()
                return []

            # Upload frames to Supabase storage
            storage_manager = StorageManager()
            uploaded_frames = []

            for frame in frames:
                success, storage_path, public_url = storage_manager.upload_frame(
                    frame["path"],
                    temp_article_id,
                    frame["timestamp_seconds"]
                )

                if success:
                    uploaded_frames.append({
                        "url": public_url,
                        "storage_path": storage_path,
                        "timestamp_seconds": frame["timestamp_seconds"],
                        "time_formatted": frame["time_formatted"],
                        "perceptual_hash": frame.get("hash")
                    })
                else:
                    self.logger.warning(f"⚠️ Failed to upload frame at {frame['time_formatted']}")

            # Clean up temporary frames
            extractor.cleanup()

            self.logger.info(f"✅ Uploaded {len(uploaded_frames)} frames to storage")
            return uploaded_frames

        except Exception as e:
            self.logger.error(f"❌ Frame extraction and upload failed: {e}", exc_info=True)
            return []

    # ============================================================================
    # MEDIA PERSISTENCE METHODS (Phase 2)
    # ============================================================================

    def _is_direct_upload_url(self, url: str) -> bool:
        """
        Check if a URL is a direct upload from Supabase storage.

        Direct uploads are already stored permanently in the 'uploaded-media' bucket,
        so we should not duplicate them to the 'article-media' bucket.

        Args:
            url: Article URL to check

        Returns:
            True if this is a direct upload URL
        """
        return 'supabase.co/storage' in url and 'uploaded-media' in url

    def _detect_content_type(self, file_path: str) -> str:
        """
        Detect MIME content type from file extension.

        Args:
            file_path: Path to the file

        Returns:
            MIME type string
        """
        ext = Path(file_path).suffix.lower()
        mime_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
        }
        return mime_types.get(ext, 'application/octet-stream')

    def _get_media_duration(self, file_path: str) -> Optional[float]:
        """
        Get duration of a media file in seconds using ffprobe.

        Args:
            file_path: Path to the media file

        Returns:
            Duration in seconds, or None if detection fails
        """
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except Exception as e:
            self.logger.warning(f"⚠️ Could not get media duration: {e}")
        return None

    async def _persist_media_to_storage(
        self,
        file_path: str,
        article_id: int,
        article_type: str,
        article_url: str
    ) -> bool:
        """
        Persist downloaded media file to Supabase storage for later reprocessing.

        This is called after downloading media during article processing.
        Direct uploads are skipped since they're already stored permanently.

        Args:
            file_path: Local path to the downloaded media file
            article_id: Database ID of the article
            article_type: 'public' or 'private'
            article_url: Original article URL (to check if it's a direct upload)

        Returns:
            True if media was persisted successfully
        """
        # Skip if media persistence is disabled
        if not self.persist_media:
            self.logger.info("   📦 [MEDIA PERSIST] Media persistence disabled, skipping storage")
            return False

        # Skip direct uploads - they're already stored permanently
        if self._is_direct_upload_url(article_url):
            self.logger.info("   📦 [MEDIA PERSIST] Direct upload detected - already stored in uploaded-media bucket")
            # Still update the database to reference the existing storage
            return await self._update_media_storage_info_for_direct_upload(
                article_id, article_type, article_url, file_path
            )

        try:
            from core.storage_manager import StorageManager

            # Get file metadata
            file_size = os.path.getsize(file_path)
            content_type = self._detect_content_type(file_path)
            duration = self._get_media_duration(file_path)

            self.logger.info(f"   📦 [MEDIA PERSIST] Uploading media to storage ({file_size / 1024 / 1024:.1f}MB)...")

            # Upload to storage
            storage = StorageManager()
            success, storage_path = storage.upload_article_media(
                file_path=file_path,
                article_id=article_id,
                article_type=article_type,
                content_type=content_type
            )

            if not success:
                self.logger.error("   ❌ [MEDIA PERSIST] Failed to upload media to storage")
                return False

            # Update database with storage info
            table = 'private_articles' if article_type == 'private' else 'articles'
            bucket_name = StorageManager.ARTICLE_MEDIA_BUCKET_NAME

            update_data = {
                'media_storage_path': storage_path,
                'media_storage_bucket': bucket_name,
                'media_uploaded_at': datetime.utcnow().isoformat(),
                'media_content_type': content_type,
                'media_size_bytes': file_size,
                'media_duration_seconds': duration
            }

            self.supabase.table(table).update(update_data).eq('id', article_id).execute()

            self.logger.info(f"   ✅ [MEDIA PERSIST] Media stored: {bucket_name}/{storage_path}")
            return True

        except Exception as e:
            self.logger.error(f"   ❌ [MEDIA PERSIST] Error persisting media: {e}", exc_info=True)
            return False

    async def _update_media_storage_info_for_direct_upload(
        self,
        article_id: int,
        article_type: str,
        article_url: str,
        file_path: str
    ) -> bool:
        """
        Update database with storage info for a direct upload.

        Direct uploads are already stored in the 'uploaded-media' bucket,
        so we just need to record the reference in the database columns.

        Args:
            article_id: Database ID of the article
            article_type: 'public' or 'private'
            article_url: The Supabase storage URL
            file_path: Local path to the file (for size/duration info)

        Returns:
            True if database was updated successfully
        """
        try:
            from core.storage_manager import StorageManager
            from urllib.parse import urlparse

            # Extract storage path from URL
            # URL format: https://xxx.supabase.co/storage/v1/object/public/uploaded-media/user_xxx/timestamp_filename.ext
            parsed = urlparse(article_url)
            path_parts = parsed.path.split('/uploaded-media/')
            if len(path_parts) > 1:
                storage_path = path_parts[1]
            else:
                storage_path = parsed.path

            # Get file metadata
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
            content_type = self._detect_content_type(file_path) if file_path else None
            duration = self._get_media_duration(file_path) if file_path and os.path.exists(file_path) else None

            # Update database - direct uploads use 'uploaded-media' bucket
            table = 'private_articles' if article_type == 'private' else 'articles'

            update_data = {
                'media_storage_path': storage_path,
                'media_storage_bucket': StorageManager.MEDIA_BUCKET_NAME,  # 'uploaded-media'
                'media_uploaded_at': datetime.utcnow().isoformat(),
                'media_content_type': content_type,
                'media_size_bytes': file_size,
                'media_duration_seconds': duration
            }

            self.supabase.table(table).update(update_data).eq('id', article_id).execute()

            self.logger.info(f"   ✅ [MEDIA PERSIST] Direct upload reference saved: uploaded-media/{storage_path}")
            return True

        except Exception as e:
            self.logger.error(f"   ❌ [MEDIA PERSIST] Error updating direct upload info: {e}", exc_info=True)
            return False

    def _is_media_available(self, article: Dict) -> tuple:
        """
        Check if stored media is available for reprocessing.

        Args:
            article: Article record from database

        Returns:
            Tuple of (is_available, reason_if_not)
        """
        storage_path = article.get('media_storage_path')
        storage_bucket = article.get('media_storage_bucket')
        uploaded_at = article.get('media_uploaded_at')

        if not storage_path:
            return False, "No stored media - re-process article with media persistence enabled"

        # Direct uploads (uploaded-media bucket) never expire
        if storage_bucket == 'uploaded-media':
            return True, None

        # Check TTL for article-media bucket
        if uploaded_at:
            try:
                uploaded_dt = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                expiry_dt = uploaded_dt + timedelta(days=self.media_retention_days)
                if datetime.utcnow().replace(tzinfo=uploaded_dt.tzinfo) > expiry_dt:
                    return False, f"Media expired on {expiry_dt.strftime('%Y-%m-%d')} - re-process article"
            except Exception:
                pass

        return True, None

    # ============================================================================
    # REPROCESSING METHODS
    # ============================================================================

    async def reprocess_article(
        self,
        article_id: int,
        article_type: str,
        steps: List[str],
        user_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None
    ) -> Dict:
        """
        Partial reprocessing of an existing article.

        This method allows regenerating specific parts of an article without
        re-downloading content. Useful for:
        - Regenerating AI summary with updated prompts
        - Adding themed insights to existing articles
        - Regenerating embeddings after schema changes

        Args:
            article_id: Database ID of the article
            article_type: 'public' or 'private'
            steps: List of steps to run. Available:
                - 'ai_summary': Regenerate summary, insights, quotes from existing transcript
                - 'themed_insights': Regenerate themed insights (private articles only)
                - 'embedding': Regenerate vector embedding
            user_id: Required for themed_insights (to look up org themes)
            progress_callback: Optional async callback for progress updates
                Signature: async def callback(event_type: str, data: dict)

        Returns:
            Dict with results of each step:
            {
                'ai_summary': {'success': True, 'insights_count': 5, ...},
                'themed_insights': {'success': True, 'themes_count': 2},
                'embedding': {'success': True}
            }

        Raises:
            ValueError: If article not found or invalid parameters
        """
        self.logger.info(f"🔄 Reprocessing {article_type} article {article_id}")
        self.logger.info(f"   Steps: {steps}")

        # Step 1: Fetch article from database
        table = 'private_articles' if article_type == 'private' else 'articles'

        try:
            result = self.supabase.table(table).select('*').eq('id', article_id).single().execute()
            if not result.data:
                raise ValueError(f"Article {article_id} not found in {table}")
            article = result.data
        except Exception as e:
            raise ValueError(f"Failed to fetch article: {e}")

        self.logger.info(f"   Title: {article.get('title', 'Unknown')}")

        if progress_callback:
            await progress_callback('article_loaded', {
                'article_id': article_id,
                'title': article.get('title'),
                'content_source': article.get('content_source')
            })

        # Step 2: Reconstruct metadata from stored fields
        metadata = self._reconstruct_metadata_from_article(article)

        results = {}

        # Step 3: Execute requested steps
        if 'ai_summary' in steps:
            results['ai_summary'] = await self._reprocess_ai_summary(
                article, metadata, article_type, progress_callback
            )

        if 'themed_insights' in steps:
            results['themed_insights'] = await self._reprocess_themed_insights(
                article, article_id, article_type, metadata, results.get('ai_summary'),
                user_id, progress_callback
            )

        if 'embedding' in steps:
            results['embedding'] = await self._reprocess_embedding(
                article, article_id, article_type, results.get('ai_summary'), progress_callback
            )

        # Phase 2: Media-based reprocessing
        if 'video_frames' in steps:
            results['video_frames'] = await self._reprocess_video_frames(
                article, article_id, article_type, progress_callback
            )

        if 'transcript' in steps:
            results['transcript'] = await self._reprocess_transcript(
                article, article_id, article_type, progress_callback
            )

        self.logger.info(f"✅ Reprocessing complete for article {article_id}")
        return results

    def _reconstruct_metadata_from_article(self, article: Dict) -> Dict:
        """
        Reconstruct metadata dict from database article record.

        This allows reusing the existing AI summary generation methods
        which expect a metadata dict with specific structure.

        Args:
            article: Article record from database

        Returns:
            Reconstructed metadata dict
        """
        # Parse transcript data from database
        transcript_text = article.get('transcript_text', '')
        transcripts = {}

        if transcript_text and article.get('video_id'):
            # Reconstruct transcript in the format expected by AI
            segments = self._parse_transcript_text(transcript_text)

            transcripts[article['video_id']] = {
                'success': True,
                'type': 'existing',
                'transcript': segments,
                'segments': segments,
                'words': []  # Word-level timing not stored, use empty
            }

        # Reconstruct content type
        content_source = article.get('content_source', 'article')
        content_type = ContentType(
            has_embedded_video=(content_source == 'video' or content_source == 'mixed'),
            has_embedded_audio=(content_source == 'audio' or content_source == 'mixed'),
            is_text_only=(content_source == 'article'),
            video_urls=[{
                'video_id': article.get('video_id'),
                'platform': article.get('platform'),
                'url': article.get('url')
            }] if article.get('video_id') else [],
            audio_urls=[{
                'url': article.get('audio_url'),
                'platform': article.get('platform')
            }] if article.get('audio_url') else []
        )

        # Build metadata
        metadata = {
            'title': article.get('title'),
            'url': article.get('url'),
            'platform': article.get('platform'),
            'content_type': content_type,
            'article_text': article.get('original_article_text', '') or article.get('article_text', ''),
            'transcripts': transcripts,
            'media_info': {
                'video_urls': content_type.video_urls,
                'audio_urls': content_type.audio_urls
            },
            'video_frames': article.get('video_frames', [])
        }

        return metadata

    def _parse_transcript_text(self, transcript_text: str) -> List[Dict]:
        """
        Parse formatted transcript text back into segments.

        Handles formats like:
        - [MM:SS] text
        - [H:MM:SS] text

        Args:
            transcript_text: Formatted transcript from database

        Returns:
            List of segment dicts with 'start' and 'text' keys
        """
        import re

        segments = []
        for line in transcript_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Parse [MM:SS] or [H:MM:SS] format
            match = re.match(r'^\[(\d+):(\d+)(?::(\d+))?\]\s*(.*)$', line)
            if match:
                if match.group(3):  # H:MM:SS format
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    seconds = int(match.group(3))
                    start_time = hours * 3600 + minutes * 60 + seconds
                    text = match.group(4)
                else:  # MM:SS format
                    minutes = int(match.group(1))
                    seconds = int(match.group(2))
                    start_time = minutes * 60 + seconds
                    text = match.group(4)

                if text:
                    segments.append({
                        'start': start_time,
                        'text': text.strip()
                    })

        return segments

    async def _reprocess_ai_summary(
        self,
        article: Dict,
        metadata: Dict,
        article_type: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Regenerate AI summary from existing transcript/article text.

        Args:
            article: Original article record from database
            metadata: Reconstructed metadata
            article_type: 'public' or 'private'
            progress_callback: Optional progress callback

        Returns:
            Dict with success status and summary details
        """
        self.logger.info("🤖 Regenerating AI summary...")

        if progress_callback:
            await progress_callback('ai_summary_start', {})

        # Check prerequisites
        content_source = article.get('content_source', 'article')
        has_transcript = bool(article.get('transcript_text'))
        has_article_text = bool(article.get('original_article_text') or article.get('article_text'))

        if content_source in ('video', 'audio') and not has_transcript:
            error_msg = f"Cannot regenerate summary: {content_source} content has no transcript. Transcribe first."
            self.logger.error(f"   ❌ {error_msg}")
            if progress_callback:
                await progress_callback('ai_summary_error', {'error': error_msg})
            return {'success': False, 'error': error_msg}

        if content_source == 'article' and not has_article_text:
            error_msg = "Cannot regenerate summary: article has no text content."
            self.logger.error(f"   ❌ {error_msg}")
            if progress_callback:
                await progress_callback('ai_summary_error', {'error': error_msg})
            return {'success': False, 'error': error_msg}

        try:
            # Enrich video frames with transcript excerpts if they exist
            if metadata.get('video_frames'):
                self.logger.info("   📝 Enriching video frames with transcript excerpts...")
                self._enrich_frames_with_transcript(metadata)

            # Generate new AI summary
            ai_summary = await self._generate_summary_async(article['url'], metadata)

            # Update database
            table = 'private_articles' if article_type == 'private' else 'articles'
            update_data = {
                'summary_text': ai_summary.get('summary', ''),
                'key_insights': ai_summary.get('key_insights', []),
                'quotes': ai_summary.get('quotes', []),
                'duration_minutes': ai_summary.get('duration_minutes'),
                'word_count': ai_summary.get('word_count'),
                'topics': ai_summary.get('topics', [])
            }

            # Include enriched video_frames if they exist
            if metadata.get('video_frames'):
                update_data['video_frames'] = metadata['video_frames']

            self.supabase.table(table).update(update_data).eq('id', article['id']).execute()

            self.logger.info(f"   ✅ AI summary regenerated ({len(ai_summary.get('key_insights', []))} insights)")

            if progress_callback:
                await progress_callback('ai_summary_complete', {
                    'insights_count': len(ai_summary.get('key_insights', [])),
                    'quotes_count': len(ai_summary.get('quotes', []))
                })

            return {
                'success': True,
                'insights_count': len(ai_summary.get('key_insights', [])),
                'quotes_count': len(ai_summary.get('quotes', [])),
                'ai_summary': ai_summary  # Pass along for themed insights
            }

        except Exception as e:
            self.logger.error(f"   ❌ AI summary failed: {e}")
            if progress_callback:
                await progress_callback('ai_summary_error', {'error': str(e)})
            return {'success': False, 'error': str(e)}

    async def _reprocess_themed_insights(
        self,
        article: Dict,
        article_id: int,
        article_type: str,
        metadata: Dict,
        ai_summary_result: Optional[Dict],
        user_id: Optional[str],
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Regenerate themed insights for a private article.

        Args:
            article: Original article record from database
            article_id: Article ID
            article_type: Must be 'private'
            metadata: Reconstructed metadata
            ai_summary_result: Result from AI summary step (if run)
            user_id: User ID for org lookup
            progress_callback: Optional progress callback

        Returns:
            Dict with success status and themes count
        """
        self.logger.info("🎯 Regenerating themed insights...")

        if progress_callback:
            await progress_callback('themed_insights_start', {})

        # Check prerequisites
        if article_type != 'private':
            error_msg = "Themed insights only available for private articles"
            self.logger.warning(f"   ⚠️ {error_msg}")
            if progress_callback:
                await progress_callback('themed_insights_error', {'error': error_msg})
            return {'success': False, 'error': error_msg}

        if not user_id:
            error_msg = "User ID required for themed insights (to look up organization themes)"
            self.logger.error(f"   ❌ {error_msg}")
            if progress_callback:
                await progress_callback('themed_insights_error', {'error': error_msg})
            return {'success': False, 'error': error_msg}

        try:
            # Build ai_summary from existing data or from just-generated summary
            if ai_summary_result and ai_summary_result.get('ai_summary'):
                ai_summary = ai_summary_result['ai_summary']
            else:
                # Use existing summary from database
                ai_summary = {
                    'summary': article.get('summary_text', ''),
                    'key_insights': article.get('key_insights', [])
                }

            # Generate themed insights
            themed_data = await self._generate_themed_insights_async(
                user_id=user_id,
                metadata=metadata,
                ai_summary=ai_summary
            )

            if themed_data:
                # Save themed insights (method handles delete + insert)
                self._save_themed_insights(article_id, themed_data)

                themes_count = len(themed_data.get('insights', []))
                self.logger.info(f"   ✅ Themed insights regenerated ({themes_count} themes)")

                if progress_callback:
                    await progress_callback('themed_insights_complete', {
                        'themes_count': themes_count
                    })

                return {'success': True, 'themes_count': themes_count}
            else:
                self.logger.info("   ℹ️ No themed insights generated (no matching themes)")
                if progress_callback:
                    await progress_callback('themed_insights_complete', {'themes_count': 0})
                return {'success': True, 'themes_count': 0}

        except Exception as e:
            self.logger.error(f"   ❌ Themed insights failed: {e}")
            if progress_callback:
                await progress_callback('themed_insights_error', {'error': str(e)})
            return {'success': False, 'error': str(e)}

    async def _reprocess_embedding(
        self,
        article: Dict,
        article_id: int,
        article_type: str,
        ai_summary_result: Optional[Dict],
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Regenerate vector embedding for semantic search.

        Args:
            article: Original article record from database
            article_id: Article ID
            article_type: 'public' or 'private'
            ai_summary_result: Result from AI summary step (if run, use fresh data)
            progress_callback: Optional progress callback

        Returns:
            Dict with success status
        """
        self.logger.info("🔢 Regenerating embedding...")

        if progress_callback:
            await progress_callback('embedding_start', {})

        if not self.openai_client:
            error_msg = "OpenAI client not initialized - cannot generate embedding"
            self.logger.error(f"   ❌ {error_msg}")
            if progress_callback:
                await progress_callback('embedding_error', {'error': error_msg})
            return {'success': False, 'error': error_msg}

        try:
            # Build embedding text from article data
            # Use fresh AI summary if available, otherwise use stored data
            if ai_summary_result and ai_summary_result.get('ai_summary'):
                ai_summary = ai_summary_result['ai_summary']
            else:
                ai_summary = {
                    'summary': article.get('summary_text', ''),
                    'key_insights': article.get('key_insights', [])
                }

            # Reconstruct minimal metadata for embedding
            metadata = {
                'title': article.get('title', ''),
                'article_text': article.get('original_article_text', '') or article.get('article_text', '')
            }

            embedding_text = self._build_embedding_text(metadata, ai_summary)
            embedding = self._generate_embedding(embedding_text)

            if embedding:
                # Update database
                table = 'private_articles' if article_type == 'private' else 'articles'
                self.supabase.table(table).update({'embedding': embedding}).eq('id', article_id).execute()

                self.logger.info(f"   ✅ Embedding regenerated")

                if progress_callback:
                    await progress_callback('embedding_complete', {})

                return {'success': True}
            else:
                error_msg = "Embedding generation returned None"
                self.logger.error(f"   ❌ {error_msg}")
                if progress_callback:
                    await progress_callback('embedding_error', {'error': error_msg})
                return {'success': False, 'error': error_msg}

        except Exception as e:
            self.logger.error(f"   ❌ Embedding failed: {e}")
            if progress_callback:
                await progress_callback('embedding_error', {'error': str(e)})
            return {'success': False, 'error': str(e)}

    # ============================================================================
    # PHASE 2 REPROCESSING METHODS
    # ============================================================================

    async def _reprocess_video_frames(
        self,
        article: Dict,
        article_id: int,
        article_type: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Re-extract video frames from stored media.

        This downloads the stored media from Supabase Storage, extracts frames
        using FFmpeg, and uploads new frames to the video-frames bucket.

        Args:
            article: Article record from database
            article_id: Article ID
            article_type: 'public' or 'private'
            progress_callback: Optional progress callback

        Returns:
            Dict with success status and frame count
        """
        import tempfile
        import shutil

        self.logger.info("🎬 Re-extracting video frames from stored media...")

        if progress_callback:
            await progress_callback('video_frames_start', {})

        # Check if media is available
        is_available, unavailable_reason = self._is_media_available(article)
        if not is_available:
            self.logger.error(f"   ❌ {unavailable_reason}")
            if progress_callback:
                await progress_callback('video_frames_error', {'error': unavailable_reason})
            return {'success': False, 'error': unavailable_reason}

        temp_dir = None
        try:
            from core.storage_manager import StorageManager

            storage_path = article['media_storage_path']
            storage_bucket = article.get('media_storage_bucket', StorageManager.ARTICLE_MEDIA_BUCKET_NAME)

            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="reprocess_frames_")
            local_path = os.path.join(temp_dir, "media.mp4")

            self.logger.info(f"   📥 Downloading media from {storage_bucket}/{storage_path}...")

            # Download from storage
            storage = StorageManager()
            success = storage.download_article_media(
                storage_path=storage_path,
                destination_path=local_path,
                bucket_name=storage_bucket
            )

            if not success:
                error_msg = "Failed to download media from storage"
                self.logger.error(f"   ❌ {error_msg}")
                if progress_callback:
                    await progress_callback('video_frames_error', {'error': error_msg})
                return {'success': False, 'error': error_msg}

            file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
            self.logger.info(f"   ✅ Downloaded media: {file_size_mb:.1f}MB")

            # Extract and upload frames
            self.logger.info("   🎞️ Extracting frames...")
            frames = await self._extract_and_upload_frames(
                video_path=local_path,
                article_url=article['url'],
                article_id=article_id
            )

            if not frames:
                error_msg = "No frames extracted from video"
                self.logger.warning(f"   ⚠️ {error_msg}")
                if progress_callback:
                    await progress_callback('video_frames_error', {'error': error_msg})
                return {'success': False, 'error': error_msg}

            # Update database with new frames
            table = 'private_articles' if article_type == 'private' else 'articles'
            self.supabase.table(table).update({
                'video_frames': frames
            }).eq('id', article_id).execute()

            self.logger.info(f"   ✅ Extracted and uploaded {len(frames)} frames")

            if progress_callback:
                await progress_callback('video_frames_complete', {'frame_count': len(frames)})

            return {'success': True, 'frame_count': len(frames)}

        except Exception as e:
            self.logger.error(f"   ❌ Video frame extraction failed: {e}", exc_info=True)
            if progress_callback:
                await progress_callback('video_frames_error', {'error': str(e)})
            return {'success': False, 'error': str(e)}

        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

    async def _reprocess_transcript(
        self,
        article: Dict,
        article_id: int,
        article_type: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Regenerate transcript from stored media using Deepgram.

        This downloads the stored media and transcribes it fresh using Deepgram,
        useful when:
        - YouTube transcript wasn't available originally
        - Want higher quality transcript
        - Original transcription had errors

        Args:
            article: Article record from database
            article_id: Article ID
            article_type: 'public' or 'private'
            progress_callback: Optional progress callback

        Returns:
            Dict with success status and word count
        """
        import tempfile
        import shutil

        self.logger.info("🎤 Regenerating transcript from stored media...")

        if progress_callback:
            await progress_callback('transcript_start', {})

        # Check if file transcriber is available
        if not self.file_transcriber:
            error_msg = "File transcriber (Deepgram) not available"
            self.logger.error(f"   ❌ {error_msg}")
            if progress_callback:
                await progress_callback('transcript_error', {'error': error_msg})
            return {'success': False, 'error': error_msg}

        # Check if media is available
        is_available, unavailable_reason = self._is_media_available(article)
        if not is_available:
            self.logger.error(f"   ❌ {unavailable_reason}")
            if progress_callback:
                await progress_callback('transcript_error', {'error': unavailable_reason})
            return {'success': False, 'error': unavailable_reason}

        temp_dir = None
        try:
            from core.storage_manager import StorageManager

            storage_path = article['media_storage_path']
            storage_bucket = article.get('media_storage_bucket', StorageManager.ARTICLE_MEDIA_BUCKET_NAME)

            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="reprocess_transcript_")
            local_path = os.path.join(temp_dir, "media.mp4")

            self.logger.info(f"   📥 Downloading media from {storage_bucket}/{storage_path}...")

            # Download from storage
            storage = StorageManager()
            success = storage.download_article_media(
                storage_path=storage_path,
                destination_path=local_path,
                bucket_name=storage_bucket
            )

            if not success:
                error_msg = "Failed to download media from storage"
                self.logger.error(f"   ❌ {error_msg}")
                if progress_callback:
                    await progress_callback('transcript_error', {'error': error_msg})
                return {'success': False, 'error': error_msg}

            file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
            self.logger.info(f"   ✅ Downloaded media: {file_size_mb:.1f}MB")

            # Transcribe with Deepgram
            self.logger.info("   🎯 Transcribing with Deepgram...")
            transcript_result = self.file_transcriber.transcribe(local_path)

            if not transcript_result or not transcript_result.get('success'):
                error_msg = transcript_result.get('error', 'Transcription failed') if transcript_result else 'Transcription failed'
                self.logger.error(f"   ❌ {error_msg}")
                if progress_callback:
                    await progress_callback('transcript_error', {'error': error_msg})
                return {'success': False, 'error': error_msg}

            # Format transcript text
            segments = transcript_result.get('segments', [])
            transcript_lines = []
            for segment in segments:
                start_time = segment.get('start', 0)
                text = segment.get('text', '').strip()
                if text:
                    minutes = int(start_time // 60)
                    seconds = int(start_time % 60)
                    transcript_lines.append(f"[{minutes}:{seconds:02d}] {text}")

            transcript_text = "\n".join(transcript_lines)
            word_count = len(transcript_text.split())

            # Update database
            table = 'private_articles' if article_type == 'private' else 'articles'
            self.supabase.table(table).update({
                'transcript_text': transcript_text
            }).eq('id', article_id).execute()

            self.logger.info(f"   ✅ Transcript regenerated: {word_count} words")

            if progress_callback:
                await progress_callback('transcript_complete', {'word_count': word_count})

            return {'success': True, 'word_count': word_count}

        except Exception as e:
            self.logger.error(f"   ❌ Transcript regeneration failed: {e}", exc_info=True)
            if progress_callback:
                await progress_callback('transcript_error', {'error': str(e)})
            return {'success': False, 'error': str(e)}

        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

    def get_article_reprocess_info(self, article_id: int, article_type: str) -> Dict:
        """
        Get information about an article for the reprocessing UI.

        Returns details about what data exists and what reprocessing
        options are available.

        Args:
            article_id: Database ID of the article
            article_type: 'public' or 'private'

        Returns:
            Dict with article info and available operations
        """
        table = 'private_articles' if article_type == 'private' else 'articles'

        try:
            result = self.supabase.table(table).select('*').eq('id', article_id).single().execute()
            if not result.data:
                return {'error': f'Article {article_id} not found'}

            article = result.data

            # Determine what operations are available
            content_source = article.get('content_source', 'article')
            has_transcript = bool(article.get('transcript_text'))
            has_article_text = bool(article.get('original_article_text') or article.get('article_text'))
            has_video_frames = bool(article.get('video_frames'))
            video_frame_count = len(article.get('video_frames', []))

            # Check for existing themed insights (private only)
            themed_insights_count = 0
            if article_type == 'private':
                try:
                    insights_result = self.supabase.table('private_article_themed_insights').select(
                        'id', count='exact'
                    ).eq('private_article_id', article_id).execute()
                    themed_insights_count = insights_result.count or 0
                except:
                    pass

            # Determine availability
            can_regen_summary = (
                (content_source in ('video', 'audio') and has_transcript) or
                (content_source == 'article' and has_article_text) or
                (content_source == 'mixed' and (has_transcript or has_article_text))
            )

            summary_unavailable_reason = None
            if not can_regen_summary:
                if content_source in ('video', 'audio'):
                    summary_unavailable_reason = "No transcript available - transcribe first"
                else:
                    summary_unavailable_reason = "No article text available"

            # Phase 2: Check media availability for video_frames and transcript reprocessing
            media_available, media_unavailable_reason = self._is_media_available(article)
            has_stored_media = bool(article.get('media_storage_path'))
            media_storage_bucket = article.get('media_storage_bucket')
            media_size_bytes = article.get('media_size_bytes')
            media_uploaded_at = article.get('media_uploaded_at')

            # Calculate days remaining for TTL media
            media_days_remaining = None
            if has_stored_media and media_uploaded_at and media_storage_bucket != 'uploaded-media':
                try:
                    uploaded_dt = datetime.fromisoformat(media_uploaded_at.replace('Z', '+00:00'))
                    expiry_dt = uploaded_dt + timedelta(days=self.media_retention_days)
                    days_remaining = (expiry_dt - datetime.utcnow().replace(tzinfo=uploaded_dt.tzinfo)).days
                    media_days_remaining = max(0, days_remaining)
                except Exception:
                    pass

            # Can regenerate video frames if media is available and content is video
            can_regen_video_frames = media_available and content_source in ('video', 'mixed')
            video_frames_unavailable_reason = None
            if not can_regen_video_frames:
                if content_source not in ('video', 'mixed'):
                    video_frames_unavailable_reason = "Not a video article"
                else:
                    video_frames_unavailable_reason = media_unavailable_reason

            # Can regenerate transcript if media is available and content is video/audio
            can_regen_transcript = media_available and content_source in ('video', 'audio', 'mixed')
            transcript_unavailable_reason = None
            if not can_regen_transcript:
                if content_source not in ('video', 'audio', 'mixed'):
                    transcript_unavailable_reason = "Not a video/audio article"
                else:
                    transcript_unavailable_reason = media_unavailable_reason

            return {
                'id': article_id,
                'type': article_type,
                'title': article.get('title'),
                'url': article.get('url'),
                'content_source': content_source,
                'platform': article.get('platform'),
                'created_at': article.get('created_at'),
                'updated_at': article.get('updated_at'),

                # Current state
                'has_transcript': has_transcript,
                'has_article_text': has_article_text,
                'has_video_frames': has_video_frames,
                'video_frame_count': video_frame_count,
                'has_summary': bool(article.get('summary_text')),
                'has_insights': bool(article.get('key_insights')),
                'insights_count': len(article.get('key_insights', [])),
                'has_embedding': bool(article.get('embedding')),
                'themed_insights_count': themed_insights_count,

                # Phase 1 available operations
                'can_regen_summary': can_regen_summary,
                'summary_unavailable_reason': summary_unavailable_reason,
                'can_regen_themed_insights': article_type == 'private',
                'can_regen_embedding': True,

                # Phase 2: Media storage info
                'has_stored_media': has_stored_media,
                'media_storage_bucket': media_storage_bucket,
                'media_size_mb': round(media_size_bytes / 1024 / 1024, 1) if media_size_bytes else None,
                'media_uploaded_at': media_uploaded_at,
                'media_days_remaining': media_days_remaining,
                'media_is_permanent': media_storage_bucket == 'uploaded-media',

                # Phase 2 available operations
                'can_regen_video_frames': can_regen_video_frames,
                'video_frames_unavailable_reason': video_frames_unavailable_reason,
                'can_regen_transcript': can_regen_transcript,
                'transcript_unavailable_reason': transcript_unavailable_reason
            }

        except Exception as e:
            return {'error': str(e)}


def main():
    """Main entry point for CLI usage"""
    if len(sys.argv) != 2:
        print("Usage: python3 article_processor.py <url>")
        sys.exit(1)

    url = sys.argv[1]

    try:
        processor = ArticleProcessor()

        # Check if article already exists
        existing = processor.check_article_exists(url)
        if existing:
            print(f"⚠️  Article already exists in database!")
            print(f"   ID: {existing['id']}")
            print(f"   Title: {existing['title']}")
            print(f"   Created: {existing['created_at']}")
            print(f"   Updated: {existing['updated_at']}")
            print(f"   View at: http://localhost:3000/article/{existing['id']}")
            print(f"\n❓ This will reprocess the article (costs API calls for transcription + AI summary)")
            print(f"   Continue anyway? (y/n): ", end='')

            response = input().strip().lower()
            if response != 'y':
                print("Cancelled. No processing performed.")
                sys.exit(0)
            print("\n🔄 Reprocessing article...")

        article_id = processor.process_article(url)
        print(f"✅ Success! Article ID: {article_id}")
        print(f"   View at: http://localhost:3000/article/{article_id}")

    except Exception as e:
        print(f"❌ ERROR: Processing failed - {e}")
        print(f"❌ Article was NOT saved to database")
        print(f"❌ Please check the error above and fix the issue before retrying")
        sys.exit(1)


if __name__ == "__main__":
    main()