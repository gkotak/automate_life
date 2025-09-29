#!/usr/bin/env python3
"""
Hybrid Video Article Summarizer
Combines deterministic Python operations with Claude Code AI capabilities
"""

import os
import sys
import json
import subprocess
import requests
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

class VideoArticleSummarizer:
    def __init__(self, base_dir="/Users/gauravkotak/cursor-projects-1/automate_life"):
        self.base_dir = Path(base_dir)
        self.html_dir = self.base_dir / "HTML" / "article_summaries"
        self.claude_cmd = self._find_claude_cli()

        # Ensure directories exist
        self.html_dir.mkdir(parents=True, exist_ok=True)

    def _find_claude_cli(self):
        """Find Claude CLI executable"""
        locations = [
            "/usr/local/bin/claude",
            "/opt/homebrew/bin/claude",
            "claude"  # Try PATH
        ]

        for location in locations:
            try:
                result = subprocess.run([location, "--version"],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return location
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        raise RuntimeError("Claude CLI not found. Please install Claude Code.")

    def _sanitize_filename(self, title):
        """Convert title to safe filename with underscores"""
        # Remove HTML tags if any
        title = re.sub(r'<[^>]+>', '', title)
        # Replace spaces and special chars with underscores
        filename = re.sub(r'[^\w\s-]', '', title)
        filename = re.sub(r'[\s-]+', '_', filename)
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        # Limit length
        return filename[:100] if filename else "untitled_article"

    def _extract_video_urls(self, soup, page_content):
        """Extract video URLs from page content"""
        video_info = {
            'youtube_urls': [],
            'video_embeds': [],
            'iframe_sources': []
        }

        # Extract YouTube URLs from various sources
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})'
        ]

        found_video_ids = set()
        for pattern in youtube_patterns:
            matches = re.findall(pattern, page_content)
            for match in matches:
                video_id = match
                if video_id not in found_video_ids:
                    found_video_ids.add(video_id)
                    video_info['youtube_urls'].append({
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'video_id': video_id,
                        'embed_url': f"https://www.youtube.com/embed/{video_id}"
                    })

        # Extract iframe sources
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src')
            if src:
                if 'youtube.com/embed' in src:
                    video_id_match = re.search(r'/embed/([a-zA-Z0-9_-]{11})', src)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        video_info['iframe_sources'].append({
                            'src': src,
                            'video_id': video_id,
                            'platform': 'youtube'
                        })
                else:
                    video_info['iframe_sources'].append({
                        'src': src,
                        'platform': 'other'
                    })

        return video_info

    def _extract_youtube_transcript(self, video_id):
        """Extract transcript from YouTube video if available"""
        try:
            # Initialize the API instance
            ytt_api = YouTubeTranscriptApi()

            # Try to get transcript (both manual and auto-generated)
            transcript_list = ytt_api.list(video_id)

            # Try to get a manually created transcript first
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
                transcript_data = transcript.fetch()
                # Convert FetchedTranscript to list of dicts for JSON serialization
                transcript_list_data = []
                for entry in transcript_data:
                    transcript_list_data.append({
                        'start': entry.start,
                        'text': entry.text,
                        'duration': getattr(entry, 'duration', 0)
                    })
                return {
                    'success': True,
                    'type': 'manual',
                    'transcript': transcript_list_data,
                    'language': 'en'
                }
            except:
                # Fall back to auto-generated transcript
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    transcript_data = transcript.fetch()
                    # Convert FetchedTranscript to list of dicts for JSON serialization
                    transcript_list_data = []
                    for entry in transcript_data:
                        transcript_list_data.append({
                            'start': entry.start,
                            'text': entry.text,
                            'duration': getattr(entry, 'duration', 0)
                        })
                    return {
                        'success': True,
                        'type': 'auto_generated',
                        'transcript': transcript_list_data,
                        'language': 'en'
                    }
                except:
                    return {
                        'success': False,
                        'error': 'No English transcript available',
                        'transcript': []
                    }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to fetch transcript: {str(e)}',
                'transcript': []
            }

    def _format_transcript_for_analysis(self, transcript_data):
        """Format transcript data into readable text for AI analysis"""
        if not transcript_data or not transcript_data.get('success'):
            return ""

        transcript = transcript_data.get('transcript', [])
        formatted_text = []

        for entry in transcript:
            # Handle dict objects (converted from FetchedTranscript)
            start_time = entry.get('start', 0)
            text = entry.get('text', '').strip()

            # Convert seconds to MM:SS format
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"{minutes}:{seconds:02d}"

            if text:
                formatted_text.append(f"[{timestamp}] {text}")

        return "\n".join(formatted_text)

    def _extract_basic_metadata(self, url):
        """Extract basic metadata from URL (deterministic part)"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract basic info
            title = soup.find('title')
            title = title.get_text().strip() if title else "Untitled Article"

            # Extract video information
            video_info = self._extract_video_urls(soup, response.text)

            # Determine if video content exists
            has_video_indicators = (
                len(video_info['youtube_urls']) > 0 or
                len(video_info['iframe_sources']) > 0 or
                'youtube.com' in response.text or
                'youtu.be' in response.text or
                soup.find('video') is not None
            )

            # Extract YouTube transcripts if videos found
            transcripts = {}
            if video_info['youtube_urls']:
                print("   Found YouTube videos, extracting transcripts...")
                for video in video_info['youtube_urls']:
                    video_id = video['video_id']
                    print(f"     Extracting transcript for: {video_id}")
                    transcript_data = self._extract_youtube_transcript(video_id)
                    transcripts[video_id] = transcript_data
                    if transcript_data['success']:
                        print(f"     ✓ Transcript extracted ({transcript_data['type']})")
                    else:
                        print(f"     ✗ No transcript available: {transcript_data.get('error', 'Unknown error')}")

            return {
                'title': title,
                'url': url,
                'domain': urlparse(url).netloc,
                'has_video_indicators': has_video_indicators,
                'video_info': video_info,
                'transcripts': transcripts,
                'extracted_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'title': f"Article from {urlparse(url).netloc}",
                'url': url,
                'domain': urlparse(url).netloc,
                'has_video_indicators': False,
                'video_info': {'youtube_urls': [], 'video_embeds': [], 'iframe_sources': []},
                'transcripts': {},
                'extraction_error': str(e),
                'extracted_at': datetime.now().isoformat()
            }

    def _call_claude_api(self, prompt):
        """Call Claude Code API for AI-powered analysis"""
        try:
            # Call Claude CLI with --print flag for non-interactive mode
            result = subprocess.run([
                self.claude_cmd,
                "--print",
                "--output-format", "text",
                prompt
            ], capture_output=True, text=True, timeout=120, cwd=self.base_dir)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error calling Claude API: {result.stderr}"

        except subprocess.TimeoutExpired:
            return f"Claude API call timed out after 120 seconds"
        except Exception as e:
            return f"Error in Claude API call: {str(e)}"

    def _extract_json_from_response(self, response):
        """Extract and parse JSON from Claude's response, handling various formats"""
        # Try to find JSON block in response
        import re

        # Look for JSON between ```json and ``` or just plain JSON
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

        # If no JSON found, return None
        return None

    def _format_summary_as_html(self, summary_text):
        """Convert plain text summary to formatted HTML"""
        # Handle markdown-like formatting
        html = summary_text.replace('\n\n', '</p><p>')
        html = html.replace('\n• ', '<br>• ')
        html = html.replace('\n## ', '</p><h3>')
        html = html.replace('\n### ', '</p><h4>')

        # Wrap in paragraph tags
        if not html.startswith('<'):
            html = f'<p>{html}</p>'

        # Close any opened headers
        html = html.replace('<h3>', '<h3>').replace('\n', '</h3><p>')
        html = html.replace('<h4>', '<h4>').replace('\n', '</h4><p>')

        return html

    def _generate_summary_with_ai(self, url, metadata):
        """Use AI to generate content summary (non-deterministic part)"""
        video_context = ""
        transcript_context = ""

        if metadata.get('video_info') and metadata['video_info']['youtube_urls']:
            video_context = f"""
        IMPORTANT: This article contains video content. Video URLs found: {metadata['video_info']['youtube_urls']}

        Please focus on extracting video timestamps with the following format:
        - Use MM:SS format for timestamps (e.g., "5:23", "12:45", "1:02:30")
        - Provide detailed descriptions of what happens at each timestamp
        - Aim for 5-8 key timestamps that represent the most valuable content
        - Include timestamps for: key insights, important discussions, actionable advice, demonstrations
        """

        # Include transcript data if available
        if metadata.get('transcripts'):
            available_transcripts = []
            for video_id, transcript_data in metadata['transcripts'].items():
                if transcript_data.get('success'):
                    formatted_transcript = self._format_transcript_for_analysis(transcript_data)
                    if formatted_transcript:
                        available_transcripts.append(f"""
        VIDEO TRANSCRIPT for {video_id} ({transcript_data.get('type', 'unknown')} transcript):
        {formatted_transcript[:5000]}...  # Truncated for prompt size
        """)

            if available_transcripts:
                transcript_context = f"""
        TRANSCRIPT DATA AVAILABLE: The following are actual transcripts from the YouTube videos.
        Use these to create ACCURATE timestamps and content descriptions:

        {''.join(available_transcripts)}

        Since you have the actual transcript, please provide precise timestamps that match the actual content,
        not estimates. Focus on the most valuable parts of the video content.
        """

        prompt = f"""
        Analyze this article: {url}

        Create a comprehensive summary with the following structure:
        1. Write a clear, structured summary (max 1000 words) in HTML format
        2. Extract 5-8 key insights as bullet points
        3. If video content exists, identify specific timestamps with detailed descriptions
        4. List recommended sections for readers

        {video_context}
        {transcript_context}

        Please provide a clean, well-formatted response focusing on the content value rather than technical processing details.

        Article metadata: {json.dumps(metadata, indent=2)}

        Return your response in this JSON format:
        {{
            "summary": "HTML formatted summary content",
            "key_insights": ["insight 1", "insight 2", ...],
            "video_timestamps": [{{"time": "MM:SS", "description": "detailed description of what happens at this time"}}, ...],
            "recommended_sections": ["section 1", "section 2", ...]
        }}
        """

        response = self._call_claude_api(prompt)

        # Try to extract JSON from response
        parsed_json = self._extract_json_from_response(response)

        if parsed_json:
            # Ensure summary is properly formatted as HTML
            if 'summary' in parsed_json:
                summary = parsed_json['summary']
                if not any(tag in summary for tag in ['<p>', '<div>', '<h1>', '<h2>', '<h3>']):
                    # Convert plain text to HTML
                    parsed_json['summary'] = self._format_summary_as_html(summary)

            return parsed_json
        else:
            # Fallback: format the entire response as HTML summary
            formatted_summary = self._format_summary_as_html(response)
            return {
                "summary": formatted_summary,
                "key_insights": ["Content analyzed - see summary for details"],
                "video_timestamps": [],
                "recommended_sections": []
            }

    def _load_template(self, template_name="article_summary.html"):
        """Load HTML template from templates directory"""
        template_path = self.base_dir / "scripts" / "templates" / template_name
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template not found: {template_path}")

    def _convert_timestamp_to_seconds(self, timestamp):
        """Convert MM:SS or H:MM:SS timestamp to seconds"""
        parts = timestamp.split(':')
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # H:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0

    def _generate_video_embed_html(self, metadata):
        """Generate video embed HTML if video URLs are found"""
        video_info = metadata.get('video_info', {})

        # Prioritize YouTube embeds
        if video_info.get('youtube_urls'):
            video_data = video_info['youtube_urls'][0]  # Use first video found
            video_id = video_data['video_id']

            embed_html = f'''
    <div class="video-container">
        <h2>🎥 Watch the Video</h2>
        <div class="video-embed">
            <iframe
                src="https://www.youtube.com/embed/{video_id}?enablejsapi=1"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen>
            </iframe>
        </div>
    </div>'''
            return embed_html

        elif video_info.get('iframe_sources'):
            # Use first iframe source
            iframe_data = video_info['iframe_sources'][0]
            if iframe_data.get('platform') == 'youtube':
                video_id = iframe_data.get('video_id')
                embed_html = f'''
    <div class="video-container">
        <h2>🎥 Watch the Video</h2>
        <div class="video-embed">
            <iframe
                src="https://www.youtube.com/embed/{video_id}?enablejsapi=1"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen>
            </iframe>
        </div>
    </div>'''
                return embed_html

        return ''

    def _generate_section_html(self, ai_summary, metadata):
        """Generate dynamic HTML sections based on AI summary content"""
        sections = {}

        # Generate video embed section
        video_embed = self._generate_video_embed_html(metadata)
        sections['VIDEO_EMBED_SECTION'] = video_embed

        # Generate insights section
        insights = ai_summary.get('key_insights', [])
        if insights and insights != ["Analysis completed but formatting needs review"] and insights != ["Content analyzed - see summary for details"]:
            insights_html = '<div class="summary-section"><h3>💡 Key Insights</h3><ul>'
            for insight in insights:
                insights_html += f'<li>{insight}</li>'
            insights_html += '</ul></div>'
            sections['INSIGHTS_SECTION'] = insights_html
        else:
            sections['INSIGHTS_SECTION'] = ''

        # Generate interactive video timestamps section
        timestamps = ai_summary.get('video_timestamps', [])
        video_info = metadata.get('video_info', {})

        if timestamps and video_info.get('youtube_urls'):
            video_id = video_info['youtube_urls'][0]['video_id']
            timestamps_html = '<div class="video-timestamps"><h3>🎬 Interactive Video Highlights</h3>'
            timestamps_html += '<p><em>Click timestamps to jump to that part of the video:</em></p><ul>'

            for ts in timestamps:
                time_str = ts.get("time", "0:00")
                description = ts.get("description", "No description")
                seconds = self._convert_timestamp_to_seconds(time_str)

                timestamps_html += f'''
                <li class="timestamp-item">
                    <span class="timestamp-link" onclick="jumpToTime({seconds})">
                        <strong>{time_str}</strong>
                    </span>
                    <button class="play-button" onclick="jumpToTime({seconds})">▶ Play</button>
                    <br>
                    <span class="timestamp-description">{description}</span>
                </li>'''

            timestamps_html += '</ul></div>'
            sections['TIMESTAMPS_SECTION'] = timestamps_html

            # Add video ID for JavaScript
            sections['VIDEO_ID'] = video_id
        else:
            sections['TIMESTAMPS_SECTION'] = ''
            sections['VIDEO_ID'] = ''

        # Generate recommended sections
        if ai_summary.get('recommended_sections'):
            recommended_html = '<div class="recommended-section"><h3>⭐ Recommended Sections</h3><ul>'
            for section in ai_summary['recommended_sections']:
                recommended_html += f'<li>{section}</li>'
            recommended_html += '</ul></div>'
            sections['RECOMMENDED_SECTION'] = recommended_html
        else:
            sections['RECOMMENDED_SECTION'] = ''

        return sections

    def _generate_html_content(self, metadata, ai_summary):
        """Generate HTML content using external template (deterministic template loading)"""
        # Load the HTML template
        template = self._load_template()

        # Generate dynamic sections
        sections = self._generate_section_html(ai_summary, metadata)

        # Prepare template variables
        template_vars = {
            'TITLE': metadata['title'],
            'DOMAIN': metadata['domain'],
            'URL': metadata['url'],
            'EXTRACTED_AT': metadata['extracted_at'],
            'HAS_VIDEO': 'Yes' if metadata.get('has_video_indicators') else 'No',
            'SUMMARY_CONTENT': ai_summary.get('summary', 'Summary not available'),
            'GENERATION_DATE': datetime.now().strftime('%B %d, %Y'),
            **sections
        }

        # Replace template variables
        html_content = template
        for var, value in template_vars.items():
            html_content = html_content.replace(f'{{{{{var}}}}}', value)

        return html_content

    def _collect_index_statistics(self, articles_data):
        """Collect statistics about the article collection"""
        stats = {
            'total_articles': len(articles_data),
            'video_articles': 0,
            'domains': set(),
            'last_updated': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }

        for article in articles_data:
            # Check if article has video indicators
            article_path = self.html_dir / article['filename']
            if article_path.exists():
                try:
                    with open(article_path, 'r') as f:
                        content = f.read()
                        if 'video-container' in content or 'Video Content:</strong> Yes' in content:
                            stats['video_articles'] += 1
                except:
                    pass

            # Extract domain from URL if available
            if 'url' in article:
                domain = urlparse(article['url']).netloc
                if domain:
                    stats['domains'].add(domain)

        stats['domains_count'] = len(stats['domains'])
        return stats

    def _generate_articles_list_html(self, articles_data):
        """Generate HTML for articles list"""
        articles_html = ""

        for article in articles_data:
            filename = article['filename']
            title = article['title']
            description = article['description']
            is_updated = 'Updated on' in description

            # Check if article has video
            has_video = False
            article_path = self.html_dir / filename
            if article_path.exists():
                try:
                    with open(article_path, 'r') as f:
                        content = f.read()
                        has_video = 'video-container' in content or 'Video Content:</strong> Yes' in content
                except:
                    pass

            # Generate indicators
            indicators = ""
            if has_video:
                indicators += '<span class="video-indicator">📹 VIDEO</span>'
            if is_updated:
                indicators += '<span class="updated-indicator">🔄 UPDATED</span>'

            articles_html += f'''
        <li class="article-item">
            <a href="{filename}" class="article-title">{title}{indicators}</a>
            <p class="article-description">{description}</p>
        </li>'''

        return articles_html

    def _update_index_html(self, new_filename, title, metadata=None):
        """Update index.html with new article using external template"""
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
                        articles_data.append({
                            'filename': link.get('href'),
                            'title': link.get_text().replace('📹 VIDEO', '').replace('🔄 UPDATED', '').strip(),
                            'description': desc.get_text(),
                            'url': metadata.get('url', '') if metadata else ''
                        })

        # Check if article already exists and update or add
        existing_article = None
        for i, article in enumerate(articles_data):
            if article['filename'] == new_filename:
                existing_article = i
                break

        if existing_article is not None:
            # Update existing article
            articles_data[existing_article].update({
                'title': title,
                'description': f"Updated on {datetime.now().strftime('%B %d, %Y')}",
                'url': metadata.get('url', '') if metadata else articles_data[existing_article].get('url', '')
            })
            # Move to front (most recent)
            article = articles_data.pop(existing_article)
            articles_data.insert(0, article)
        else:
            # Add new article at the beginning
            articles_data.insert(0, {
                'filename': new_filename,
                'title': title,
                'description': f"Generated on {datetime.now().strftime('%B %d, %Y')}",
                'url': metadata.get('url', '') if metadata else ''
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

    def _git_commit_and_push(self, filename):
        """Handle git operations (deterministic)"""
        try:
            os.chdir(self.base_dir)

            # Add files
            subprocess.run(['git', 'add', f'HTML/article_summaries/{filename}'], check=True)
            subprocess.run(['git', 'add', 'HTML/article_summaries/index.html'], check=True)

            # Commit
            commit_msg = f"""Add article summary: {filename}

Generated via hybrid Python + Claude Code approach

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)

            # Push
            subprocess.run(['git', 'push'], check=True)

            return True

        except subprocess.CalledProcessError as e:
            print(f"Git operation failed: {e}")
            return False

    def process_article(self, url):
        """Main processing pipeline"""
        print(f"Processing article: {url}")

        # Step 1: Extract basic metadata (deterministic)
        print("1. Extracting metadata...")
        metadata = self._extract_basic_metadata(url)
        print(f"   Title: {metadata['title']}")

        # Step 2: Generate filename (deterministic)
        filename = self._sanitize_filename(metadata['title']) + '.html'
        print(f"   Filename: {filename}")

        # Step 3: AI-powered content analysis (non-deterministic)
        print("2. Analyzing content with AI...")
        ai_summary = self._generate_summary_with_ai(url, metadata)

        # Step 4: Generate HTML (deterministic template)
        print("3. Generating HTML...")
        html_content = self._generate_html_content(metadata, ai_summary)

        # Step 5: Write file (deterministic)
        html_path = self.html_dir / filename
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"   Created: {html_path}")

        # Step 6: Update index (deterministic)
        print("4. Updating index...")
        self._update_index_html(filename, metadata['title'], metadata)

        # Step 7: Git operations (deterministic)
        print("5. Committing to git...")
        if self._git_commit_and_push(filename):
            print("✅ Successfully committed and pushed to GitHub")
        else:
            print("❌ Git operations failed")

        print(f"✅ Processing complete: {filename}")
        return filename

def main():
    if len(sys.argv) != 2:
        print("Usage: python video_article_summarizer.py <article_url>")
        sys.exit(1)

    url = sys.argv[1]
    summarizer = VideoArticleSummarizer()

    try:
        result = summarizer.process_article(url)
        print(f"Success! Generated: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()