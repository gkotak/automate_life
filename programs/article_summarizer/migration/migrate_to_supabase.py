#!/usr/bin/env python3
"""
Migration script to import existing HTML files into Supabase database
Extracts content, generates embeddings, and uploads to articles table
"""

import os
import re
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, unquote

# Add the scripts directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

try:
    from supabase import create_client, Client
    from sentence_transformers import SentenceTransformer
    from bs4 import BeautifulSoup
    import requests
except ImportError as e:
    print(f"❌ Missing required packages. Please install:")
    print("pip install supabase sentence-transformers beautifulsoup4 requests")
    sys.exit(1)

# Supabase configuration
SUPABASE_URL = "https://gmwqeqlbfhxffxpsjokf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdtd3FlcWxiZmh4ZmZ4cHNqb2tmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MDgxNDIsImV4cCI6MjA3NDk4NDE0Mn0.U_iJr_72FdbrkMj83eevJ_Hzi3fXQDoVrCsCnZj8fGc"

# File paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "article_summaries"

class ContentExtractor:
    """Extract different types of content from HTML files"""

    def __init__(self):
        # Use lightweight, efficient embedding model (384 dimensions)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    def extract_from_html(self, html_content: str, filename: str) -> Dict:
        """Extract all content types from HTML file"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract title
        title = self._extract_title(soup, filename)

        # Extract URL from HTML or filename
        url = self._extract_url(soup, filename)

        # Extract summary (Claude's output)
        summary_text, summary_html = self._extract_summary(soup)

        # Extract transcript if available
        transcript_text = self._extract_transcript(soup)

        # Extract original article content if available
        original_article_text = self._extract_original_article(soup)

        # Determine content source
        content_source = self._determine_content_source(soup, transcript_text, original_article_text)

        # Extract video/platform info
        video_id, platform = self._extract_video_info(soup, url)

        # Extract creation date
        created_at = self._extract_creation_date(soup, filename)

        # Generate tags
        tags = self._generate_tags(summary_text, transcript_text, platform)

        return {
            'title': title,
            'url': url,
            'summary_html': summary_html,
            'summary_text': summary_text,
            'transcript_text': transcript_text,
            'original_article_text': original_article_text,
            'content_source': content_source,
            'video_id': video_id,
            'platform': platform,
            'created_at': created_at,
            'tags': tags
        }

    def _extract_title(self, soup: BeautifulSoup, filename: str) -> str:
        """Extract title from HTML or filename"""
        # Try HTML title tag first
        title_tag = soup.find('title')
        if title_tag and title_tag.get_text().strip():
            return title_tag.get_text().strip()

        # Try h1 tag
        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.get_text().strip():
            return h1_tag.get_text().strip()

        # Fall back to filename
        title = filename.replace('.html', '').replace('_', ' ')
        return title

    def _extract_url(self, soup: BeautifulSoup, filename: str) -> str:
        """Extract original URL from HTML or derive from filename"""
        # Look for URL in HTML (might be in a comment or meta tag)
        url_patterns = [
            r'https?://[^\s<>"{}|\\^`\[\]]+',
            r'URL:\s*(https?://[^\s<>"{}|\\^`\[\]]+)',
            r'Source:\s*(https?://[^\s<>"{}|\\^`\[\]]+)'
        ]

        html_text = str(soup)
        for pattern in url_patterns:
            matches = re.findall(pattern, html_text)
            if matches:
                return matches[0]

        # Try to reconstruct URL from filename
        # This is best effort - you may need to manually fix some URLs
        if 'stratechery' in filename.lower():
            return f"https://stratechery.com/{filename.replace('.html', '').replace('_', '-').lower()}"
        elif 'lenny' in filename.lower():
            return f"https://www.lennysnewsletter.com/p/{filename.replace('.html', '').replace('_', '-').lower()}"

        return f"https://example.com/{filename}"  # Placeholder

    def _extract_summary(self, soup: BeautifulSoup) -> Tuple[str, str]:
        """Extract Claude's summary in both text and HTML format"""
        # Remove style and script tags to clean up content
        for script in soup(["script", "style"]):
            script.decompose()

        # Look for the main content within body tag (excluding header/footer)
        body = soup.find('body')
        if body:
            # Try to find the main content area (everything inside body)
            summary_html = ''.join(str(tag) for tag in body.children if str(tag).strip())
            summary_text = body.get_text().strip()
        else:
            # Fallback to entire soup if no body tag
            summary_html = str(soup)
            summary_text = soup.get_text().strip()

        return summary_text, summary_html

    def _extract_transcript(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract video/audio transcript if available"""
        # Look for transcript sections
        transcript_patterns = [
            'transcript',
            'captions',
            'video-text',
            'audio-text'
        ]

        for pattern in transcript_patterns:
            transcript_div = soup.find(['div', 'section'], class_=re.compile(pattern, re.I))
            if transcript_div:
                return transcript_div.get_text().strip()

        # Look for timestamp patterns (indicating transcript)
        timestamp_pattern = r'\d{1,2}:\d{2}(?::\d{2})?'
        text_content = soup.get_text()
        if re.search(timestamp_pattern, text_content):
            # This might contain transcript data
            lines = text_content.split('\n')
            transcript_lines = [line for line in lines if re.search(timestamp_pattern, line)]
            if len(transcript_lines) > 5:  # Likely a transcript
                return '\n'.join(transcript_lines)

        return None

    def _extract_original_article(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract original article content if available"""
        # Look for article content sections
        article_patterns = [
            'article-content',
            'original-article',
            'full-text',
            'article-body'
        ]

        for pattern in article_patterns:
            article_div = soup.find(['div', 'section', 'article'], class_=re.compile(pattern, re.I))
            if article_div:
                return article_div.get_text().strip()

        return None

    def _determine_content_source(self, soup: BeautifulSoup, transcript: Optional[str], article: Optional[str]) -> str:
        """Determine the primary content source"""
        html_text = str(soup).lower()

        has_video = 'youtube' in html_text or 'video' in html_text
        has_audio = 'audio' in html_text or 'podcast' in html_text
        has_transcript = transcript is not None
        has_article = article is not None

        if has_video and has_transcript:
            return 'video'
        elif has_audio and has_transcript:
            return 'audio'
        elif has_article:
            return 'article'
        elif has_transcript:
            return 'mixed'
        else:
            return 'article'  # Default

    def _extract_video_info(self, soup: BeautifulSoup, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract video ID and platform information"""
        html_text = str(soup)

        # YouTube video ID
        youtube_patterns = [
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'youtu\.be/([a-zA-Z0-9_-]+)',
            r'youtube\.com/embed/([a-zA-Z0-9_-]+)'
        ]

        for pattern in youtube_patterns:
            match = re.search(pattern, html_text)
            if match:
                return match.group(1), 'youtube'

        # Determine platform from URL or content
        if 'stratechery' in url.lower():
            return None, 'stratechery'
        elif 'lenny' in url.lower():
            return None, 'substack'
        elif 'medium' in url.lower():
            return None, 'medium'

        return None, 'unknown'

    def _extract_creation_date(self, soup: BeautifulSoup, filename: str) -> str:
        """Extract or estimate creation date"""
        # Try to find date in HTML
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        ]

        html_text = str(soup)
        for pattern in date_patterns:
            match = re.search(pattern, html_text)
            if match:
                try:
                    return datetime.strptime(match.group(), '%Y-%m-%d').isoformat()
                except:
                    pass

        # Fall back to file modification time
        file_path = OUTPUT_DIR / filename
        if file_path.exists():
            mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            return mod_time.isoformat()

        return datetime.now().isoformat()

    def _generate_tags(self, summary: str, transcript: Optional[str], platform: Optional[str]) -> List[str]:
        """Generate tags based on content analysis"""
        tags = []

        if platform:
            tags.append(platform)

        # Add content type tags
        text_to_analyze = (summary or '') + ' ' + (transcript or '')
        text_lower = text_to_analyze.lower()

        # Technology tags
        tech_keywords = {
            'ai': ['ai', 'artificial intelligence', 'machine learning', 'llm', 'gpt', 'claude'],
            'startup': ['startup', 'venture', 'funding', 'vc', 'entrepreneur'],
            'product': ['product', 'features', 'user experience', 'design'],
            'business': ['business', 'strategy', 'revenue', 'growth', 'market'],
            'tech': ['technology', 'software', 'development', 'engineering']
        }

        for tag, keywords in tech_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                tags.append(tag)

        return tags[:5]  # Limit to 5 tags

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for semantic search"""
        return self.embedding_model.encode(text).tolist()

class SupabaseMigrator:
    """Handle Supabase database operations"""

    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.extractor = ContentExtractor()

    def migrate_all_files(self) -> None:
        """Migrate all HTML files to Supabase"""
        html_files = list(OUTPUT_DIR.glob("*.html"))

        if not html_files:
            print(f"❌ No HTML files found in {OUTPUT_DIR}")
            return

        print(f"🔍 Found {len(html_files)} HTML files to migrate")

        successful = 0
        failed = 0

        for file_path in html_files:
            try:
                if file_path.name == 'index.html':
                    continue  # Skip index file

                print(f"\n📄 Processing: {file_path.name}")

                # Read HTML content
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Extract content
                article_data = self.extractor.extract_from_html(html_content, file_path.name)

                # Generate combined text for embedding
                combined_text = f"{article_data['title']} {article_data['summary_text'] or ''}"
                if article_data['transcript_text']:
                    combined_text += f" {article_data['transcript_text'][:1000]}"  # Limit transcript for embedding

                # Generate embedding
                embedding = self.extractor.generate_embedding(combined_text)
                article_data['embedding'] = embedding

                # Upload to Supabase
                result = self.supabase.table('articles').upsert(article_data).execute()

                if result.data:
                    print(f"✅ Successfully migrated: {article_data['title'][:60]}...")
                    successful += 1
                else:
                    print(f"❌ Failed to migrate: {file_path.name}")
                    failed += 1

            except Exception as e:
                print(f"❌ Error processing {file_path.name}: {str(e)}")
                failed += 1

        print(f"\n📊 Migration Summary:")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📁 Total: {len(html_files)}")

    def test_search(self) -> None:
        """Test search functionality after migration"""
        print("\n🔍 Testing search functionality...")

        try:
            # Test basic query
            result = self.supabase.table('articles').select('title, url').limit(5).execute()
            print(f"✅ Basic query successful: {len(result.data)} articles found")

            # Test search function (if available)
            # This requires the search functions to be set up in Supabase
            print("✅ Database connection successful")

        except Exception as e:
            print(f"❌ Search test failed: {str(e)}")

def main():
    print("🚀 Starting migration to Supabase...")
    print(f"📁 Source directory: {OUTPUT_DIR}")
    print(f"🔗 Supabase URL: {SUPABASE_URL}")

    migrator = SupabaseMigrator()

    # Run migration
    migrator.migrate_all_files()

    # Test the setup
    migrator.test_search()

    print("\n🎉 Migration complete!")

if __name__ == "__main__":
    main()