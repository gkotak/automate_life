#!/usr/bin/env python3
"""
Article Summarizer

Refactored from video_article_summarizer.py to provide cleaner separation of concerns:
- Content type detection (video/audio/text-only)
- Authentication handling
- AI-powered content analysis
- HTML generation

Usage:
    python3 article_summarizer.py "https://example.com/article"
"""

import sys
import json
import subprocess
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
from processors.transcript_processor import TranscriptProcessor


class ArticleSummarizer(BaseProcessor):
    """
    Main article summarizer that handles all content types:
    - Embedded video content (with transcripts)
    - Embedded audio content (with transcripts)
    - Text-only articles
    """

    def __init__(self):
        super().__init__("ArticleSummarizer")
        self.content_detector = ContentTypeDetector()
        self.auth_manager = AuthenticationManager(self.base_dir, self.session)
        self.transcript_processor = TranscriptProcessor(self.base_dir, self.session)
        self.claude_cmd = Config.find_claude_cli()
        self.html_dir = self.output_dir / "article_summaries"

        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')  # Use service key for server-side operations
        self.supabase: Optional[Client] = None

        if supabase_url and supabase_key:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                self.logger.info("✅ Supabase client initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to initialize Supabase: {e}")
        else:
            self.logger.warning("⚠️ Supabase credentials not found - database insertion will be skipped")

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

            # Step 4: Generate HTML
            self.logger.info("3. Generating HTML...")
            html_content = self._generate_html_content(metadata, ai_summary)

            # Step 5: Save file
            output_file = self.output_dir / "article_summaries" / filename
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.logger.info(f"   Created: {output_file}")

            # Step 6: Save to Supabase database
            self.logger.info("4. Saving to Supabase database...")
            self._save_to_database(metadata, ai_summary, html_content)

            # Step 7: Update index
            self.logger.info("5. Updating index...")
            self._update_index_file(filename, metadata, ai_summary)

            # Step 8: Commit to git
            self.logger.info("6. Committing to git...")
            self._commit_to_git(filename)

            self.logger.info(f"✅ Processing complete: {filename}")
            return str(output_file)

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
            metadata.update(self._process_video_content(content_type.video_urls, soup))
        elif content_type.has_embedded_audio:
            metadata.update(self._process_audio_content(content_type.audio_urls, soup))
        else:
            metadata.update(self._process_text_content(soup))

        return metadata

    def _process_video_content(self, video_urls: List[Dict], soup) -> Dict:
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
            self.logger.info(f"      ✗ No transcript available: {transcript_data.get('error', 'Unknown error')}")

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

        return {
            'media_info': {'youtube_urls': video_urls},
            'transcripts': transcripts,
            'article_text': article_text or 'Content not available'
        }

    def _process_audio_content(self, audio_urls: List[Dict], soup) -> Dict:
        """Process content with embedded audio"""
        self.logger.info("   Found embedded audio content...")

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

        # For now, just store audio metadata
        # Future: Add audio transcript extraction
        return {
            'media_info': {'audio_urls': audio_urls},
            'article_text': article_text or 'Content not available'
        }

    def _process_text_content(self, soup) -> Dict:
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

        return {
            'article_text': article_text or 'Content not available'
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
        article_text = metadata.get('article_text', 'Content not available')

        return f"""
IMPORTANT: This article contains audio/podcast content. Audio URLs found: {audio_urls}
This appears to be a podcast episode. Please:
- Identify key discussion points and insights from the conversation
- Extract actionable advice or key takeaways
- Note the participants/speakers if mentioned in the content
- Focus on the most valuable content and main themes
- DO NOT include any timestamps or time-based references since no transcript is available
Audio Platform: {audio_urls[0]['platform'] if audio_urls else 'unknown'}

ARTICLE TEXT CONTENT:
{article_text}

Please analyze the article text to provide comprehensive insights about the audio content.
"""

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
1. Write a clear, structured summary (max 1000 words) in HTML format with embedded timestamps for each major subsection
2. Extract 5-8 key insights as bullet points
3. If video/audio content exists, identify specific timestamps with detailed descriptions

{media_context}

Article metadata: {json.dumps(self._create_metadata_for_prompt(metadata), indent=2)}

Return your response in this JSON format:
{{
    "summary": "HTML formatted summary content (no timestamps in summary if no transcript data)",
    "key_insights": [
        {{"insight": "insight text", "timestamp_seconds": 300, "time_formatted": "5:00"}},
        {{"insight": "insight text without timestamp", "timestamp_seconds": null, "time_formatted": null}}
    ],
    "main_points": [
        {{"point": "Main point text", "details": "Optional additional details or explanation"}}
    ],
    "quotes": [
        {{"quote": "Exact quote text", "speaker": "Speaker name", "timestamp_seconds": 120, "context": "Context for the quote"}}
    ],
    "takeaways": ["Takeaway 1", "Takeaway 2", "Takeaway 3"],
    "duration_minutes": 45,
    "word_count": 5000,
    "topics": ["AI", "Product", "Engineering"],
    "sentiment": "positive",
    "complexity_level": "intermediate"
}}

CRITICAL:
- Use null for timestamp_seconds and time_formatted if no transcript match exists
- Only include timestamps for content you can find in the provided transcript
- Include ALL insights (with or without timestamps) but NEVER guess timestamps
- main_points should be 5-8 key points from the content
- quotes should be memorable/important quotes with speaker attribution
- takeaways should be 3-5 actionable takeaways
- If transcript is truncated, only use timestamps from the visible portion
"""

    def _call_claude_api(self, prompt: str) -> str:
        """Call Claude Code API for AI-powered analysis"""
        try:
            # Log prompt details for debugging
            prompt_length = len(prompt)
            prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
            self.logger.info(f"   🤖 [CLAUDE API] Sending prompt ({prompt_length} chars)")
            self.logger.debug(f"   📝 [PROMPT PREVIEW] {prompt_preview}")

            # Save full prompt to debug file for inspection
            debug_file = self.base_dir / "programs" / "article_summarizer" / "logs" / "debug_prompt.txt"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            self.logger.info(f"   💾 [DEBUG] Full prompt saved to: {debug_file}")

            # Use shell redirection with temp file for better handling of large prompts
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
                tmp.write(prompt)
                tmp_path = tmp.name

            try:
                # Use shell=True with input redirection
                cmd = f'{self.claude_cmd} --print --output-format text < "{tmp_path}"'
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=300,
                    cwd=self.base_dir
                )
            finally:
                # Clean up temp file
                import os
                try:
                    os.unlink(tmp_path)
                except:
                    pass

            # Save response for debugging (always, even if empty)
            response_file = self.base_dir / "programs" / "article_summarizer" / "logs" / "debug_response.txt"
            stderr_file = self.base_dir / "programs" / "article_summarizer" / "logs" / "debug_stderr.txt"

            response = result.stdout.strip()
            stderr = result.stderr.strip()

            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(f"=== CLAUDE RESPONSE ({len(response)} chars) ===\n")
                f.write(response)
                f.write(f"\n=== END RESPONSE ===\n")

            with open(stderr_file, 'w', encoding='utf-8') as f:
                f.write(f"=== STDERR (return code: {result.returncode}) ===\n")
                f.write(stderr)
                f.write(f"\n=== END STDERR ===\n")

            self.logger.info(f"   💾 [DEBUG] Response saved to: {response_file}")
            self.logger.info(f"   💾 [DEBUG] Stderr saved to: {stderr_file}")

            if result.returncode != 0:
                self.logger.error(f"   ❌ Claude API failed with return code {result.returncode}")
                self.logger.error(f"   ❌ Stderr: {stderr[:500]}")
                return f"Error calling Claude API: {stderr}"

            if not response:
                self.logger.warning(f"   ⚠️ Claude API returned empty response (stderr: {stderr[:200]})")

            return response

        except subprocess.TimeoutExpired:
            self.logger.error("   ❌ Claude API call timed out after 120 seconds")
            return f"Claude API call timed out after 120 seconds"
        except Exception as e:
            self.logger.error(f"   ❌ Exception in Claude API call: {str(e)}")
            return f"Error in Claude API call: {str(e)}"

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

    def _generate_html_content(self, metadata: Dict, ai_summary: Dict) -> str:
        """Generate the final HTML content"""
        template = self._load_template()

        # Prepare template variables
        template_vars = self._prepare_template_variables(metadata, ai_summary)

        # Replace placeholders in template
        html_content = template
        for key, value in template_vars.items():
            placeholder = f"{{{{{key}}}}}"
            html_content = html_content.replace(placeholder, str(value))

        return html_content

    def _prepare_template_variables(self, metadata: Dict, ai_summary: Dict) -> Dict:
        """Prepare variables for HTML template"""
        content_type = metadata['content_type']

        return {
            'TITLE': metadata['title'],
            'URL': metadata['url'],
            'DOMAIN': self._extract_domain(metadata['url']),
            'EXTRACTED_AT': datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            'HAS_VIDEO': 'Yes' if content_type.has_embedded_video else 'No',
            'HAS_AUDIO': 'Yes' if content_type.has_embedded_audio else 'No',
            'SUMMARY_CONTENT': ai_summary.get('summary', 'No summary available'),
            'INSIGHTS_SECTION': self._format_insights_section(ai_summary.get('key_insights', [])),
            'MEDIA_EMBED_SECTION': self._generate_media_embed_html(metadata),
            'TIMESTAMPS_SECTION': self._format_media_timestamps(ai_summary.get('media_timestamps', [])),
            'SUMMARY_SECTIONS': '',  # Additional summary sections placeholder
            'GENERATION_DATE': datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        }

    def _format_insights_section(self, insights: List[Dict]) -> str:
        """Format key insights as HTML section"""
        if not insights:
            return ""

        html = '''
    <div class="summary-section">
        <h2>🔍 Key Insights</h2>
        <ul>'''
        for insight in insights:
            html += f"<li>{insight.get('insight', '')}</li>"
        html += '''
        </ul>
    </div>'''
        return html

    def _format_media_timestamps(self, timestamps: List[Dict]) -> str:
        """Format media timestamps as HTML"""
        if not timestamps:
            return ""

        html = '<div class="timestamps-section"><h3>🕐 Key Timestamps</h3><ul>'
        for ts in timestamps:
            time = ts.get('time', '')
            description = ts.get('description', '')
            media_type = ts.get('type', 'content')

            if time:
                # Convert to seconds for JavaScript
                seconds = self._convert_timestamp_to_seconds(time)
                click_handler = f"jumpToTime({seconds})" if media_type == "video" else f"jumpToAudioTime({seconds})"
                html += f'<li><span class="timestamp" onclick="{click_handler}" title="Jump to {time}">⏰ {time}</span> {description}</li>'
            else:
                html += f'<li>{description}</li>'

        html += '</ul></div>'
        return html

    def _generate_media_embed_html(self, metadata: Dict) -> str:
        """Generate media embed HTML based on content type"""
        content_type = metadata['content_type']

        if content_type.has_embedded_video:
            return self._generate_video_embed_html(metadata)
        elif content_type.has_embedded_audio:
            return self._generate_audio_embed_html(metadata)
        else:
            return ""

    def _generate_video_embed_html(self, metadata: Dict) -> str:
        """Generate video embed HTML"""
        video_urls = metadata['media_info']['youtube_urls']
        if not video_urls:
            return ""

        video_data = video_urls[0]  # Use first video
        video_id = video_data['video_id']

        return f'''
<div class="video-container">
    <h2>🎥 Watch the Video</h2>
    <div class="speed-notice">
        ⚡ Video automatically plays at 2x speed for efficient viewing. You can adjust speed in player controls.
    </div>
    <div class="video-embed">
        <iframe
            src="https://www.youtube.com/embed/{video_id}?enablejsapi=1&playsinline=1"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen>
        </iframe>
    </div>
</div>'''

    def _generate_audio_embed_html(self, metadata: Dict) -> str:
        """Generate standardized audio embed HTML (platform-agnostic)"""
        audio_urls = metadata['media_info']['audio_urls']
        if not audio_urls:
            return ""

        audio_data = audio_urls[0]  # Use first audio
        audio_url = audio_data['url']
        audio_type = audio_data.get('type', 'audio/mpeg')

        # Standardized audio player for all platforms
        return f'''
<div class="audio-container">
    <h2>🎧 Listen to Audio</h2>
    <div class="speed-notice">
        ⚡ Audio automatically plays at 2x speed for efficient listening. You can adjust speed in player controls.
    </div>
    <div class="audio-embed">
        <audio controls controlsList="nodownload" style="width: 100%; max-width: 600px;">
            <source src="{audio_url}" type="{audio_type}">
            Your browser does not support the audio element.
        </audio>
    </div>
    <p class="audio-note">
        <strong>Note:</strong> Audio content embedded from original article.
    </p>
</div>'''

    # Utility methods (keeping existing implementations)
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

    def _extract_article_text_content(self, soup) -> str:
        """Extract main article text content"""
        # Try multiple content selectors
        content_selectors = [
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

    def _format_transcript_for_analysis(self, transcript_data: Dict) -> str:
        """Format transcript for AI analysis"""
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

    def _convert_timestamp_to_seconds(self, timestamp: str) -> int:
        """Convert MM:SS or H:MM:SS timestamp to seconds"""
        parts = timestamp.split(':')
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # H:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0

    def _load_template(self, template_name: str = "article_summary.html") -> str:
        """Load HTML template"""
        template_path = self.base_dir / "programs" / "article_summarizer" / "scripts" / "templates" / template_name
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template not found: {template_path}")

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

    def _update_index_file(self, filename: str, metadata: Dict, ai_summary: Dict):
        """Update the index file with new entry"""
        index_path = self.html_dir / "index.html"

        # Collect existing articles data
        articles_data = []

        if index_path.exists():
            # Parse existing index to extract articles
            with open(index_path, 'r') as f:
                content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            article_list = soup.find('ul', class_='article-list')

            if article_list:
                for item in article_list.find_all('li', class_='article-item'):
                    link = item.find('a', class_='article-title')
                    desc = item.find('p', class_='article-description')
                    if link and desc:
                        # Extract URL from article HTML file for better domain statistics
                        article_url = ''
                        try:
                            article_file = self.html_dir / link.get('href')
                            if article_file.exists():
                                with open(article_file, 'r') as af:
                                    article_content = af.read()
                                    # Look for URL in metadata section
                                    url_pattern = r'<li><strong>URL:</strong> <a href="([^"]+)"'
                                    import re
                                    url_match = re.search(url_pattern, article_content)
                                    if url_match:
                                        article_url = url_match.group(1)
                        except:
                            pass

                        articles_data.append({
                            'filename': link.get('href'),
                            'title': self._clean_title_indicators(link.get_text()),
                            'description': desc.get_text(),
                            'url': article_url if article_url else metadata.get('url', '')
                        })

        # Check if article already exists and update or add
        existing_article = None
        for i, article in enumerate(articles_data):
            if article['filename'] == filename:
                existing_article = i
                break

        if existing_article is not None:
            # Update existing article
            articles_data[existing_article].update({
                'title': metadata.get('title', ''),
                'description': f"Updated on {datetime.now().strftime('%B %d, %Y')}",
                'url': metadata.get('url', '')
            })
            # Move to front (most recent)
            article = articles_data.pop(existing_article)
            articles_data.insert(0, article)
        else:
            # Add new article at the beginning
            articles_data.insert(0, {
                'filename': filename,
                'title': metadata.get('title', ''),
                'description': f"Generated on {datetime.now().strftime('%B %d, %Y')}",
                'url': metadata.get('url', '')
            })

        # Generate statistics
        stats = self._collect_index_statistics(articles_data)

        # Generate articles list HTML
        articles_list_html = self._generate_articles_list_html(articles_data)

        # Load index template
        index_template = self._load_template("index.html")

        # Prepare template variables
        template_vars = {
            'TOTAL_ARTICLES': str(stats['total_articles']),
            'VIDEO_ARTICLES': str(stats['video_articles']),
            'AUDIO_ARTICLES': str(stats['audio_articles']),
            'DOMAINS_COUNT': str(stats['domains_count']),
            'ARTICLES_LIST': articles_list_html,
            'LAST_UPDATED': stats['last_updated']
        }

        # Replace template variables
        index_content = index_template
        for var, value in template_vars.items():
            index_content = index_content.replace(f'{{{{{var}}}}}', value)

        # Write updated index
        with open(index_path, 'w') as f:
            f.write(index_content)

    def _clean_title_indicators(self, title: str) -> str:
        """Remove repeated indicator text from title"""
        import re

        # Remove repeated patterns of indicators
        indicators = ['📹 VIDEO', '🎧 AUDIO', '🔄 UPDATED']
        for indicator in indicators:
            # Remove the indicator text itself (not the spans)
            title = title.replace(indicator, '')

        # Remove any multiple spaces
        title = re.sub(r'\s+', ' ', title).strip()

        return title

    def _collect_index_statistics(self, articles_data: list) -> Dict:
        """Collect statistics about the article collection"""
        from urllib.parse import urlparse

        stats = {
            'total_articles': len(articles_data),
            'video_articles': 0,
            'audio_articles': 0,
            'domains': set(),
            'last_updated': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }

        for article in articles_data:
            # Check if article has video or audio indicators
            article_path = self.html_dir / article['filename']
            if article_path.exists():
                try:
                    with open(article_path, 'r') as f:
                        content = f.read()
                        # More specific detection to avoid CSS false positives
                        if 'Video Content:</strong> Yes' in content:
                            stats['video_articles'] += 1
                        if 'Audio Content:</strong> Yes' in content:
                            stats['audio_articles'] += 1
                except:
                    pass

            # Extract domain from URL if available
            if 'url' in article and article['url']:
                try:
                    domain = urlparse(article['url']).netloc
                    if domain:
                        stats['domains'].add(domain)
                except:
                    pass

        stats['domains_count'] = len(stats['domains'])
        return stats

    def _generate_articles_list_html(self, articles_data: list) -> str:
        """Generate HTML for articles list"""
        articles_html = ""

        for article in articles_data:
            filename = article['filename']
            title = article['title']
            description = article['description']
            is_updated = 'Updated on' in description

            # Check if article has video or audio
            has_video = False
            has_audio = False
            article_path = self.html_dir / filename
            if article_path.exists():
                try:
                    with open(article_path, 'r') as f:
                        content = f.read()
                        # More specific detection to avoid CSS false positives
                        has_video = 'Video Content:</strong> Yes' in content
                        has_audio = 'Audio Content:</strong> Yes' in content
                except:
                    pass

            # Generate indicators
            indicators = ""
            if has_video:
                indicators += '<span class="video-indicator">📹 VIDEO</span>'
            if has_audio:
                indicators += '<span class="audio-indicator">🎧 AUDIO</span>'
            if is_updated:
                indicators += '<span class="updated-indicator">🔄 UPDATED</span>'

            articles_html += f'''
        <li class="article-item">
            <a href="{filename}" class="article-title">{title}{indicators}</a>
            <p class="article-description">{description}</p>
        </li>'''

        return articles_html

    def _save_to_database(self, metadata: Dict, ai_summary: Dict, html_content: str):
        """Save article data to Supabase database"""
        if not self.supabase:
            self.logger.warning("   ⚠️ Supabase not initialized - skipping database save")
            return

        try:
            content_type = metadata['content_type']

            # Extract transcript text if available
            transcript_text = None
            transcripts = metadata.get('transcripts', {})
            if transcripts:
                transcript_parts = []
                for video_id, transcript_data in transcripts.items():
                    if transcript_data.get('success'):
                        formatted = self._format_transcript_for_analysis(transcript_data)
                        if formatted:
                            transcript_parts.append(formatted)
                if transcript_parts:
                    transcript_text = "\n\n".join(transcript_parts)

            # Get video ID if available
            video_id = None
            if content_type.has_embedded_video and metadata.get('media_info', {}).get('youtube_urls'):
                video_id = metadata['media_info']['youtube_urls'][0].get('video_id')

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
                'summary_html': html_content,
                'summary_text': ai_summary.get('summary', ''),
                'transcript_text': transcript_text,
                'original_article_text': metadata.get('article_text'),
                'content_source': content_source,
                'video_id': video_id,
                'platform': metadata.get('platform'),
                'tags': [],  # Could extract from AI summary topics

                # Structured data
                'key_insights': ai_summary.get('key_insights', []),
                'main_points': ai_summary.get('main_points', []),
                'quotes': ai_summary.get('quotes', []),
                'takeaways': ai_summary.get('takeaways', []),

                # Metadata
                'duration_minutes': ai_summary.get('duration_minutes'),
                'word_count': ai_summary.get('word_count'),
                'topics': ai_summary.get('topics', []),
                'sentiment': ai_summary.get('sentiment'),
                'complexity_level': ai_summary.get('complexity_level'),
            }

            # Try to update existing article or insert new one
            result = self.supabase.table('articles').upsert(
                article_data,
                on_conflict='url'
            ).execute()

            if result.data:
                article_id = result.data[0]['id']
                self.logger.info(f"   ✅ Saved to database (article ID: {article_id})")
            else:
                self.logger.warning("   ⚠️ Database save completed but no data returned")

        except Exception as e:
            self.logger.error(f"   ❌ Database save failed: {e}")
            # Don't fail the entire process if database save fails

    def _commit_to_git(self, filename: str):
        """Commit changes to git"""
        try:
            subprocess.run(['git', 'add', '.'], cwd=self.base_dir, check=True)

            commit_msg = f"""Add article summary: {filename}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

            subprocess.run(['git', 'commit', '-m', commit_msg], cwd=self.base_dir, check=True)
            subprocess.run(['git', 'push'], cwd=self.base_dir, check=True)

            self.logger.info("✅ Successfully committed and pushed to GitHub")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Git operation failed: {e}")


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python3 article_summarizer.py <url>")
        sys.exit(1)

    url = sys.argv[1]

    try:
        summarizer = ArticleSummarizer()
        output_file = summarizer.process_article(url)
        print(f"Success! Generated: {Path(output_file).name}")

    except Exception as e:
        print(f"Error processing article: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()