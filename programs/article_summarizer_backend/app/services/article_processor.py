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
from datetime import datetime
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
    create_metadata_for_prompt
)
from processors.transcript_processor import TranscriptProcessor
from processors.file_transcriber import FileTranscriber


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

    async def process_article(self, url: str, user_id: Optional[str] = None) -> str:
        """
        Main processing pipeline for any article type

        Args:
            url: URL of the article to process
            user_id: Optional user ID for authentication (Supabase auth user)

        Returns:
            Path to generated HTML file
        """
        self.logger.info(f"Processing article: {url}")
        if user_id:
            self.logger.info(f"   User ID: {user_id}")

        # Store user_id for database save
        self.current_user_id = user_id

        try:
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

            # Step 5: Save to Supabase database
            if self.event_emitter:
                await self.event_emitter.emit('save_start')

            self.logger.info("3. Saving to Supabase database...")
            article_id = self._save_to_database(metadata, ai_summary, self.current_user_id)

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
        # Check if URL points to a direct media file (video/audio)
        is_media, media_type = self.content_detector.is_direct_media_url(url)
        if is_media:
            self.logger.info(f"🎥 [DIRECT MEDIA FILE] Detected direct {media_type} file URL")
            return await self._process_direct_media_file(url, media_type, progress_callback, extract_demo_frames)

        # Check if URL is a direct YouTube video link
        youtube_match = re.match(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', url)
        if youtube_match:
            self.logger.info("🎥 [DIRECT YOUTUBE] Detected direct YouTube video URL")
            return await self._process_direct_youtube_url(url, youtube_match.group(1), extract_demo_frames)

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
            metadata.update(await self._process_video_content_async(
                content_type.video_urls, soup, url, progress_callback
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

        return metadata

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

        # Extract transcript using the generic async video processing
        self.logger.info(f"   🎥 [EXTRACTING] Transcript for Loom video...")

        # OPTIMIZATION: If we need frames, download video once and extract audio from it
        # Otherwise, use standard audio-only download path
        video_frames = []
        video_temp_path = None
        transcripts = {}
        article_text = ''

        if extract_demo_frames:
            self.logger.info("🎬 [DEMO VIDEO MODE] Downloading video once for both frames and audio...")
            try:
                # Step 1: Download full video using unified method
                import tempfile
                temp_dir = tempfile.mkdtemp(prefix="demo_video_")
                temp_template = os.path.join(temp_dir, f'video_{video_id}')

                video_temp_path = self._download_video_with_ytdlp(
                    url,
                    temp_template,
                    referer=url,
                    download_video=True  # Download full video, not just audio
                )

                if video_temp_path:
                    # Step 2: Extract audio from video using ffmpeg (reuse existing method)
                    audio_temp_path = await self._extract_audio_from_video(video_temp_path)

                    if audio_temp_path:
                        # Step 3: Transcribe the extracted audio
                        self.logger.info(f"🎵 [DEMO VIDEO MODE] Transcribing extracted audio...")
                        result = await self._transcribe_audio_with_size_check(
                            audio_temp_path,
                            media_type='video',
                            progress_callback=progress_callback
                        )

                        if result and result.get('transcript_data'):
                            transcript_data = result['transcript_data']
                            formatted_transcript = {
                                'success': True,
                                'type': 'deepgram',
                                'text': transcript_data.get('text', ''),
                                'segments': transcript_data.get('segments', []),
                                'language': transcript_data.get('language', 'en')
                            }
                            transcripts[video_id] = formatted_transcript
                            article_text = transcript_data.get('text', '')
                            self.logger.info(f"✅ [DEMO VIDEO MODE] Transcription successful")
                        else:
                            self.logger.warning(f"⚠️ [DEMO VIDEO MODE] Transcription failed")
                    else:
                        self.logger.warning(f"⚠️ [DEMO VIDEO MODE] Could not extract audio from video")

                    # Step 4: Extract frames from same video file
                    video_frames = await self._extract_and_upload_frames(video_temp_path, url)
                    self.logger.info(f"✅ [FRAME EXTRACTION] Extracted {len(video_frames)} frames")

                    # TODO: TEMPORARY - Remove cleanup to preserve video for testing
                    # Clean up temp directory
                    # try:
                    #     import shutil
                    #     shutil.rmtree(temp_dir)
                    #     self.logger.info(f"🧹 Cleaned up temp directory: {temp_dir}")
                    # except Exception as e:
                    #     self.logger.warning(f"⚠️ Failed to remove temp directory: {e}")
                    self.logger.info(f"💾 [TEMPORARY] Video file preserved at: {video_temp_path}")
                    self.logger.info(f"📂 [TEMPORARY] Temp directory preserved at: {temp_dir}")
                else:
                    self.logger.warning("⚠️ [DEMO VIDEO MODE] Could not download video, falling back to audio-only")
                    # Fall back to standard processing
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup('', 'html.parser')
                    video_data = await self._process_video_content_async(
                        video_urls, soup, url, progress_callback
                    )
                    transcripts = video_data.get('transcripts', {})
                    article_text = video_data.get('article_text', '')

            except Exception as e:
                self.logger.error(f"❌ [DEMO VIDEO MODE] Failed: {e}", exc_info=True)
                # Fall back to standard processing
                from bs4 import BeautifulSoup
                soup = BeautifulSoup('', 'html.parser')
                video_data = await self._process_video_content_async(
                    video_urls, soup, url, progress_callback
                )
                transcripts = video_data.get('transcripts', {})
                article_text = video_data.get('article_text', '')
        else:
            # Standard path: audio-only download
            from bs4 import BeautifulSoup
            soup = BeautifulSoup('', 'html.parser')
            video_data = await self._process_video_content_async(
                video_urls, soup, url, progress_callback
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

        # Emit progress
        if progress_callback:
            await progress_callback("fetch_complete", {"title": title})

        # Download the media file using yt-dlp (extracts audio for video files)
        self.logger.info(f"⬇️ [DOWNLOAD] Downloading {media_type} with yt-dlp (audio extraction)...")
        if progress_callback:
            await progress_callback("download_start", {"filename": filename})

        try:
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

            if not transcript_result:
                raise Exception("Transcription failed")

            # Extract video frames if requested (for demo videos)
            video_frames = []
            if extract_demo_frames and media_type == 'video':
                self.logger.info("🎬 [FRAME EXTRACTION] Extracting frames from demo video...")
                if progress_callback:
                    await progress_callback("extracting_frames", {"message": "Extracting video frames..."})

                try:
                    # Download full video file (not just audio) for frame extraction
                    video_temp_path = await self._download_video_for_frames(url)

                    if video_temp_path:
                        video_frames = await self._extract_and_upload_frames(video_temp_path, url)
                        self.logger.info(f"✅ [FRAME EXTRACTION] Extracted {len(video_frames)} frames")

                        # Clean up video file
                        try:
                            os.unlink(video_temp_path)
                        except Exception as e:
                            self.logger.warning(f"⚠️ Failed to remove video temp file: {e}")

                        if progress_callback:
                            await progress_callback("frames_extracted", {"frame_count": len(video_frames)})
                    else:
                        self.logger.warning("⚠️ [FRAME EXTRACTION] Could not download video for frame extraction")

                except Exception as e:
                    self.logger.error(f"❌ [FRAME EXTRACTION] Failed: {e}", exc_info=True)
                    if progress_callback:
                        await progress_callback("frame_extraction_failed", {"error": str(e)})

            # Clean up the audio temporary file
            try:
                os.unlink(temp_path)
                self.logger.info(f"🗑️ [CLEANUP] Removed temporary audio file: {temp_path}")
            except Exception as e:
                self.logger.warning(f"⚠️ [CLEANUP] Failed to remove temp file: {e}")

            # Handle case where video has no audio track
            transcripts = {}
            article_text = ''
            if transcript_result is None:
                self.logger.warning(f"⚠️ [{media_type.upper()}] No audio track found - will process without transcription")
                if progress_callback:
                    await progress_callback("no_audio_track", {"reason": "Video file has no audio track"})
            else:
                # Extract transcript data
                transcript_data = transcript_result.get('transcript_data', {})
                transcript_text = transcript_data.get('text', '')
                transcripts = {
                    'direct_file': {  # Use 'direct_file' as key to match video_id
                        'success': True,  # Mark as successful for transcript formatting
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
                'source': urlparse(url).netloc,
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

    async def _process_direct_youtube_url(self, url: str, video_id: str, extract_demo_frames: bool = False) -> Dict:
        """
        Process a direct YouTube video URL (e.g., https://www.youtube.com/watch?v=xyz)

        Args:
            url: The YouTube video URL
            video_id: Extracted YouTube video ID
            extract_demo_frames: If True, download video and extract frames

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

        # Extract transcript
        self.logger.info(f"   🎥 [EXTRACTING] YouTube transcript for video: {video_id}")
        transcript_data = self.transcript_processor.get_youtube_transcript(video_id)

        transcripts = {}
        article_text = ""

        if transcript_data and transcript_data.get('success'):
            transcripts[video_id] = transcript_data
            self.logger.info(f"      ✓ Transcript extracted ({transcript_data.get('type', 'unknown')})")

            # Extract text from transcript for article content
            if 'transcript' in transcript_data:
                article_text = ' '.join([entry['text'] for entry in transcript_data['transcript']])
                self.logger.info(f"      ✓ Extracted {len(article_text)} characters from transcript")
        else:
            error_msg = transcript_data.get('error', 'Unknown error') if transcript_data else 'Unknown error'
            self.logger.info(f"      ✗ No YouTube transcript available: {error_msg}")

            # Fallback: Try to download and transcribe video audio using DeepGram
            self.logger.info(f"      🎵 [FALLBACK] Attempting DeepGram transcription for video...")

            # Extract audio URL using yt-dlp
            audio_url = self._extract_youtube_audio_url(video_id)
            if audio_url:
                self.logger.info(f"      🎵 [FALLBACK] Transcribing audio with DeepGram...")
                transcript_data = await self._download_and_transcribe_media_async(audio_url, "video")
                if transcript_data:
                    transcripts[video_id] = transcript_data
                    self.logger.info(f"      ✓ Video transcription successful via DeepGram")

                    # Extract text from transcript
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

        # Extract video frames if requested (for demo videos)
        # For YouTube, we have native transcripts so only download video when needed for frames
        video_frames = []
        if extract_demo_frames:
            self.logger.info("🎬 [FRAME EXTRACTION] Extracting frames from YouTube video...")
            try:
                # Download full YouTube video for frame extraction
                video_temp_path = await self._download_video_for_frames(url)

                if video_temp_path:
                    video_frames = await self._extract_and_upload_frames(video_temp_path, url)
                    self.logger.info(f"✅ [FRAME EXTRACTION] Extracted {len(video_frames)} frames")

                    # Clean up video file and temp directory
                    try:
                        import shutil
                        temp_dir = os.path.dirname(video_temp_path)
                        shutil.rmtree(temp_dir)
                        self.logger.info(f"🧹 Cleaned up temp directory: {temp_dir}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to remove temp directory: {e}")
                else:
                    self.logger.warning("⚠️ [FRAME EXTRACTION] Could not download YouTube video for frame extraction")

            except Exception as e:
                self.logger.error(f"❌ [FRAME EXTRACTION] Failed: {e}", exc_info=True)

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
            'video_frames': video_frames
        }

    async def _process_video_content_async(
        self,
        video_urls: List[Dict],
        soup,
        base_url: str,
        progress_callback: Optional[Callable[[str, Dict], Awaitable[None]]] = None
    ) -> Dict:
        """
        Async version: Process content with single validated video with progress callbacks

        Args:
            video_urls: List of video URLs detected
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            progress_callback: Optional async callback for progress updates

        Returns:
            Dict with transcripts, article_text, and images
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
                                    'language': transcript_data.get('language', 'en')
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

        # Extract images from article
        images = self._extract_article_images(soup, base_url)

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
            'images': images
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

    async def _generate_summary_async(self, url: str, metadata: Dict) -> Dict:
        """
        Async wrapper for AI summary generation.

        Runs the synchronous Claude API call in a thread pool to avoid blocking
        the event loop, enabling real-time SSE streaming.
        """
        import asyncio

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

    def _call_claude_api(self, prompt: str) -> str:
        """Call Claude Code API for AI-powered analysis"""
        return self.claude_client.call_api(prompt)

    def _extract_json_from_response(self, response: str) -> Optional[Dict]:
        """Extract and parse JSON from Claude's response"""
        import re

        json_patterns = [
            (r'```json\s*(\{.*?\})\s*```', 'json code block'),
            (r'```\s*(\{.*?\})\s*```', 'generic code block'),
            (r'"""\s*json\s*(\{.*?\})\s*"""', 'triple-quoted json block'),
            (r'"""\s*(\{.*?\})\s*"""', 'triple-quoted block'),
            (r'(\{.*?\})', 'raw JSON')
        ]

        for pattern, pattern_name in json_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    json_content = match.group(1)
                    self.logger.debug(f"   🔍 [JSON] Trying {pattern_name} - found {len(json_content)} chars")
                    return json.loads(json_content)
                except json.JSONDecodeError as e:
                    self.logger.debug(f"   ❌ [JSON] {pattern_name} failed: {e}")
                    continue

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

    def _save_to_database(self, metadata: Dict, ai_summary: Dict, user_id: Optional[str] = None):
        """Save article data to Supabase database

        Args:
            metadata: Article metadata
            ai_summary: AI-generated summary
            user_id: Optional user ID for authentication (Supabase auth user)
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
                'duration_minutes': ai_summary.get('duration_minutes'),
                'word_count': ai_summary.get('word_count'),
                'topics': ai_summary.get('topics', []),
            }

            # Add embedding if generated
            if embedding:
                article_data['embedding'] = embedding

            # Try to update existing article or insert new one
            # Note: user_id is no longer on articles table (moved to article_users junction table)
            result = self.supabase.table('articles').upsert(
                article_data,
                on_conflict='url'
            ).execute()

            if result.data:
                article_id = result.data[0]['id']
                self.logger.info(f"   ✅ Saved to database (article ID: {article_id})")

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
            self.logger.error(f"   ❌ Database save failed: {e}")
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

            # Clean up any existing files matching this output template
            pattern = output_template + "*"
            existing_files = glob.glob(pattern)
            for f in existing_files:
                try:
                    os.unlink(f)
                    self.logger.info(f"      🧹 Cleaned up existing file: {f}")
                except Exception as e:
                    self.logger.warning(f"      ⚠️ Could not clean up existing file {f}: {e}")

            if download_video:
                self.logger.info(f"      🔧 [YT-DLP] Downloading full video with yt-dlp...")
                ydl_opts = {
                    'format': 'bestvideo+bestaudio/best',  # Download both streams and merge, fallback to best single file
                    'outtmpl': output_template,
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                    'no_check_certificate': True,
                    'ignoreerrors': False,
                    'merge_output_format': 'mp4',  # Merge to MP4 if separate video/audio streams
                    # No postprocessor - keep video as-is (ffmpeg will merge streams automatically)
                }
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

    def _download_and_transcribe_media(self, media_url: str, media_type: str = "audio") -> Optional[Dict]:
        """
        Download and transcribe audio/video file using DeepGram

        Args:
            media_url: URL of the audio/video file
            media_type: Type of media (audio or video)

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

            # Download media file to temp location
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name
                self.logger.info(f"   📥 [DOWNLOAD] Downloading {media_type} file...")

                response = requests.get(media_url, stream=True, timeout=60)
                response.raise_for_status()

                # Write to temp file
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)

            # Check file size (OpenAI DeepGram limit is 25MB)
            file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
            self.logger.info(f"   ✅ [DOWNLOAD] Downloaded to {temp_path}")
            self.logger.info(f"   📊 [FILE SIZE] {file_size_mb:.1f}MB")

            # If file exceeds 25MB, split into chunks
            if file_size_mb > 25:
                self.logger.info(f"   ✂️ [CHUNKING] File exceeds 25MB limit, splitting into chunks...")
                return self._transcribe_large_audio_file(temp_path, media_type)

            # Transcribe the file
            result = self.file_transcriber.transcribe_file(temp_path)
            transcript_data = result['transcript_data']
            transcript_json_file = result['output_file']

            # Format for our use - convert to same format as YouTube transcripts
            segments = transcript_data.get('segments', [])
            transcript_list = []
            for segment in segments:
                transcript_list.append({
                    'start': segment.get('start', 0),
                    'text': segment.get('text', ''),
                    'duration': segment.get('end', 0) - segment.get('start', 0)
                })

            formatted_transcript = {
                'success': True,
                'transcript': transcript_list,  # Use 'transcript' key to match YouTube format
                'text': transcript_data.get('text', ''),
                'language': transcript_data.get('language', 'unknown'),
                'type': 'deepgram_transcription',
                'source': media_type,
                'total_entries': len(transcript_list)
            }

            self.logger.info(f"   ✅ [DEEPGRAM] Transcription successful ({len(formatted_transcript['text'])} chars)")

            # Clean up temp files
            try:
                os.unlink(temp_path)  # Delete downloaded audio file
                os.unlink(transcript_json_file)  # Delete transcript JSON file
                self.logger.info(f"   🧹 Cleaned up temp files")
            except Exception as cleanup_error:
                self.logger.warning(f"   ⚠️ Could not clean up temp files: {cleanup_error}")

            return formatted_transcript

        except Exception as e:
            self.logger.warning(f"   ⚠️ [DEEPGRAM] Transcription failed: {str(e)}")
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
                'text': transcript_data.get('text', ''),
                'language': transcript_data.get('language', 'unknown'),
                'type': transcript_data.get('type', 'deepgram_transcription'),
                'source': media_type,
                'total_entries': len(transcript_list)
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
                    'type': formatted_transcript.get('type', 'deepgram')
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

    def _transcribe_large_audio_file(self, audio_path: str, media_type: str, max_duration_minutes: int = 30) -> Optional[Dict]:
        """
        Transcribe large audio files by splitting into chunks with timeout handling

        Args:
            audio_path: Path to the audio file
            media_type: Type of media (audio or video)
            max_duration_minutes: Maximum time to spend on transcription (default: 30 minutes)

        Returns:
            Transcript data dict or None if transcription fails

        Note:
            If max_duration_minutes is reached, returns partial transcript with whatever
            chunks were successfully transcribed
        """
        try:
            from pydub import AudioSegment
            import tempfile
            import os
            import time

            self.logger.info(f"   🎵 [CHUNKING] Loading audio file for splitting...")
            start_time = time.time()
            timeout_seconds = max_duration_minutes * 60

            # Load audio file
            audio = AudioSegment.from_file(audio_path)
            duration_ms = len(audio)
            duration_min = duration_ms / 1000 / 60

            self.logger.info(f"   ⏱️ [DURATION] Audio is {duration_min:.1f} minutes")
            self.logger.info(f"   ⏰ [TIMEOUT] Will process for max {max_duration_minutes} minutes")

            # Split into 20-minute chunks (1200 seconds = 1,200,000 ms)
            # At 128kbps: 20 minutes ≈ 19MB (well under 25MB DeepGram API limit)
            chunk_length_ms = 20 * 60 * 1000  # 20 minutes
            chunks = []

            for i in range(0, duration_ms, chunk_length_ms):
                chunk = audio[i:i + chunk_length_ms]
                chunks.append((i / 1000, chunk))  # Store start time in seconds

            self.logger.info(f"   ✂️ [CHUNKS] Split into {len(chunks)} chunks of ~20 minutes each")

            # Transcribe each chunk
            all_segments = []
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

                # Save chunk to temp file
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as chunk_file:
                    chunk_path = chunk_file.name
                    chunk.export(chunk_path, format='mp3')

                # Log chunk file size
                chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
                self.logger.info(f"   📊 [CHUNK {chunk_idx + 1}] File size: {chunk_size_mb:.1f}MB (sending to DeepGram API)")

                try:
                    # Transcribe this chunk
                    result = self.file_transcriber.transcribe_file(chunk_path)
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

                    all_text.append(transcript_data.get('text', ''))
                    chunks_completed += 1

                    self.logger.info(f"   ✅ [CHUNK {chunk_idx + 1}/{len(chunks)}] Complete ({len(segments)} segments)")

                    # Clean up chunk files
                    os.unlink(chunk_path)
                    os.unlink(transcript_json_file)

                except Exception as chunk_error:
                    self.logger.warning(f"   ⚠️ [CHUNK {chunk_idx + 1}/{len(chunks)}] Failed: {chunk_error}")
                    # Continue with other chunks even if one fails
                    try:
                        os.unlink(chunk_path)
                    except:
                        pass

            # Clean up original file
            os.unlink(audio_path)

            if not all_segments:
                self.logger.warning(f"   ❌ [CHUNKING] No segments transcribed successfully")
                return None

            # Combine all transcripts
            is_partial = chunks_completed < len(chunks)
            formatted_transcript = {
                'success': True,
                'transcript': all_segments,
                'text': ' '.join(all_text),
                'language': 'unknown',
                'type': 'deepgram_transcription_chunked' + ('_partial' if is_partial else ''),
                'source': media_type,
                'total_entries': len(all_segments),
                'chunks_processed': chunks_completed,
                'total_chunks': len(chunks),
                'is_partial': is_partial
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

                    all_text.append(transcript_data.get('text', ''))
                    chunks_completed += 1

                    self.logger.info(f"   ✅ [CHUNK {chunk_idx + 1}/{len(chunks)}] Complete ({len(segments)} segments)")

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
                'text': ' '.join(all_text),
                'language': 'unknown',
                'type': 'deepgram_transcription_chunked' + ('_partial' if is_partial else ''),
                'source': media_type,
                'total_entries': len(all_segments),
                'chunks_processed': chunks_completed,
                'total_chunks': len(chunks),
                'is_partial': is_partial
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
        """Format transcript for display (grouped into 30+ second sections)"""
        if not transcript_data or not transcript_data.get('success'):
            return ""

        # Handle both YouTube API format ('transcript') and DeepGram format ('segments')
        transcript = transcript_data.get('transcript', transcript_data.get('segments', []))
        formatted_sections = []

        # Group transcript entries into 30+ second sections
        current_section_start = None
        current_section_text = []
        min_section_duration = 30  # minimum 30 seconds per section

        for entry in transcript:
            start_time = entry.get('start', 0)
            text = entry.get('text', '').strip()

            if not text:
                continue

            # Start a new section if this is the first entry
            if current_section_start is None:
                current_section_start = start_time
                current_section_text = [text]
            else:
                # Check if we should start a new section
                section_duration = start_time - current_section_start

                # Start new section if: we've exceeded min duration AND at sentence boundary
                is_sentence_boundary = current_section_text[-1].rstrip().endswith(('.', '!', '?'))

                if section_duration >= min_section_duration and is_sentence_boundary:
                    # Save current section
                    minutes = int(current_section_start // 60)
                    seconds = int(current_section_start % 60)
                    timestamp = f"[{minutes}:{seconds:02d}]"
                    section_text = " ".join(current_section_text)
                    formatted_sections.append(f"{timestamp} {section_text}")

                    # Start new section
                    current_section_start = start_time
                    current_section_text = [text]
                else:
                    # Continue current section
                    current_section_text.append(text)

        # Add the final section
        if current_section_start is not None and current_section_text:
            minutes = int(current_section_start // 60)
            seconds = int(current_section_start % 60)
            timestamp = f"[{minutes}:{seconds:02d}]"
            section_text = " ".join(current_section_text)
            formatted_sections.append(f"{timestamp} {section_text}")

        return "\n\n".join(formatted_sections)

    def _convert_timestamp_to_seconds(self, timestamp: str) -> int:
        """Convert MM:SS or H:MM:SS timestamp to seconds"""
        parts = timestamp.split(':')
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # H:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0

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

    async def _extract_audio_from_video(self, video_path: str) -> Optional[str]:
        """
        Extract audio from video file using ffmpeg

        Args:
            video_path: Path to video file

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

            stdout, stderr = await process.communicate()

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
            # Clean up any old video_frames_* temp directories first
            temp_base = tempfile.gettempdir()
            old_temp_dirs = glob.glob(os.path.join(temp_base, "video_frames_*"))
            for old_dir in old_temp_dirs:
                try:
                    import shutil
                    shutil.rmtree(old_dir)
                    self.logger.info(f"🧹 Cleaned up old temp directory: {old_dir}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not clean up old temp directory {old_dir}: {e}")

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