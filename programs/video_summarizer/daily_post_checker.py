#!/usr/bin/env python3
"""
Daily Post Checker
Monitors platform URLs for new posts and automatically runs video summarizer
"""

import os
import sys
import json
import subprocess
import requests
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import logging
import warnings
from bs4 import XMLParsedAsHTMLWarning
import feedparser
import email.utils

# Suppress XML parsing warnings since we'll handle them properly
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

class DailyPostChecker:
    def __init__(self, base_dir=None):
        if base_dir is None:
            # Find the project root
            current_dir = Path(__file__).parent
            while current_dir != current_dir.parent:
                if (current_dir / '.git').exists() or (current_dir / 'CLAUDE.md').exists():
                    base_dir = current_dir
                    break
                current_dir = current_dir.parent
            else:
                base_dir = Path(__file__).parent

        self.base_dir = Path(base_dir)
        self.links_file = self.base_dir / "programs" / "video_summarizer" / "newsletter_podcast_links.md"
        self.tracking_file = self.base_dir / "programs" / "video_summarizer" / "processed_posts.json"
        self.logs_dir = self.base_dir / "programs" / "video_summarizer" / "logs"
        self.summarizer_script = self.base_dir / "programs" / "video_summarizer" / "scripts" / "summarize_article.sh"

        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Setup session for web requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def _setup_logging(self):
        """Setup logging to both console and file"""
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = self.logs_dir / f"new_posts_extraction_{timestamp}.log"

        self.logger = logging.getLogger('NewPostsExtractor')
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        # File handler with detailed formatting for post extraction logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - [NEW POSTS] - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Log startup with session info
        self.logger.info("=" * 80)
        self.logger.info(f"NEW POSTS EXTRACTION SESSION STARTED")
        self.logger.info(f"Session Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Log File: {log_file}")
        self.logger.info(f"Looking for posts from last 3 days (since {(datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')})")
        self.logger.info("=" * 80)

    def _load_tracked_posts(self):
        """Load previously processed posts from tracking file"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}

    def _save_tracked_posts(self, tracked_posts):
        """Save processed posts to tracking file"""
        with open(self.tracking_file, 'w') as f:
            json.dump(tracked_posts, f, indent=2)

    def _read_platform_urls(self):
        """Read platform URLs from newsletter_podcast_links.md"""
        self.logger.info(f"📖 Reading platform URLs from: {self.links_file}")

        if not self.links_file.exists():
            self.logger.error(f"❌ Links file not found: {self.links_file}")
            return []

        urls = []
        try:
            with open(self.links_file, 'r') as f:
                content = f.read()

            self.logger.info(f"📄 Links file content length: {len(content)} characters")

            # Parse markdown content to extract URLs
            lines = content.split('\n')
            line_count = 0
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                # Look for markdown links [text](url) or plain URLs
                if 'http' in line:
                    line_count += 1
                    self.logger.info(f"🔍 Line {line_num}: Found potential URL in line: {line[:100]}...")

                    # Extract URLs using simple parsing
                    if '](http' in line:
                        # Markdown format [text](url)
                        start = line.find('](http') + 2
                        end = line.find(')', start)
                        if end > start:
                            url = line[start:end]
                            urls.append(url.strip())
                            self.logger.info(f"✅ Extracted markdown URL: {url.strip()}")
                    elif line.startswith('http'):
                        # Plain URL
                        url = line.split()[0]  # Take first word in case there are spaces
                        urls.append(url.strip())
                        self.logger.info(f"✅ Extracted plain URL: {url.strip()}")
                    elif 'https://' in line or 'http://' in line:
                        # URL somewhere in the line
                        words = line.split()
                        for word in words:
                            if word.startswith(('http://', 'https://')):
                                clean_url = word.strip('()[]')
                                urls.append(clean_url)
                                self.logger.info(f"✅ Extracted inline URL: {clean_url}")

        except Exception as e:
            self.logger.error(f"❌ Error reading links file: {e}")
            return []

        self.logger.info(f"📊 SUMMARY: Found {len(urls)} platform URLs to monitor from {line_count} lines")
        for i, url in enumerate(urls, 1):
            self.logger.info(f"   {i}. {url}")

        return urls

    def _get_post_hash(self, title, url):
        """Generate a unique hash for a post based on title and URL"""
        content = f"{title}|{url}"
        return hashlib.md5(content.encode()).hexdigest()

    def _is_rss_feed(self, url, response=None):
        """Detect if URL is an RSS/XML feed"""
        # Check URL patterns
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in ['/feed', '/rss', '/atom', '.xml', '.rss']):
            return True

        # Check content-type header if response available
        if response and hasattr(response, 'headers'):
            content_type = response.headers.get('content-type', '').lower()
            if any(feed_type in content_type for feed_type in ['xml', 'rss', 'atom']):
                return True

        return False

    def _detect_platform_type(self, url):
        """Detect the type of platform from URL"""
        domain = urlparse(url).netloc.lower()

        if 'substack.com' in domain:
            return 'substack'
        elif 'medium.com' in domain:
            return 'medium'
        elif 'youtube.com' in domain or 'youtu.be' in domain:
            return 'youtube'
        elif 'ghost.io' in domain or '/ghost/' in url.lower():
            return 'ghost'
        elif 'linkedin.com' in domain:
            return 'linkedin'
        elif 'twitter.com' in domain or 'x.com' in domain:
            return 'twitter'
        else:
            return 'generic'

    def _extract_posts_from_rss_feed(self, url):
        """Extract posts from RSS/Atom feed using feedparser"""
        self.logger.info(f"🔍 Parsing RSS/XML feed content...")

        try:
            # Use feedparser to parse the RSS/Atom feed
            feed = feedparser.parse(url)

            if feed.bozo:
                self.logger.warning(f"⚠️ Feed parsing warning: {feed.bozo_exception}")

            posts = []
            self.logger.info(f"📋 Found {len(feed.entries)} entries in RSS feed")

            for entry in feed.entries:
                # Extract title
                title = entry.get('title', 'No title')

                # Extract link
                link = entry.get('link', '')

                # Extract published date
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'published'):
                    try:
                        # Try to parse various date formats
                        published = datetime(*email.utils.parsedate(entry.published)[:6])
                    except:
                        pass

                # Extract description/summary
                description = entry.get('summary', entry.get('description', ''))

                if title and link:
                    posts.append({
                        'title': title,
                        'url': link,
                        'platform': 'rss_feed',
                        'published': published,
                        'description': description[:200] + '...' if len(description) > 200 else description
                    })
                    self.logger.info(f"   📝 RSS Entry: {title[:80]}... -> {link}")

            self.logger.info(f"📊 RSS extraction complete: {len(posts)} posts found from {len(feed.entries)} entries")
            return posts

        except Exception as e:
            self.logger.error(f"❌ Error parsing RSS feed {url}: {e}")
            return []

    def _extract_posts_from_feed(self, url, platform_type):
        """Extract recent posts from a platform feed/page"""
        self.logger.info(f"🌐 Fetching content from: {url}")
        self.logger.info(f"🏷️ Platform type: {platform_type}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.logger.info(f"✅ Successfully fetched content (Status: {response.status_code}, Size: {len(response.content)} bytes)")

            # Check if this is an RSS/XML feed
            if self._is_rss_feed(url, response):
                self.logger.info(f"🔍 Detected RSS/XML feed, using feedparser...")
                return self._extract_posts_from_rss_feed(url)

            # Use appropriate parser based on content type
            content_type = response.headers.get('content-type', '').lower()
            if 'xml' in content_type:
                self.logger.info(f"🔍 Using XML parser for content-type: {content_type}")
                soup = BeautifulSoup(response.content, 'xml')
            else:
                self.logger.info(f"🔍 Using HTML parser for content-type: {content_type}")
                soup = BeautifulSoup(response.content, 'html.parser')

            posts = []

            if platform_type == 'substack':
                self.logger.info("🔍 Parsing Substack content for post links...")
                # Look for Substack post links
                post_links = soup.find_all('a', href=True)
                self.logger.info(f"📋 Found {len(post_links)} total links on page")

                substack_post_count = 0
                for link in post_links:
                    href = link.get('href')
                    if href and '/p/' in href:
                        # This is likely a post link
                        title = link.get_text().strip()
                        if title and len(title) > 10:  # Filter out short/empty titles
                            substack_post_count += 1
                            full_url = urljoin(url, href)
                            posts.append({
                                'title': title,
                                'url': full_url,
                                'platform': 'substack'
                            })
                            self.logger.info(f"   📝 Post {substack_post_count}: {title[:80]}... -> {full_url}")

                self.logger.info(f"📊 Substack extraction complete: {len(posts)} posts found from {len(post_links)} total links")

            elif platform_type == 'medium':
                # Look for Medium article links
                article_links = soup.find_all('a', href=True)
                for link in article_links:
                    href = link.get('href')
                    if href and ('/@' in href or '/p/' in href or 'medium.com' in href):
                        title = link.get_text().strip()
                        if title and len(title) > 10:
                            full_url = urljoin(url, href)
                            posts.append({
                                'title': title,
                                'url': full_url,
                                'platform': 'medium'
                            })

            elif platform_type == 'youtube':
                # Look for YouTube video links
                video_links = soup.find_all('a', href=True)
                for link in video_links:
                    href = link.get('href')
                    if href and ('/watch?v=' in href or '/shorts/' in href):
                        title = link.get('title') or link.get_text().strip()
                        if title and len(title) > 5:
                            full_url = urljoin('https://youtube.com', href)
                            posts.append({
                                'title': title,
                                'url': full_url,
                                'platform': 'youtube'
                            })

            else:
                # Generic approach - look for article-like links
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href')
                    title = link.get_text().strip()
                    if (href and title and len(title) > 10 and
                        not any(skip in href.lower() for skip in ['javascript:', 'mailto:', '#', 'about', 'contact'])):
                        full_url = urljoin(url, href)
                        posts.append({
                            'title': title,
                            'url': full_url,
                            'platform': 'generic'
                        })

            # Remove duplicates and sort by title length (longer titles often more relevant)
            seen_urls = set()
            unique_posts = []
            for post in posts:
                if post['url'] not in seen_urls:
                    seen_urls.add(post['url'])
                    unique_posts.append(post)

            # Limit to most recent/relevant posts
            unique_posts.sort(key=lambda x: len(x['title']), reverse=True)
            return unique_posts[:10]  # Return top 10 posts

        except Exception as e:
            self.logger.warning(f"Error extracting posts from {url}: {e}")
            return []

    def _is_recent_post(self, post_url, published_date=None):
        """Check if a post appears to be recent (within last 3 days)"""
        self.logger.info(f"📅 Checking if post is recent (last 3 days): {post_url}")

        # If we have a published date from RSS feed, use it directly
        if published_date:
            days_ago = (datetime.now() - published_date).days
            is_recent = days_ago <= 3
            self.logger.info(f"   📅 Using RSS published date: {published_date.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"   📊 Days ago: {days_ago}, Recent (≤3 days): {is_recent}")
            return is_recent

        try:
            response = self.session.get(post_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for date indicators in meta tags, time elements, or text
            date_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="date"]',
                'time[datetime]',
                '.date',
                '.published',
                '.post-date'
            ]

            self.logger.info(f"🔍 Searching for date indicators using {len(date_selectors)} selectors...")

            for selector in date_selectors:
                elements = soup.select(selector)
                if elements:
                    self.logger.info(f"   Found {len(elements)} elements with selector '{selector}'")

                for element in elements:
                    date_str = element.get('content') or element.get('datetime') or element.get_text()
                    if date_str:
                        self.logger.info(f"   📝 Found date string: '{date_str[:50]}...' from selector '{selector}'")

                        try:
                            # Try to parse various date formats
                            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%B %d, %Y', '%d %B %Y']:
                                try:
                                    post_date = datetime.strptime(date_str[:19], fmt)
                                    days_ago = (datetime.now() - post_date).days
                                    is_recent = days_ago <= 3

                                    self.logger.info(f"   ✅ Successfully parsed date: {post_date.strftime('%Y-%m-%d %H:%M:%S')}")
                                    self.logger.info(f"   📊 Days ago: {days_ago}, Recent (≤3 days): {is_recent}")

                                    return is_recent
                                except ValueError:
                                    continue
                        except Exception as parse_error:
                            self.logger.warning(f"   ⚠️ Error parsing date '{date_str}': {parse_error}")
                            continue

            # If no date found, assume it might be recent
            self.logger.info("   🤷 No valid date found, assuming post is recent")
            return True

        except Exception as e:
            self.logger.warning(f"❌ Error checking post date for {post_url}: {e}")
            return True  # Assume recent if we can't determine

    def _run_video_summarizer(self, post_url):
        """Run the video summarizer script on a new post"""
        try:
            self.logger.info(f"🚀 Running video summarizer for: {post_url}")

            # Check if summarizer script exists
            if not self.summarizer_script.exists():
                self.logger.error(f"Summarizer script not found: {self.summarizer_script}")
                return False

            # Run the summarizer script
            result = subprocess.run([
                str(self.summarizer_script),
                post_url
            ], capture_output=True, text=True, timeout=300, cwd=self.base_dir)

            if result.returncode == 0:
                self.logger.info(f"✅ Successfully processed: {post_url}")
                self.logger.info(f"Output: {result.stdout.strip()}")
                return True
            else:
                self.logger.error(f"❌ Summarizer failed for {post_url}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ Summarizer timed out for {post_url}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error running summarizer for {post_url}: {e}")
            return False

    def check_for_new_posts(self):
        """Main method to check all platforms for new posts"""
        self.logger.info("🔍 Starting daily post check...")

        # Load tracking data
        tracked_posts = self._load_tracked_posts()
        self.logger.info(f"📋 Loaded {len(tracked_posts)} previously tracked posts")

        new_posts_found = 0
        processed_posts = 0
        total_posts_checked = 0

        # Read platform URLs
        platform_urls = self._read_platform_urls()

        if not platform_urls:
            self.logger.warning("❌ No platform URLs found to monitor")
            return

        self.logger.info(f"🚀 Beginning extraction from {len(platform_urls)} platforms...")

        for platform_num, platform_url in enumerate(platform_urls, 1):
            self.logger.info("=" * 60)
            self.logger.info(f"📡 PLATFORM {platform_num}/{len(platform_urls)}: {platform_url}")

            # Detect platform type
            platform_type = self._detect_platform_type(platform_url)
            self.logger.info(f"🏷️ Platform type: {platform_type}")

            # Extract posts from the platform
            posts = self._extract_posts_from_feed(platform_url, platform_type)
            self.logger.info(f"📊 Platform {platform_num} results: {len(posts)} posts found")

            if not posts:
                self.logger.info("   ℹ️ No posts found on this platform, moving to next...")
                continue

            for post_num, post in enumerate(posts, 1):
                self.logger.info(f"   🔍 POST {post_num}/{len(posts)}: {post['title'][:60]}...")
                total_posts_checked += 1

                post_hash = self._get_post_hash(post['title'], post['url'])
                self.logger.info(f"   🆔 Post hash: {post_hash}")

                # Check if we've already processed this post
                if post_hash not in tracked_posts:
                    self.logger.info("   ✅ Post is NEW (not in tracking database)")

                    # Check if it's a recent post (pass published date if available from RSS)
                    published_date = post.get('published') if isinstance(post, dict) else None
                    if self._is_recent_post(post['url'], published_date):
                        self.logger.info(f"   ✅ Post is RECENT (within last 3 days)")
                        self.logger.info(f"   📝 NEW POST QUALIFIED FOR PROCESSING: {post['title']}")
                        new_posts_found += 1

                        # Run video summarizer
                        self.logger.info(f"   🚀 Launching video summarizer for post...")
                        if self._run_video_summarizer(post['url']):
                            processed_posts += 1
                            # Mark as processed
                            tracked_posts[post_hash] = {
                                'title': post['title'],
                                'url': post['url'],
                                'platform': post['platform'],
                                'processed_at': datetime.now().isoformat(),
                                'source_feed': platform_url,
                                'published_date': published_date.isoformat() if published_date else None
                            }
                            self.logger.info(f"   ✅ POST SUCCESSFULLY PROCESSED AND TRACKED")
                        else:
                            self.logger.warning(f"   ❌ Failed to process post: {post['title']}")
                    else:
                        self.logger.info(f"   ⏰ Post is OLD (older than 3 days), skipping...")
                else:
                    self.logger.info(f"   ♻️ Post already processed (found in tracking database), skipping...")

        # Clean up old tracking entries (older than 30 days)
        self.logger.info("🧹 Cleaning up old tracking entries (>30 days)...")
        cutoff_date = datetime.now() - timedelta(days=30)
        cleaned_tracked = {}
        removed_count = 0

        for post_hash, post_data in tracked_posts.items():
            try:
                processed_at = datetime.fromisoformat(post_data.get('processed_at', ''))
                if processed_at > cutoff_date:
                    cleaned_tracked[post_hash] = post_data
                else:
                    removed_count += 1
                    self.logger.info(f"   🗑️ Removing old entry: {post_data.get('title', 'Unknown')[:40]}...")
            except:
                # Keep entries without valid dates
                cleaned_tracked[post_hash] = post_data

        self.logger.info(f"   📊 Cleanup complete: Removed {removed_count} old entries")

        # Save updated tracking data
        self._save_tracked_posts(cleaned_tracked)
        self.logger.info(f"💾 Saved {len(cleaned_tracked)} posts to tracking database")

        # Final Summary
        self.logger.info("=" * 80)
        self.logger.info("📊 FINAL SESSION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"🌐 Platforms checked: {len(platform_urls)}")
        self.logger.info(f"📝 Total posts found: {total_posts_checked}")
        self.logger.info(f"🆕 New posts discovered: {new_posts_found}")
        self.logger.info(f"✅ Successfully processed: {processed_posts}")
        self.logger.info(f"💾 Total tracked posts: {len(cleaned_tracked)}")
        self.logger.info(f"🕐 Session completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if processed_posts > 0:
            self.logger.info(f"🎉 SUCCESS: Processed {processed_posts} new posts!")
        else:
            self.logger.info("✨ No new posts to process today")

        self.logger.info("=" * 80)

def main():
    """Main entry point"""
    checker = DailyPostChecker()

    try:
        checker.check_for_new_posts()
    except KeyboardInterrupt:
        checker.logger.info("Process interrupted by user")
    except Exception as e:
        checker.logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()