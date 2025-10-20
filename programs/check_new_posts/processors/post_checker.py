#!/usr/bin/env python3
"""
Manual Post Checker - Refactored version using BaseProcessor
Manually checks platform URLs for new posts and outputs URLs for processing
"""

import json
import time
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning
import feedparser
import email.utils
from dotenv import load_dotenv
from supabase import create_client, Client

# Import our base class and config
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from common.base import BaseProcessor
from common.config import Config
from common.url_utils import normalize_url, generate_post_id

# Load environment variables
root_env = Path(__file__).parent.parent.parent.parent / '.env.local'
load_dotenv(root_env)

# Suppress XML parsing warnings since we'll handle them properly
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class PostChecker(BaseProcessor):
    def __init__(self):
        super().__init__("post_checker")

        # Setup specific directories for this processor
        self.summarizer_script = self.base_dir / "programs" / "article_summarizer" / "scripts" / "summarize_article.sh"

        # Initialize Supabase client (required - database-only approach, no JSON fallback)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env.local")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.logger.info("✅ Connected to Supabase")

        # Fallback markdown file
        self.links_file = self.base_dir / "programs" / "check_new_posts" / "newsletter_podcast_links.md"

    def _load_tracked_posts(self):
        """Load previously processed posts from Supabase content_queue table"""
        try:
            # Query all articles from content_queue
            result = self.supabase.table('content_queue').select('*').eq(
                'content_type', 'article'
            ).execute()

            # Convert to dict format with post_hash as key (for backward compatibility)
            tracked_posts = {}
            for row in result.data:
                # Generate post hash from URL
                post_hash = generate_post_id(row['url'], row['url'])

                tracked_posts[post_hash] = {
                    'title': row['title'],
                    'url': row['url'],
                    'platform': row['platform'],
                    'found_at': row['found_at'],
                    'source_feed': row['source_feed'],
                    'published_date': row['published_date'],
                    'status': row['status']
                }

            self.logger.info(f"📂 Loaded {len(tracked_posts)} posts from database")
            return tracked_posts

        except Exception as e:
            self.logger.error(f"❌ Error loading posts from database: {e}")
            self.logger.error("💥 Database is required - cannot continue without it")
            raise

    def _save_tracked_posts(self, tracked_posts):
        """Save processed posts to Supabase content_queue table"""
        try:
            # Convert tracked_posts dict to list of records for upserting
            # Use a dict to deduplicate by URL (in case multiple post_hashes map to same URL)
            records_dict = {}
            for post_hash, post in tracked_posts.items():
                url = post['url']

                # Skip if we already have this URL
                if url in records_dict:
                    continue

                # Extract channel info from URL or source_feed
                channel_title, channel_url = self._extract_channel_info(url, post.get('source_feed'))

                records_dict[url] = {
                    'url': url,
                    'title': post['title'],
                    'content_type': 'article',
                    'channel_title': channel_title,
                    'channel_url': channel_url,
                    'video_url': None,  # Will be populated by article_summarizer
                    'platform': post.get('platform', 'generic'),
                    'source_feed': post.get('source_feed'),
                    'found_at': post.get('found_at'),
                    'published_date': post.get('published_date'),
                    'status': post.get('status', 'discovered')
                }

            # Convert to list
            records = list(records_dict.values())

            # Batch upsert to Supabase (upsert based on unique URL)
            if records:
                self.supabase.table('content_queue').upsert(
                    records,
                    on_conflict='url'
                ).execute()

            self.logger.info(f"💾 Saved {len(tracked_posts)} posts to database")

        except Exception as e:
            self.logger.error(f"❌ Error saving posts to database: {e}")
            raise

    def _extract_channel_info(self, url: str, source_feed: str = None):
        """Extract channel title and URL from article URL"""
        # Common patterns
        if 'stratechery.com' in url:
            return 'Stratechery', 'https://stratechery.com'
        elif 'lennysnewsletter.com' in url:
            return "Lenny's Newsletter", 'https://www.lennysnewsletter.com'
        elif 'creatoreconomy.so' in url:
            return 'Creator Economy', 'https://creatoreconomy.so'
        elif 'akashbajwa.co' in url:
            return 'Akash Bajwa', 'https://www.akashbajwa.co'

        # Try to extract from source_feed if provided
        if source_feed:
            parsed = urlparse(source_feed)
            domain = parsed.netloc.replace('www.', '')
            return domain, f"https://{parsed.netloc}"

        # Try to extract domain as fallback
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain, f"https://{parsed.netloc}"
        except:
            return None, None

    def _read_platform_urls(self):
        """Read platform URLs from Supabase or fallback to markdown file"""

        # Try Supabase first
        if self.supabase:
            try:
                self.logger.info("📖 Reading platform URLs from Supabase content_sources table")

                # Query active sources
                response = self.supabase.table('content_sources').select('*').eq('is_active', True).execute()

                if response.data:
                    urls = [row['url'] for row in response.data]
                    self.logger.info(f"✅ Loaded {len(urls)} active URLs from Supabase")

                    # Log source types breakdown
                    source_types = {}
                    for row in response.data:
                        source_type = row.get('source_type', 'unknown')
                        source_types[source_type] = source_types.get(source_type, 0) + 1

                    for source_type, count in source_types.items():
                        self.logger.info(f"   • {source_type}: {count}")

                    return urls
                else:
                    self.logger.warning("⚠️ No active content sources found in Supabase")
                    return []

            except Exception as e:
                self.logger.error(f"❌ Error reading from Supabase: {e}")
                self.logger.warning("⚠️ Falling back to markdown file")
                # Fall through to markdown fallback

        # Fallback to markdown file
        if not hasattr(self, 'links_file') or not self.links_file:
            self.logger.error("❌ No Supabase connection and no fallback file configured")
            return []

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
        """
        Generate a unique hash for a post based on title and normalized base URL.
        This prevents duplicate entries when URLs have different parameters.
        """
        return generate_post_id(title, url)

    def _is_rss_feed(self, url, response=None):
        """Detect if URL is an RSS/XML feed"""
        url_lower = url.lower()
        patterns = Config.get_platform_patterns()['rss_feed']

        if any(pattern in url_lower for pattern in patterns):
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
        patterns = Config.get_platform_patterns()

        for platform, platform_patterns in patterns.items():
            if platform == 'rss_feed':
                continue  # Handle RSS feeds separately

            for pattern in platform_patterns:
                if pattern in domain or pattern in url.lower():
                    return platform

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
            response = self.safe_request(url, timeout=Config.DEFAULT_TIMEOUT)
            if not response:
                return []

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
                post_links = soup.find_all('a', href=True)
                self.logger.info(f"📋 Found {len(post_links)} total links on page")

                substack_post_count = 0
                for link in post_links:
                    href = link.get('href')
                    if href and '/p/' in href:
                        title = link.get_text().strip()
                        if title and len(title) > 10:
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

            # Remove duplicates and sort by title length
            seen_urls = set()
            unique_posts = []
            for post in posts:
                if post['url'] not in seen_urls:
                    seen_urls.add(post['url'])
                    unique_posts.append(post)

            # Limit to most recent/relevant posts
            unique_posts.sort(key=lambda x: len(x['title']), reverse=True)
            return unique_posts[:Config.RSS_FEED_ENTRY_LIMIT]

        except Exception as e:
            self.logger.warning(f"Error extracting posts from {url}: {e}")
            return []

    def _is_recent_post(self, post_url, published_date=None):
        """Check if a post appears to be recent (within last 3 days)"""
        self.logger.info(f"📅 Checking if post is recent (last {Config.RSS_POST_RECENCY_DAYS} days): {post_url}")

        # If we have a published date from RSS feed, use it directly
        if published_date:
            days_ago = (datetime.now() - published_date).days
            is_recent = days_ago <= Config.RSS_POST_RECENCY_DAYS
            self.logger.info(f"   📅 Using RSS published date: {published_date.strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info(f"   📊 Days ago: {days_ago}, Recent (≤{Config.RSS_POST_RECENCY_DAYS} days): {is_recent}")
            return is_recent

        try:
            response = self.safe_request(post_url, timeout=Config.SHORT_TIMEOUT)
            if not response:
                return True  # Assume recent if we can't determine

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
                                    is_recent = days_ago <= Config.RSS_POST_RECENCY_DAYS

                                    self.logger.info(f"   ✅ Successfully parsed date: {post_date.strftime('%Y-%m-%d %H:%M:%S')}")
                                    self.logger.info(f"   📊 Days ago: {days_ago}, Recent (≤{Config.RSS_POST_RECENCY_DAYS} days): {is_recent}")

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

    def _show_new_posts_summary(self, new_posts):
        """Show summary of new posts found (replaces markdown file generation)"""
        try:
            if not new_posts:
                return None

            self.logger.info(f"📋 Found {len(new_posts)} new posts:")
            self.logger.info("=" * 80)

            for i, post in enumerate(new_posts, 1):
                published = post.get('published_date', 'Unknown')
                if published and published != 'Unknown':
                    published = published[:10]  # Just the date part

                self.logger.info(f"{i}. {post['title'][:70]}...")
                self.logger.info(f"   📅 {published} | 🌐 {post['platform']} | 🔗 {post.get('source_feed', 'N/A')}")

            self.logger.info("=" * 80)
            self.logger.info("💡 To process these posts, use:")
            self.logger.info("   python3 scripts/post_manager.py list --status=discovered")
            self.logger.info("   python3 scripts/post_manager.py process <post_ids>")
            self.logger.info("   python3 scripts/post_manager.py bulk --status=discovered --action=process --limit=5")

            return f"Found {len(new_posts)} new posts"

        except Exception as e:
            self.logger.error(f"❌ Error showing post summary: {e}")
            return None

    def check_for_new_posts(self):
        """Main method to check all platforms for new posts"""
        self.logger.info("🔍 Starting manual post check...")

        # Load tracking data
        tracked_posts = self._load_tracked_posts()
        self.logger.info(f"📋 Loaded {len(tracked_posts)} previously tracked posts")

        new_posts_found = 0
        total_posts_checked = 0
        new_posts_for_processing = []

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

                    # Check if it's a recent post
                    published_date = post.get('published') if isinstance(post, dict) else None
                    if self._is_recent_post(post['url'], published_date):
                        self.logger.info(f"   ✅ Post is RECENT (within last {Config.RSS_POST_RECENCY_DAYS} days)")
                        self.logger.info(f"   📝 NEW POST QUALIFIED FOR PROCESSING: {post['title']}")
                        new_posts_found += 1

                        # Add to processing list
                        new_posts_for_processing.append({
                            'title': post['title'],
                            'url': post['url'],
                            'platform': post['platform'],
                            'source_feed': platform_url,
                            'published_date': published_date.isoformat() if published_date else None,
                            'post_hash': post_hash
                        })

                        # Mark as found (but not processed)
                        tracked_posts[post_hash] = {
                            'title': post['title'],
                            'url': post['url'],
                            'platform': post['platform'],
                            'found_at': datetime.now().isoformat(),
                            'source_feed': platform_url,
                            'published_date': published_date.isoformat() if published_date else None,
                            'status': 'discovered'
                        }
                        self.logger.info(f"   📋 POST ADDED TO PROCESSING QUEUE")
                    else:
                        self.logger.info(f"   ⏰ Post is OLD (older than {Config.RSS_POST_RECENCY_DAYS} days), skipping...")
                else:
                    self.logger.info(f"   ♻️ Post already processed (found in tracking database), skipping...")

        # Clean up old tracking entries
        self.logger.info(f"🧹 Cleaning up old tracking entries (>{Config.TRACKING_CLEANUP_DAYS} days)...")
        cutoff_date = datetime.now() - timedelta(days=Config.TRACKING_CLEANUP_DAYS)
        cleaned_tracked = {}
        removed_count = 0

        for post_hash, post_data in tracked_posts.items():
            try:
                processed_at = datetime.fromisoformat(post_data.get('found_at', post_data.get('processed_at', '')))
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

        # Show summary of new posts (replaces markdown file generation)
        output_summary = None
        if new_posts_for_processing:
            output_summary = self._show_new_posts_summary(new_posts_for_processing)

        # Log session summary
        self.log_session_summary(
            platforms_checked=len(platform_urls),
            total_posts_found=total_posts_checked,
            new_posts_discovered=new_posts_found,
            total_tracked_posts=len(cleaned_tracked),
            summary=output_summary or "No new posts found"
        )

        if new_posts_found > 0:
            self.logger.info(f"🎉 SUCCESS: Found {new_posts_found} new posts!")
        else:
            self.logger.info("✨ No new posts found today")

        return output_summary


def main():
    """Main entry point"""
    checker = PostChecker()

    try:
        summary = checker.check_for_new_posts()
        # Print summary to stdout for shell script to capture (if any new posts found)
        if summary:
            print(summary)
    except KeyboardInterrupt:
        checker.logger.info("Process interrupted by user")
    except Exception as e:
        checker.logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()