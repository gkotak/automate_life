#!/usr/bin/env python3
"""
Regenerate HTML - Re-render HTML files from existing Supabase data

This script allows you to regenerate HTML files without reprocessing content:
- Fetches article data from Supabase
- Regenerates HTML using current templates
- Saves updated HTML file

Useful when:
- Template design changes
- CSS/styling updates
- HTML structure improvements

Usage:
    python3 regenerate_html.py <article_url>
    python3 regenerate_html.py <article_id>
    python3 regenerate_html.py --all  # Regenerate all articles
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.base import BaseProcessor
from common.content_detector import ContentType


class HTMLRegenerator(BaseProcessor):
    """Regenerate HTML files from Supabase data"""

    def __init__(self):
        super().__init__("HTMLRegenerator")
        self.html_dir = self.output_dir / "article_summaries"
        self.html_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.supabase: Optional[Client] = None

        if supabase_url and supabase_key:
            try:
                self.supabase = create_client(supabase_url, supabase_key)
                self.logger.info("✅ Supabase client initialized")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize Supabase: {e}")
                sys.exit(1)
        else:
            self.logger.error("❌ Supabase credentials not found in environment")
            sys.exit(1)

    def regenerate_by_url(self, url: str) -> str:
        """Regenerate HTML for an article by URL"""
        self.logger.info(f"🔍 Fetching article data for: {url}")

        try:
            # Fetch article from Supabase
            result = self.supabase.table('articles').select('*').eq('url', url).execute()

            if not result.data:
                self.logger.error(f"❌ Article not found in database: {url}")
                sys.exit(1)

            article = result.data[0]
            return self._regenerate_html(article)

        except Exception as e:
            self.logger.error(f"❌ Error fetching article: {e}")
            sys.exit(1)

    def regenerate_by_id(self, article_id: int) -> str:
        """Regenerate HTML for an article by ID"""
        self.logger.info(f"🔍 Fetching article data for ID: {article_id}")

        try:
            # Fetch article from Supabase
            result = self.supabase.table('articles').select('*').eq('id', article_id).execute()

            if not result.data:
                self.logger.error(f"❌ Article not found in database: ID {article_id}")
                sys.exit(1)

            article = result.data[0]
            return self._regenerate_html(article)

        except Exception as e:
            self.logger.error(f"❌ Error fetching article: {e}")
            sys.exit(1)

    def regenerate_all(self):
        """Regenerate HTML for all articles"""
        self.logger.info("🔄 Regenerating HTML for all articles...")

        try:
            # Fetch all articles
            result = self.supabase.table('articles').select('*').execute()

            if not result.data:
                self.logger.warning("⚠️ No articles found in database")
                return

            total = len(result.data)
            self.logger.info(f"📊 Found {total} articles to regenerate")

            success_count = 0
            for i, article in enumerate(result.data, 1):
                try:
                    self.logger.info(f"\n[{i}/{total}] Processing: {article['title'][:60]}...")
                    self._regenerate_html(article)
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"❌ Failed to regenerate article {article['id']}: {e}")

            self.logger.info(f"\n✅ Regenerated {success_count}/{total} articles")

        except Exception as e:
            self.logger.error(f"❌ Error fetching articles: {e}")
            sys.exit(1)

    def _regenerate_html(self, article: Dict) -> str:
        """Regenerate HTML from article data"""
        self.logger.info(f"🎨 Regenerating HTML for: {article['title']}")

        # Reconstruct metadata and AI summary from database
        metadata = self._build_metadata_from_article(article)
        ai_summary = self._build_ai_summary_from_article(article)

        # Generate HTML content
        html_content = self._generate_html_content(metadata, ai_summary)

        # Save HTML file
        filename = self._sanitize_filename(article['title']) + '.html'
        html_path = self.html_dir / filename

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.logger.info(f"✅ Saved: {html_path}")

        # Update database with new HTML
        try:
            self.supabase.table('articles').update({
                'summary_html': html_content,
                'updated_at': datetime.now().isoformat()
            }).eq('id', article['id']).execute()
            self.logger.info("✅ Updated database with new HTML")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to update database: {e}")

        return str(html_path)

    def _build_metadata_from_article(self, article: Dict) -> Dict:
        """Build metadata dict from article data"""
        # Reconstruct content type
        content_type = ContentType(
            has_embedded_video=(article['content_source'] in ['video', 'mixed']),
            has_embedded_audio=(article['content_source'] in ['audio', 'mixed']),
            youtube_urls=[],
            audio_urls=[]
        )

        # Build media info
        media_info = {
            'youtube_urls': [],
            'audio_urls': []
        }

        if article.get('video_id'):
            media_info['youtube_urls'] = [{
                'url': f"https://www.youtube.com/watch?v={article['video_id']}",
                'video_id': article['video_id']
            }]

        if article.get('audio_url'):
            media_info['audio_urls'] = [{
                'url': article['audio_url'],
                'type': 'audio/mpeg'
            }]

        return {
            'title': article['title'],
            'url': article['url'],
            'content_type': content_type,
            'media_info': media_info,
            'platform': article.get('platform', 'unknown')
        }

    def _build_ai_summary_from_article(self, article: Dict) -> Dict:
        """Build AI summary dict from article data"""
        return {
            'summary': article.get('summary_text', 'No summary available'),
            'key_insights': article.get('key_insights', []),
            'media_timestamps': [],  # Could extract from key_insights if needed
            'duration_minutes': article.get('duration_minutes'),
            'word_count': article.get('word_count'),
            'topics': article.get('topics', [])
        }

    def _generate_html_content(self, metadata: Dict, ai_summary: Dict) -> str:
        """Generate the final HTML content (copied from ArticleSummarizer)"""
        template = self._load_template()
        template_vars = self._prepare_template_variables(metadata, ai_summary)

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
            'INSIGHTS_SECTION': self._format_insights_section(ai_summary.get('key_insights', []), content_type),
            'MEDIA_EMBED_SECTION': self._generate_media_embed_html(metadata),
            'TIMESTAMPS_SECTION': '',  # Not regenerating timestamps
            'SUMMARY_SECTIONS': '',
            'GENERATION_DATE': datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        }

    def _format_insights_section(self, insights: list, content_type) -> str:
        """Format key insights as HTML section"""
        if not insights:
            return ""

        jump_function = "jumpToAudioTime" if content_type.has_embedded_audio else "jumpToTime"

        html = '''
    <div class="summary-section">
        <h2>🔍 Key Insights</h2>
        <ul>'''
        for insight in insights:
            insight_text = insight.get('insight', '')
            timestamp = insight.get('time_formatted')
            timestamp_seconds = insight.get('timestamp_seconds')

            if timestamp and timestamp_seconds is not None:
                click_handler = f"{jump_function}({timestamp_seconds})"
                html += f'<li><span class="timestamp" onclick="{click_handler}" title="Jump to {timestamp}">⏰ {timestamp}</span> {insight_text}</li>'
            else:
                html += f"<li>{insight_text}</li>"

        html += '''
        </ul>
    </div>'''
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

        video_data = video_urls[0]
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
        audio_urls = metadata['media_info']['audio_urls']
        if not audio_urls:
            return ""

        audio_data = audio_urls[0]
        audio_url = audio_data['url']
        audio_type = audio_data.get('type', 'audio/mpeg')

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

    def _load_template(self) -> str:
        """Load HTML template"""
        template_path = self.base_dir / "programs" / "article_summarizer" / "scripts" / "templates" / "article_summary.html"

        if not template_path.exists():
            self.logger.error(f"❌ Template not found: {template_path}")
            sys.exit(1)

        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        return urlparse(url).netloc

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename"""
        import re
        sanitized = title.replace('–', '-').replace('—', '-').replace('−', '-')
        sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = ''.join(char if ord(char) < 128 else '_' for char in sanitized)
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        return sanitized[:100] if len(sanitized) > 100 else sanitized


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 regenerate_html.py <article_url>")
        print("  python3 regenerate_html.py <article_id>")
        print("  python3 regenerate_html.py --all")
        sys.exit(1)

    regenerator = HTMLRegenerator()

    arg = sys.argv[1]

    if arg == '--all':
        regenerator.regenerate_all()
    elif arg.isdigit():
        # Argument is an article ID
        html_path = regenerator.regenerate_by_id(int(arg))
        print(f"\n✅ HTML regenerated: {html_path}")
    else:
        # Argument is a URL
        html_path = regenerator.regenerate_by_url(arg)
        print(f"\n✅ HTML regenerated: {html_path}")


if __name__ == "__main__":
    main()
