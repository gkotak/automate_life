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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

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

            # Step 6: Update index
            self.logger.info("4. Updating index...")
            self._update_index_file(filename, metadata, ai_summary)

            # Step 7: Commit to git
            self.logger.info("5. Committing to git...")
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
            metadata.update(self._process_video_content(content_type.video_urls))
        elif content_type.has_embedded_audio:
            metadata.update(self._process_audio_content(content_type.audio_urls))
        else:
            metadata.update(self._process_text_content(soup))

        return metadata

    def _process_video_content(self, video_urls: List[Dict]) -> Dict:
        """Process content with embedded videos"""
        self.logger.info("   Found embedded videos, extracting transcripts...")

        transcripts = {}
        for video in video_urls:
            video_id = video['video_id']
            self.logger.info(f"      🎥 [HIGH PRIORITY] Main Video URL: {video['url']}")
            self.logger.info(f"      🎥 [HIGH PRIORITY] Embed URL: {video['embed_url']}")
            self.logger.info(f"      Extracting transcript for: {video_id}")

            transcript_data = self.transcript_processor.get_youtube_transcript(video_id)
            if transcript_data and transcript_data.get('success'):
                transcripts[video_id] = transcript_data
                self.logger.info(f"      ✓ Transcript extracted ({transcript_data.get('type', 'unknown')})")
            else:
                self.logger.info(f"      ✗ No transcript available: {transcript_data.get('error', 'Unknown error')}")

        return {
            'media_info': {'youtube_urls': video_urls},
            'transcripts': transcripts
        }

    def _process_audio_content(self, audio_urls: List[Dict]) -> Dict:
        """Process content with embedded audio"""
        self.logger.info("   Found embedded audio content...")

        # For now, just store audio metadata
        # Future: Add audio transcript extraction
        return {
            'media_info': {'audio_urls': audio_urls}
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
            return parsed_json
        else:
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

        context = f"""
IMPORTANT: This article contains video content. Video URLs found: {video_urls}
Please focus on extracting video timestamps with the following format:
- Use MM:SS format for timestamps (e.g., "5:23", "12:45", "1:02:30")
- Provide detailed descriptions of what happens at each timestamp
- Aim for 5-8 key timestamps that represent the most valuable content
- Include timestamps for: key insights, important discussions, actionable advice, demonstrations
"""

        # Add transcript data if available
        if transcripts:
            for video_id, transcript_data in transcripts.items():
                if transcript_data.get('success'):
                    formatted_transcript = self._format_transcript_for_analysis(transcript_data)
                    if formatted_transcript:
                        context += f"""

VIDEO TRANSCRIPT for {video_id} ({transcript_data.get('type', 'unknown')} transcript):
{formatted_transcript[:Config.MAX_TRANSCRIPT_CHARS]}{'...' if len(formatted_transcript) > Config.MAX_TRANSCRIPT_CHARS else ''}
"""

        return context

    def _build_audio_context(self, metadata: Dict) -> str:
        """Build context string for audio content"""
        audio_urls = metadata['media_info']['audio_urls']

        return f"""
IMPORTANT: This article contains audio/podcast content. Audio URLs found: {audio_urls}
This appears to be a podcast episode. Please:
- Identify key discussion points and insights from the conversation
- Extract actionable advice or key takeaways
- Note the participants/speakers if mentioned in the content
- Focus on the most valuable content and main themes
- DO NOT include any timestamps or time-based references since no transcript is available
Audio Platform: {audio_urls[0]['platform'] if audio_urls else 'unknown'}
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
        {{"insight": "insight text found in transcript", "timestamp": "MM:SS", "transcript_quote": "exact quote from transcript"}},
        {{"insight": "insight text NOT found in transcript", "timestamp": "", "transcript_quote": ""}},
        ...
    ],
    "media_timestamps": [
        {{"time": "MM:SS", "description": "detailed description of what happens at this time", "type": "{media_type_indicator}", "transcript_quote": "exact quote from transcript"}}
    ]
}}

CRITICAL:
- Use empty string "" for timestamp if no transcript match exists
- Only include media_timestamps entries for content you can find in the provided transcript
- Include ALL insights (with or without timestamps) but NEVER guess timestamps
- If transcript is truncated, only use timestamps from the visible portion
"""

    def _call_claude_api(self, prompt: str) -> str:
        """Call Claude Code API for AI-powered analysis"""
        try:
            result = subprocess.run([
                self.claude_cmd,
                "--print",
                "--output-format", "text",
                prompt
            ], capture_output=True, text=True, timeout=120, cwd=self.base_dir)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                self.logger.error(f"   ❌ Claude API failed with return code {result.returncode}: {result.stderr}")
                return f"Error calling Claude API: {result.stderr}"

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
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{.*?\})'
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

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
            'ANALYSIS_DATE': datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            'HAS_VIDEO': 'Yes' if content_type.has_embedded_video else 'No',
            'HAS_AUDIO': 'Yes' if content_type.has_embedded_audio else 'No',
            'SUMMARY_CONTENT': ai_summary.get('summary', 'No summary available'),
            'KEY_INSIGHTS': self._format_key_insights(ai_summary.get('key_insights', [])),
            'MEDIA_TIMESTAMPS': self._format_media_timestamps(ai_summary.get('media_timestamps', [])),
            'MEDIA_EMBED': self._generate_media_embed_html(metadata),
        }

    def _format_key_insights(self, insights: List[Dict]) -> str:
        """Format key insights as HTML"""
        if not insights:
            return "<p>No key insights extracted</p>"

        html = "<ul>"
        for insight in insights:
            html += f"<li>{insight.get('insight', '')}</li>"
        html += "</ul>"
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
        """Generate audio embed HTML"""
        # Future implementation for audio embeds
        return ""

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
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
        # Replace spaces and multiple spaces with underscores
        sanitized = re.sub(r'\s+', '_', sanitized)
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
        template_path = self.base_dir / "programs" / "video_summarizer" / "scripts" / "templates" / template_name
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
        # Implementation for updating index file
        pass

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