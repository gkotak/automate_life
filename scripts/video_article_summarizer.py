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

            # Look for video indicators
            has_youtube = 'youtube.com' in response.text or 'youtu.be' in response.text
            has_video_tag = soup.find('video') is not None
            has_iframe = soup.find('iframe') is not None

            return {
                'title': title,
                'url': url,
                'domain': urlparse(url).netloc,
                'has_video_indicators': has_youtube or has_video_tag or has_iframe,
                'extracted_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'title': f"Article from {urlparse(url).netloc}",
                'url': url,
                'domain': urlparse(url).netloc,
                'has_video_indicators': False,
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
        prompt = f"""
        Analyze this article: {url}

        Create a comprehensive summary with the following structure:
        1. Write a clear, structured summary (max 1000 words) in HTML format
        2. Extract 5-8 key insights as bullet points
        3. If video content exists, identify timestamps with descriptions
        4. List recommended sections for readers

        Please provide a clean, well-formatted response focusing on the content value rather than technical processing details.

        Article metadata: {json.dumps(metadata, indent=2)}

        Return your response in this JSON format:
        {{
            "summary": "HTML formatted summary content",
            "key_insights": ["insight 1", "insight 2", ...],
            "video_timestamps": [{{"time": "MM:SS", "description": "what happens"}}, ...],
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

    def _generate_section_html(self, ai_summary):
        """Generate dynamic HTML sections based on AI summary content"""
        sections = {}

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

        # Generate video timestamps section
        if ai_summary.get('video_timestamps'):
            timestamps_html = '<div class="video-timestamps"><h3>🎥 Key Video Timestamps</h3><ul>'
            for ts in ai_summary['video_timestamps']:
                timestamps_html += f'<li><strong>{ts.get("time", "N/A")}</strong> - {ts.get("description", "No description")}</li>'
            timestamps_html += '</ul></div>'
            sections['TIMESTAMPS_SECTION'] = timestamps_html
        else:
            sections['TIMESTAMPS_SECTION'] = ''

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
        sections = self._generate_section_html(ai_summary)

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

    def _update_index_html(self, new_filename, title):
        """Update index.html with new article (deterministic operation)"""
        index_path = self.html_dir / "index.html"

        if not index_path.exists():
            # Create initial index.html
            index_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Article Summaries Index</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            line-height: 1.6;
            color: #333;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        .article-list {
            list-style: none;
            padding: 0;
        }
        .article-item {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .article-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .article-title {
            font-size: 1.2em;
            font-weight: 600;
            color: #2c3e50;
            text-decoration: none;
            display: block;
            margin-bottom: 8px;
        }
        .article-title:hover {
            color: #3498db;
        }
        .article-description {
            color: #666;
            font-size: 0.9em;
        }
        .total-count {
            color: #666;
            font-style: italic;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <h1>Article Summaries</h1>
    <p class="total-count">Total articles: 0</p>
    <ul class="article-list">
    </ul>
</body>
</html>"""
            with open(index_path, 'w') as f:
                f.write(index_content)

        # Read current index
        with open(index_path, 'r') as f:
            content = f.read()

        # Parse and update
        soup = BeautifulSoup(content, 'html.parser')
        article_list = soup.find('ul', class_='article-list')

        # Create new article item
        new_item = soup.new_tag('li', **{'class': 'article-item'})

        title_link = soup.new_tag('a', href=new_filename, **{'class': 'article-title'})
        title_link.string = title

        description = soup.new_tag('p', **{'class': 'article-description'})
        description.string = f"Generated on {datetime.now().strftime('%B %d, %Y')}"

        new_item.append(title_link)
        new_item.append(description)

        # Insert at the beginning (reverse chronological order)
        if article_list.find('li'):
            article_list.insert(0, new_item)
        else:
            article_list.append(new_item)

        # Update count
        count_p = soup.find('p', class_='total-count')
        current_count = len(article_list.find_all('li'))
        count_p.string = f"Total articles: {current_count}"

        # Write back
        with open(index_path, 'w') as f:
            f.write(str(soup))

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
        self._update_index_html(filename, metadata['title'])

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