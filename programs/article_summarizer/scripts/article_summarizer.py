#!/usr/bin/env python3
"""
Article Summarizer - Database-Only Version

Processes articles and saves structured data to Supabase database.
No static HTML files are generated - all rendering is done by the Next.js web app.

Features:
- Content type detection (video/audio/text-only)
- Authentication handling for paywalled content
- AI-powered content analysis using Claude
- Saves structured data (summaries, insights, transcripts) to Supabase
- Returns article ID for viewing in web app

Usage:
    python3 article_summarizer.py "https://example.com/article"

View results:
    http://localhost:3000/article/{id}
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from supabase import create_client, Client

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base import BaseProcessor
from common.config import Config
from common.content_detector import ContentTypeDetector, ContentType
from common.authentication import AuthenticationManager
from common.claude_client import ClaudeClient
from processors.transcript_processor import TranscriptProcessor
from processors.file_transcriber import FileTranscriber


class ArticleSummarizer(BaseProcessor):
    """
    Main article summarizer that handles all content types:
    - Embedded video content (with transcripts)
    - Embedded audio content (with transcripts)
    - Text-only articles
    """

    def __init__(self):
        super().__init__("ArticleSummarizer")
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

        # Initialize Supabase client with anon key
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
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
                missing.append('SUPABASE_ANON_KEY')
            self.logger.warning(f"⚠️ Supabase credentials not found - database insertion will be skipped (missing: {', '.join(missing)})")

    def process_article(self, url: str) -> str:
        """
        Main processing pipeline for any article type

        Args:
            url: URL of the article to process

        Returns:
            Path to generated HTML file
        """
        self.logger.info(f"Processing article: {url}")

        try:
            # Step 1: Extract metadata and detect content type
            self.logger.info("1. Extracting metadata...")
            metadata = self._extract_metadata(url)
            self.logger.info(f"   Title: {metadata['title']}")

            # Step 2: Generate filename
            filename = self._sanitize_filename(metadata['title']) + '.html'
            self.logger.info(f"   Filename: {filename}")

            # Step 3: AI-powered content analysis
            self.logger.info("2. Analyzing content with AI...")
            ai_summary = self._generate_summary_with_ai(url, metadata)

            # Step 4: Save to Supabase database
            self.logger.info("3. Saving to Supabase database...")
            article_id = self._save_to_database(metadata, ai_summary)

            self.logger.info(f"✅ Processing complete! View at: http://localhost:3000/article/{article_id}")
            return article_id

        except Exception as e:
            self.logger.error(f"❌ Processing failed: {e}")
            raise

    def _extract_metadata(self, url: str) -> Dict:
        """
        Extract metadata and detect content type

        Args:
            url: URL to analyze

        Returns:
            Dictionary containing metadata and content analysis
        """
        # Get page content
        response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
        soup = self._get_soup(response.content)

        # Check if we should use browser fetch for this URL/response
        should_use_browser = self.auth_manager.should_use_browser_fetch(url, response)

        if should_use_browser:
            self.logger.info("🌐 [BROWSER FALLBACK] Anti-bot measures detected, switching to browser fetch...")
            browser_success, html_content, browser_message = self.auth_manager.fetch_with_browser(url)

            if browser_success:
                soup = self._get_soup(html_content)
                self.logger.info("✅ [BROWSER FALLBACK] Successfully retrieved content via browser")
            else:
                self.logger.warning(f"⚠️ [BROWSER FALLBACK] Browser fetch failed: {browser_message}")
                self.logger.warning("⚠️ [BROWSER FALLBACK] Continuing with standard request content...")

        # Detect platform and handle authentication
        platform = self.auth_manager.detect_platform(url)
        auth_required, auth_reason = self.auth_manager.check_authentication_required(url, platform)

        if auth_required:
            auth_success, auth_message = self.auth_manager.authenticate_if_needed(url, platform)
            if not auth_success:
                self.logger.warning(f"⚠️ Authentication failed: {auth_message}")
            else:
                # Re-fetch content after authentication
                response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
                soup = self._get_soup(response.content)

        # Detect content type
        content_type = self.content_detector.detect_content_type(soup, url)

        # Extract basic metadata
        title = self._extract_title(soup, url)

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
            metadata.update(self._process_video_content(content_type.video_urls, soup, url))
        elif content_type.has_embedded_audio:
            metadata.update(self._process_audio_content(content_type.audio_urls, soup, url))
        else:
            metadata.update(self._process_text_content(soup, url))

        return metadata

    def _process_video_content(self, video_urls: List[Dict], soup, base_url: str) -> Dict:
        """Process content with single validated video"""

        # Should only receive 1 validated video from detection logic
        if not video_urls:
            self.logger.info("   No validated videos to process")
            return {'media_info': {'youtube_urls': []}, 'transcripts': {}}

        if len(video_urls) > 1:
            self.logger.warning(f"   ⚠️ [UNEXPECTED] Received {len(video_urls)} videos, expected 1. Using first video only.")

        # Process only the first (and should be only) video
        video = video_urls[0]
        video_id = video.get('video_id', 'N/A')
        score = video.get('relevance_score', 'N/A')
        context = video.get('context', 'unknown')

        self.logger.info(f"   Processing single validated video: ID={video_id} | Score={score} | Context={context}")

        # Extract transcript for the single video
        transcripts = {}
        self.logger.info(f"      🎥 [EXTRACTING] Video: {video_id}")

        transcript_data = self.transcript_processor.get_youtube_transcript(video_id)
        if transcript_data and transcript_data.get('success'):
            transcripts[video_id] = transcript_data
            self.logger.info(f"      ✓ Transcript extracted ({transcript_data.get('type', 'unknown')})")
        else:
            error_msg = transcript_data.get('error', 'Unknown error') if transcript_data else 'Unknown error'
            self.logger.info(f"      ✗ No YouTube transcript available: {error_msg}")

            # Fallback: Try to download and transcribe video audio using Whisper
            # Construct YouTube audio URL (yt-dlp would normally handle this, but we'll try direct URL)
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            self.logger.info(f"      🎵 [FALLBACK] Attempting Whisper transcription for video...")

            # Note: This requires yt-dlp or youtube-dl to extract audio URL
            # For now, we'll skip auto-download and just log the attempt
            # Future enhancement: integrate yt-dlp to extract audio stream URL
            self.logger.info(f"      ⚠️ [FALLBACK] Video audio transcription requires yt-dlp integration (not yet implemented)")
            # transcript_data = self._download_and_transcribe_media(audio_url, "video")
            # if transcript_data:
            #     transcripts[video_id] = transcript_data
            #     self.logger.info(f"      ✓ Video transcription successful via Whisper")

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

        return {
            'media_info': {'youtube_urls': video_urls},
            'transcripts': transcripts,
            'article_text': article_text or 'Content not available',
            'images': images
        }

    def _process_audio_content(self, audio_urls: List[Dict], soup, base_url: str) -> Dict:
        """Process content with embedded audio"""
        self.logger.info("   Found embedded audio content...")

        # Try to transcribe audio if available
        transcripts = {}
        if audio_urls:
            for idx, audio in enumerate(audio_urls):
                audio_url = audio.get('url')
                if audio_url:
                    self.logger.info(f"   🎵 [AUDIO {idx+1}] Attempting transcription...")
                    transcript_data = self._download_and_transcribe_media(audio_url, "audio")
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

    def _generate_summary_with_ai(self, url: str, metadata: Dict) -> Dict:
        """Generate AI summary based on content type"""
        content_type = metadata['content_type']

        # Build context based on content type
        if content_type.has_embedded_video:
            media_context = self._build_video_context(metadata)
        elif content_type.has_embedded_audio:
            media_context = self._build_audio_context(metadata)
        else:
            media_context = self._build_text_context(metadata)

        # Generate prompt
        prompt = self._build_analysis_prompt(url, metadata, media_context)

        # Call Claude API
        response = self._call_claude_api(prompt)

        # Parse response
        parsed_json = self._extract_json_from_response(response)

        if parsed_json:
            # Ensure summary is properly formatted as HTML
            if 'summary' in parsed_json:
                summary = parsed_json['summary']
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

    def _build_video_context(self, metadata: Dict) -> str:
        """Build context string for video content"""
        video_urls = metadata['media_info']['youtube_urls']
        transcripts = metadata.get('transcripts', {})

        # Check if we have any successful transcripts
        has_transcript_data = False
        transcript_content = ""

        if transcripts:
            for video_id, transcript_data in transcripts.items():
                if transcript_data.get('success'):
                    formatted_transcript = self._format_transcript_for_analysis(transcript_data)
                    if formatted_transcript:
                        has_transcript_data = True
                        transcript_content += f"""

VIDEO TRANSCRIPT for {video_id} ({transcript_data.get('type', 'unknown')} transcript):
{formatted_transcript[:Config.MAX_TRANSCRIPT_CHARS]}{'...' if len(formatted_transcript) > Config.MAX_TRANSCRIPT_CHARS else ''}
"""

        # Get article text content
        article_text = metadata.get('article_text', 'Content not available')

        # Build context based on whether we have transcript data
        if has_transcript_data:
            context = f"""
IMPORTANT: This article contains video content. Video URLs found: {video_urls}
Please focus on extracting video timestamps with the following format:
- Use MM:SS format for timestamps (e.g., "5:23", "12:45", "1:02:30")
- Provide detailed descriptions of what happens at each timestamp
- Aim for 5-8 key timestamps that represent the most valuable content
- Include timestamps for: key insights, important discussions, actionable advice, demonstrations
{transcript_content}

ARTICLE TEXT CONTENT:
{article_text}

Please analyze both the article text and the video transcript to provide comprehensive insights.
"""
        else:
            context = f"""
IMPORTANT: This article contains video content. Video URLs found: {video_urls}
Note: No video transcripts are available, so please focus on the article content itself.
DO NOT include any timestamps or time-based references in your response.
- Focus on key insights and takeaways mentioned in the article text
- Extract actionable advice from the article content
- Identify main themes and discussion points referenced in the article
- Base your analysis only on the article text, not on video content

ARTICLE TEXT CONTENT:
{article_text}
"""

        return context

    def _build_audio_context(self, metadata: Dict) -> str:
        """Build context string for audio content"""
        audio_urls = metadata['media_info']['audio_urls']
        transcripts = metadata.get('transcripts', {})

        # Check if we have any successful transcripts
        has_transcript_data = False
        transcript_content = ""

        if transcripts:
            for audio_id, transcript_data in transcripts.items():
                if transcript_data.get('success'):
                    formatted_transcript = self._format_transcript_for_analysis(transcript_data)
                    if formatted_transcript:
                        has_transcript_data = True
                        transcript_content += f"""

AUDIO TRANSCRIPT for {audio_id} ({transcript_data.get('type', 'unknown')} transcript):
{formatted_transcript[:Config.MAX_TRANSCRIPT_CHARS]}{'...' if len(formatted_transcript) > Config.MAX_TRANSCRIPT_CHARS else ''}
"""

        # Get article text content
        article_text = metadata.get('article_text', 'Content not available')

        # Build context based on whether we have transcript data
        if has_transcript_data:
            context = f"""
IMPORTANT: This article contains audio/podcast content. Audio URLs found: {audio_urls}
Please focus on extracting audio timestamps with the following format:
- Use MM:SS format for timestamps (e.g., "5:23", "12:45", "1:02:30")
- Provide detailed descriptions of what is discussed at each timestamp
- Aim for 5-8 key timestamps that represent the most valuable content
- Include timestamps for: key insights, important discussions, actionable advice, main themes
Audio Platform: {audio_urls[0]['platform'] if audio_urls else 'unknown'}
{transcript_content}

ARTICLE TEXT CONTENT:
{article_text}

Please analyze both the article text and the audio transcript to provide comprehensive insights.
"""
        else:
            context = f"""
IMPORTANT: This article contains audio/podcast content. Audio URLs found: {audio_urls}
Note: No audio transcripts are available, so please focus on the article content itself.
DO NOT include any timestamps or time-based references in your response.
- Focus on key insights and takeaways mentioned in the article text
- Extract actionable advice from the article content
- Identify main themes and discussion points referenced in the article
- Note the participants/speakers if mentioned in the content
- Base your analysis only on the article text, not on audio content
Audio Platform: {audio_urls[0]['platform'] if audio_urls else 'unknown'}

ARTICLE TEXT CONTENT:
{article_text}

Please analyze the article text to provide comprehensive insights about the audio content.
"""

        return context

    def _build_text_context(self, metadata: Dict) -> str:
        """Build context string for text-only content"""
        article_text = metadata.get('article_text', 'Content not available')

        return f"""
IMPORTANT: This is a TEXT-ONLY article with no video or audio content.
For text-only articles, please focus on:
- Extracting key insights from the written content
- Identifying main themes and arguments
- Summarizing actionable takeaways
- Highlighting important quotes or data points
- Structuring the content logically with clear headings
- NO timestamps should be included (since there's no media)

Article text content: {article_text}
"""

    def _build_analysis_prompt(self, url: str, metadata: Dict, media_context: str) -> str:
        """Build the complete analysis prompt"""
        content_type = metadata['content_type']

        # Determine media type for prompt
        if content_type.has_embedded_video:
            media_type_indicator = "video"
            jump_function = "jumpToTime"
        elif content_type.has_embedded_audio:
            media_type_indicator = "audio"
            jump_function = "jumpToAudioTime"
        else:
            media_type_indicator = "content"
            jump_function = "jumpToTime"

        return f"""
Analyze this article: {url}

Create a comprehensive summary with the following structure:
1. Write a clear, structured summary (2-4 paragraphs) in HTML format as paragraphs (NOT bullets)
2. Extract 8-12 key insights combining main points, insights, and actionable takeaways
3. If video/audio content exists, identify specific timestamps with detailed descriptions

{media_context}

Article metadata: {json.dumps(self._create_metadata_for_prompt(metadata), indent=2)}

Return your response in this JSON format:
{{
    "summary": "HTML formatted summary in paragraph form (2-4 paragraphs, NOT bullets). Use <p> tags for paragraphs.",
    "key_insights": [
        {{"insight": "Key insight, main point, or actionable takeaway", "timestamp_seconds": 300, "time_formatted": "5:00"}},
        {{"insight": "Another insight without timestamp", "timestamp_seconds": null, "time_formatted": null}}
    ],
    "quotes": [
        {{"quote": "Exact quote text", "speaker": "Speaker name", "timestamp_seconds": 120, "time_formatted": "2:00", "context": "Context for the quote"}}
    ],
    "duration_minutes": 45,
    "word_count": 5000,
    "topics": ["AI", "Product", "Engineering"]
}}

CRITICAL TIMESTAMP RULES:
- Each timestamp section should cover AT LEAST 30 SECONDS of continuous content
- Each description should include COMPLETE SENTENCES and full thoughts - never break mid-sentence
- Group related ideas that span 30-60 seconds into a single timestamp entry with comprehensive description
- Provide detailed summaries that capture the full context of what's discussed in that 30+ second window
- Use null for timestamp_seconds and time_formatted if you cannot find the EXACT content in the provided transcript
- NEVER guess or estimate timestamps - if you can't find it in the transcript, use null
- For quotes: search the transcript for the exact quote text and use that timestamp
- For insights: provide comprehensive descriptions that summarize the complete topic discussed in that 30+ second section
- Only include timestamps for content you can find in the provided transcript
- If transcript is truncated, only use timestamps from the visible portion
- key_insights should be 8-12 items combining key learnings, main points, and actionable takeaways
- Each insight with a timestamp should describe the complete topic/discussion in that time window, not just a single point
- quotes should be memorable/important quotes with exact speaker attribution and context
"""

    def _call_claude_api(self, prompt: str) -> str:
        """Call Claude Code API for AI-powered analysis"""
        return self.claude_client.call_api(prompt)

    def _extract_json_from_response(self, response: str) -> Optional[Dict]:
        """Extract and parse JSON from Claude's response"""
        import re

        json_patterns = [
            (r'```json\s*(\{.*?\})\s*```', 'json code block'),
            (r'```\s*(\{.*?\})\s*```', 'generic code block'),
            (r'(\{.*?\})', 'raw JSON')
        ]

        for pattern, pattern_name in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
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

    def _save_to_database(self, metadata: Dict, ai_summary: Dict):
        """Save article data to Supabase database"""
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

            # Get video ID if available
            video_id = None
            if content_type.has_embedded_video and metadata.get('media_info', {}).get('youtube_urls'):
                video_id = metadata['media_info']['youtube_urls'][0].get('video_id')

            # Get audio URL if available
            audio_url = None
            if content_type.has_embedded_audio and metadata.get('media_info', {}).get('audio_urls'):
                audio_url = metadata['media_info']['audio_urls'][0].get('url')

            # Determine content source
            if content_type.has_embedded_video and content_type.has_embedded_audio:
                content_source = 'mixed'
            elif content_type.has_embedded_video:
                content_source = 'video'
            elif content_type.has_embedded_audio:
                content_source = 'audio'
            else:
                content_source = 'article'

            # Build article record
            article_data = {
                'title': metadata['title'],
                'url': metadata['url'],
                'summary_text': ai_summary.get('summary', ''),
                'transcript_text': transcript_text,
                'original_article_text': metadata.get('article_text'),
                'content_source': content_source,
                'video_id': video_id,
                'audio_url': audio_url,
                'platform': metadata.get('platform'),
                'tags': [],

                # Structured data
                'key_insights': ai_summary.get('key_insights', []),
                'quotes': ai_summary.get('quotes', []),
                'images': metadata.get('images', []),

                # Metadata
                'duration_minutes': ai_summary.get('duration_minutes'),
                'word_count': ai_summary.get('word_count'),
                'topics': ai_summary.get('topics', []),
            }

            # Try to update existing article or insert new one
            result = self.supabase.table('articles').upsert(
                article_data,
                on_conflict='url'
            ).execute()

            if result.data:
                article_id = result.data[0]['id']
                self.logger.info(f"   ✅ Saved to database (article ID: {article_id})")
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
        # Try multiple selectors
        title_selectors = [
            'h1', 'title',
            '.entry-title', '.post-title', '.article-title',
            '[data-testid="post-title"]'
        ]

        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)

        # Fallback to URL
        return f"Article from {self._extract_domain(url)}"

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        return urlparse(url).netloc

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename"""
        import re
        # Replace em dashes and en dashes with regular hyphens
        sanitized = title.replace('–', '-').replace('—', '-').replace('−', '-')
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)
        # Replace spaces and multiple spaces with underscores
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Remove any remaining problematic Unicode characters and keep only ASCII
        sanitized = ''.join(char if ord(char) < 128 else '_' for char in sanitized)
        # Clean up multiple underscores
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        # Limit length
        return sanitized[:100] if len(sanitized) > 100 else sanitized

    def _download_and_transcribe_media(self, media_url: str, media_type: str = "audio") -> Optional[Dict]:
        """
        Download and transcribe audio/video file using Whisper

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

            self.logger.info(f"   🎵 [WHISPER] Attempting to transcribe {media_type} from URL...")

            # Download media file to temp location
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name
                self.logger.info(f"   📥 [DOWNLOAD] Downloading {media_type} file...")

                response = requests.get(media_url, stream=True, timeout=60)
                response.raise_for_status()

                # Write to temp file
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)

            self.logger.info(f"   ✅ [DOWNLOAD] Downloaded to {temp_path}")

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
                'type': 'whisper_transcription',
                'source': media_type,
                'total_entries': len(transcript_list)
            }

            self.logger.info(f"   ✅ [WHISPER] Transcription successful ({len(formatted_transcript['text'])} chars)")

            # Clean up temp files
            import os
            try:
                os.unlink(temp_path)  # Delete downloaded audio file
                os.unlink(transcript_json_file)  # Delete transcript JSON file
                self.logger.info(f"   🧹 Cleaned up temp files")
            except Exception as cleanup_error:
                self.logger.warning(f"   ⚠️ Could not clean up temp files: {cleanup_error}")

            return formatted_transcript

        except Exception as e:
            self.logger.warning(f"   ⚠️ [WHISPER] Transcription failed: {str(e)}")
            return None

    def _extract_article_text_content(self, soup) -> str:
        """Extract main article text content"""
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
                # Remove script and style elements
                for script in element(["script", "style"]):
                    script.decompose()
                return element.get_text(strip=True)

        # Fallback to body
        body = soup.find('body')
        if body:
            for script in body(["script", "style"]):
                script.decompose()
            return body.get_text(strip=True)

        return ""

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

    def _format_transcript_for_analysis(self, transcript_data: Dict) -> str:
        """Format transcript for AI analysis (line-by-line for Claude)"""
        if not transcript_data or not transcript_data.get('success'):
            return ""

        transcript = transcript_data.get('transcript', [])
        formatted_text = []

        for entry in transcript:
            start_time = entry.get('start', 0)
            text = entry.get('text', '').strip()

            # Convert seconds to MM:SS format
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"{minutes}:{seconds:02d}"

            if text:
                formatted_text.append(f"[{timestamp}] {text}")

        return "\n".join(formatted_text)

    def _format_transcript_for_display(self, transcript_data: Dict) -> str:
        """Format transcript for display (grouped into 30+ second sections)"""
        if not transcript_data or not transcript_data.get('success'):
            return ""

        transcript = transcript_data.get('transcript', [])
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

    def _create_metadata_for_prompt(self, metadata: Dict) -> Dict:
        """Create simplified metadata for AI prompt"""
        content_type = metadata['content_type']

        return {
            'title': metadata['title'],
            'url': metadata['url'],
            'platform': metadata['platform'],
            'has_video': content_type.has_embedded_video,
            'has_audio': content_type.has_embedded_audio,
            'is_text_only': content_type.is_text_only,
            'extracted_at': metadata['extracted_at']
        }

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



def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python3 article_summarizer.py <url>")
        sys.exit(1)

    url = sys.argv[1]

    try:
        summarizer = ArticleSummarizer()
        article_id = summarizer.process_article(url)
        print(f"Success! Article ID: {article_id}")
        print(f"View at: http://localhost:3000/article/{article_id}")

    except Exception as e:
        print(f"Error processing article: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()