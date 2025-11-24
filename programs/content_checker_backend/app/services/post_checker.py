"""
Post checking service - refactored for API usage
Scans content_sources table for new newsletter/blog posts
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import feedparser
import email.utils
from supabase import create_client, Client

from core.config import Config
# REMOVED: YouTube discovery moved to Article Processor
# from core.youtube_discovery import YouTubeDiscoveryService


class PostCheckerService:
    """Service for checking content sources for new posts/articles"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.logger.info("Connected to Supabase")

        # Setup HTTP session
        self.session = requests.Session()
        self.session.headers.update(Config.get_default_headers())

        # REMOVED: YouTube discovery service (moved to Article Processor)
        # self.youtube_discovery = YouTubeDiscoveryService(self.logger)

    async def check_for_new_posts(self, user_id: str) -> Dict:
        """
        Check content_sources for new posts/articles for a specific user

        Args:
            user_id: UUID of the user to check sources for

        Returns:
            Dictionary with results including newly_discovered_ids
        """
        self.logger.info(f"Starting post check for user: {user_id}...")

        # Load content sources from database (filtered by user_id)
        sources = self._load_content_sources(user_id)

        if not sources:
            self.logger.warning(f"No active content sources found for user: {user_id}")
            return {
                "new_posts_found": 0,
                "total_sources_checked": 0,
                "message": "No active content sources found",
                "newly_discovered_ids": []
            }

        self.logger.info(f"Processing {len(sources)} content sources for user: {user_id}...")

        new_posts_found = 0
        total_sources_checked = 0
        newly_discovered_ids = []

        # Load existing posts from database (filtered by user_id)
        existing_urls = self._get_existing_post_urls(user_id)

        # Process each source
        for source in sources:
            source_url = source['url']
            source_type = source.get('source_type', 'newsletter')  # Default to 'newsletter' if not set
            self.logger.info(f"Checking source: {source_url} (type: {source_type})")
            total_sources_checked += 1

            # Detect platform type
            platform_type = self._detect_platform_type(source_url)

            # Extract posts from source, using the stored source_type
            posts = self._extract_posts_from_feed(source_url, platform_type, user_source_type=source_type)

            if not posts:
                self.logger.info(f"No posts found from {source_url}")
                continue

            self.logger.info(f"Found {len(posts)} posts from {source_url}, checking for new content...")

            # Check each post
            for post in posts:
                post_url = post['url']

                # Check if already tracked
                if post_url in existing_urls:
                    self.logger.debug(f"Skipping already tracked: {post.get('title', '')[:60]}")
                    continue

                # Check if recent
                published_date = post.get('published')
                if not self._is_recent_post(post_url, published_date):
                    if published_date:
                        days_ago = (datetime.now() - published_date).days
                        self.logger.debug(f"Skipping old post ({days_ago} days ago): {post.get('title', '')[:60]}")
                    else:
                        self.logger.debug(f"Skipping post (no date or too old): {post.get('title', '')[:60]}")
                    continue

                self.logger.info(f"New post found: {post['title']}")
                new_posts_found += 1

                # REMOVED: YouTube discovery now happens in Article Processor
                # self._discover_youtube_url_for_post(post, source_url)

                # Save to database and get the ID
                post_id = self._save_post_to_queue(post, source_url, user_id)
                if post_id:
                    newly_discovered_ids.append(post_id)

        message = f"Found {new_posts_found} new posts from {total_sources_checked} sources"
        self.logger.info(f"Check complete: {message}")

        return {
            "new_posts_found": new_posts_found,
            "total_sources_checked": total_sources_checked,
            "message": message,
            "newly_discovered_ids": newly_discovered_ids
        }

    def _load_content_sources(self, user_id: str) -> List[Dict]:
        """Load active content sources from Supabase for a specific user"""
        try:
            result = self.supabase.table('content_sources').select('*').eq(
                'user_id', user_id
            ).eq(
                'is_active', True
            ).execute()

            self.logger.info(f"Loaded {len(result.data)} active content sources for user: {user_id}")
            return result.data

        except Exception as e:
            self.logger.error(f"Error loading content sources: {e}")
            return []

    def _get_existing_post_urls(self, user_id: str) -> set:
        """Get set of existing post URLs from content_queue for a specific user (RSS feed source only)"""
        try:
            result = self.supabase.table('content_queue').select('url').eq(
                'user_id', user_id
            ).eq(
                'source', 'rss_feed'
            ).execute()

            return {row['url'] for row in result.data}

        except Exception as e:
            self.logger.error(f"Error loading existing posts: {e}")
            return set()

    def _detect_platform_type(self, url: str) -> str:
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

    def _is_rss_feed(self, url: str, response=None) -> bool:
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

    def _discover_rss_feed(self, url: str, response) -> Optional[str]:
        """
        Auto-discover RSS feed URL from HTML page
        Looks for <link> tags in the HTML head that point to RSS/Atom feeds
        """
        try:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for RSS/Atom feed links in <head>
            feed_link_types = [
                'application/rss+xml',
                'application/atom+xml',
                'application/xml'
            ]

            for link in soup.find_all('link', type=feed_link_types):
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    feed_url = urljoin(url, href)
                    self.logger.info(f"Found RSS feed link: {feed_url}")
                    return feed_url

            # Fallback: try common RSS feed patterns
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            common_feed_paths = ['/feed', '/rss', '/feed.xml', '/rss.xml', '/atom.xml']

            for feed_path in common_feed_paths:
                potential_feed = base_url + feed_path
                try:
                    feed_response = self.session.head(potential_feed, timeout=Config.SHORT_TIMEOUT)
                    if feed_response.status_code == 200:
                        content_type = feed_response.headers.get('content-type', '').lower()
                        if any(t in content_type for t in ['xml', 'rss', 'atom']):
                            self.logger.info(f"Found RSS feed via common path: {potential_feed}")
                            return potential_feed
                except:
                    continue

            return None

        except Exception as e:
            self.logger.warning(f"Error discovering RSS feed: {e}")
            return None

    def _extract_posts_from_feed(self, url: str, platform_type: str, user_source_type: str = 'newsletter') -> List[Dict]:
        """Extract posts from a content source (RSS feed or webpage)

        Args:
            url: URL of the feed or webpage
            platform_type: Detected platform type
            user_source_type: User's intended source type ('newsletter' or 'podcast')
        """
        try:
            # Check if this is a PocketCasts channel URL
            if 'pocketcasts.com/podcast/' in url:
                self.logger.warning(f"⚠️ PocketCasts channel URLs are not currently supported in post_checker.")
                self.logger.warning(f"   Please use the podcast's RSS feed URL instead.")
                self.logger.warning(f"   Tip: Most podcasts have an RSS feed you can find via their website or podcast directories.")
                return []

            response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
            response.raise_for_status()

            # Check if this is an RSS/XML feed
            if self._is_rss_feed(url, response):
                return self._extract_posts_from_rss_feed(url, user_source_type)

            # Try to auto-discover RSS feed from HTML page
            discovered_feed_url = self._discover_rss_feed(url, response)
            if discovered_feed_url:
                self.logger.info(f"Auto-discovered RSS feed: {discovered_feed_url}")
                return self._extract_posts_from_rss_feed(discovered_feed_url, user_source_type)

            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            posts = []

            if platform_type == 'substack':
                # Look for article links in main content area, not navigation
                # Substack typically has articles in <article> or <div class="post"> elements
                main_content = soup.find('main') or soup.find('article') or soup
                post_links = main_content.find_all('a', href=True)

                for link in post_links:
                    href = link.get('href')
                    if not href or '/p/' not in href:
                        continue

                    title = link.get_text().strip()

                    # Filter out navigation/footer links
                    if not title or len(title) < 15:  # Increased minimum length
                        continue

                    # Skip common non-article patterns
                    skip_patterns = [
                        'privacy', 'terms', 'about', 'subscribe', 'sign in',
                        'log in', 'contact', 'settings', 'archive', 'policy'
                    ]
                    if any(pattern in title.lower() for pattern in skip_patterns):
                        continue

                    # Skip if it looks like a navigation element (parent has nav/footer)
                    parent_classes = ' '.join(link.parent.get('class', [])).lower()
                    if any(nav in parent_classes for nav in ['nav', 'footer', 'header', 'menu', 'sidebar']):
                        continue

                    full_url = urljoin(url, href)
                    posts.append({
                        'title': title,
                        'url': full_url,
                        'platform': 'substack',
                        'published': None
                    })

            elif platform_type == 'medium':
                # Focus on main content area for Medium
                main_content = soup.find('main') or soup.find('article') or soup
                article_links = main_content.find_all('a', href=True)

                for link in article_links:
                    href = link.get('href')
                    if not href or not ('/@' in href or '/p/' in href or 'medium.com' in href):
                        continue

                    title = link.get_text().strip()

                    # Filter out short titles and common non-article patterns
                    if not title or len(title) < 15:
                        continue

                    skip_patterns = [
                        'privacy', 'terms', 'about', 'subscribe', 'sign in',
                        'log in', 'contact', 'settings', 'archive', 'policy'
                    ]
                    if any(pattern in title.lower() for pattern in skip_patterns):
                        continue

                    # Skip navigation elements
                    parent_classes = ' '.join(link.parent.get('class', [])).lower()
                    if any(nav in parent_classes for nav in ['nav', 'footer', 'header', 'menu', 'sidebar']):
                        continue

                    full_url = urljoin(url, href)
                    posts.append({
                        'title': title,
                        'url': full_url,
                        'platform': 'medium',
                        'published': None
                    })

            else:
                # Generic approach - look for article-like links in main content
                main_content = soup.find('main') or soup.find('article') or soup
                links = main_content.find_all('a', href=True)

                skip_href_patterns = [
                    'javascript:', 'mailto:', '#', 'about', 'contact',
                    'privacy', 'terms', 'subscribe', 'login', 'signin'
                ]
                skip_title_patterns = [
                    'privacy', 'terms', 'about', 'subscribe', 'sign in',
                    'log in', 'contact', 'settings', 'archive', 'policy'
                ]

                for link in links:
                    href = link.get('href')
                    title = link.get_text().strip()

                    # Basic validation
                    if not href or not title or len(title) < 15:
                        continue

                    # Skip common non-article patterns
                    if any(skip in href.lower() for skip in skip_href_patterns):
                        continue

                    if any(pattern in title.lower() for pattern in skip_title_patterns):
                        continue

                    # Skip navigation elements
                    parent_classes = ' '.join(link.parent.get('class', [])).lower()
                    if any(nav in parent_classes for nav in ['nav', 'footer', 'header', 'menu', 'sidebar']):
                        continue

                    full_url = urljoin(url, href)
                    posts.append({
                        'title': title,
                        'url': full_url,
                        'platform': 'generic',
                        'published': None
                    })

            # Remove duplicates
            seen_urls = set()
            unique_posts = []
            for post in posts:
                if post['url'] not in seen_urls:
                    seen_urls.add(post['url'])
                    unique_posts.append(post)

            # Limit to most recent posts
            return unique_posts[:Config.RSS_FEED_ENTRY_LIMIT]

        except Exception as e:
            self.logger.warning(f"Error extracting posts from {url}: {e}")
            return []

    def _extract_posts_from_rss_feed(self, url: str, user_source_type: str = 'newsletter') -> List[Dict]:
        """Extract posts from RSS/Atom feed using feedparser

        Args:
            url: RSS feed URL
            user_source_type: User's intended source type ('newsletter' or 'podcast')
        """
        try:
            feed = feedparser.parse(url)

            if feed.bozo:
                self.logger.warning(f"Feed parsing warning: {feed.bozo_exception}")

            # Check if feed contains any audio content (for logging purposes)
            has_audio_content = False
            if feed.entries:
                # Check first few entries for audio enclosures
                for entry in feed.entries[:3]:
                    if hasattr(entry, 'enclosures'):
                        for enclosure in entry.enclosures:
                            if enclosure.get('type', '').startswith('audio/'):
                                has_audio_content = True
                                break
                    if has_audio_content:
                        break

            if has_audio_content:
                self.logger.info(f"Detected RSS feed with audio content (may be podcast or newsletter with audio)")

            posts = []
            for entry in feed.entries:
                # Extract title and link
                title = entry.get('title', 'No title')
                link = entry.get('link', '')

                # Extract published date
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'published'):
                    try:
                        published = datetime(*email.utils.parsedate(entry.published)[:6])
                    except:
                        pass

                # Extract audio enclosure URL for podcasts
                audio_url = None
                duration = None
                if hasattr(entry, 'enclosures'):
                    for enclosure in entry.enclosures:
                        if enclosure.get('type', '').startswith('audio/'):
                            audio_url = enclosure.get('href') or enclosure.get('url')
                            # Try to get duration from itunes:duration
                            if hasattr(entry, 'itunes_duration'):
                                try:
                                    # Duration can be in seconds or HH:MM:SS format
                                    duration_str = entry.itunes_duration
                                    if ':' in duration_str:
                                        parts = duration_str.split(':')
                                        if len(parts) == 3:
                                            duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                                        elif len(parts) == 2:
                                            duration = int(parts[0]) * 60 + int(parts[1])
                                    else:
                                        duration = int(duration_str)
                                except:
                                    pass
                            break

                # Determine URL based on user's intended source type
                # For 'podcast': always prefer audio URL
                # For 'newsletter': prefer webpage link, fallback to audio if no link
                if user_source_type == 'podcast':
                    # User explicitly searched via "Search Podcast" - always use audio
                    if audio_url:
                        link = audio_url
                        self.logger.debug(f"Using audio URL for podcast: {title[:60]}")
                    # If no audio URL for podcast, use link (edge case)
                else:
                    # User searched via "Search Newsletter by URL" - prefer webpage
                    # Only use audio if no webpage link exists
                    if not link and audio_url:
                        link = audio_url
                        self.logger.debug(f"No webpage link found, using audio URL: {title[:60]}")

                # Skip entries without a valid URL
                if not title or not link:
                    self.logger.debug(f"Skipping entry without title or URL: {entry.get('id', 'unknown')}")
                    continue

                post_data = {
                    'title': title,
                    'url': link,
                    'platform': 'podcast_rss' if user_source_type == 'podcast' else 'rss_feed',
                    'published': published,
                    'audio_url': audio_url,
                    'duration': duration
                }
                posts.append(post_data)

            # Extract channel info from feed metadata
            channel_title = feed.feed.get('title', 'Unknown')
            channel_link = feed.feed.get('link', url)

            # Add channel info to each post
            for post in posts:
                post['channel_title'] = channel_title
                post['channel_link'] = channel_link

            return posts[:Config.RSS_FEED_ENTRY_LIMIT]

        except Exception as e:
            self.logger.error(f"Error parsing RSS feed {url}: {e}")
            return []

    def _extract_episodes_from_pocketcasts(self, url: str) -> List[Dict]:
        """Extract podcast episodes from PocketCasts podcast page"""
        try:
            import json
            import re

            self.logger.info(f"Scraping PocketCasts podcast page: {url}")
            response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract podcast title from page
            podcast_title = 'Unknown Podcast'
            title_tag = soup.find('h1')
            if title_tag:
                podcast_title = title_tag.get_text().strip()

            self.logger.info(f"Podcast title: {podcast_title}")

            # Try to find embedded JSON data with episodes
            episodes = []
            scripts = soup.find_all('script', type='application/json')

            for script in scripts:
                if not script.string:
                    continue

                try:
                    data = json.loads(script.string)

                    # Look for episodes in various locations
                    if isinstance(data, dict):
                        props = data.get('props', {})
                        page_props = props.get('pageProps', {})

                        # Try different paths
                        episodes_data = None
                        if 'episodes' in page_props:
                            episodes_data = page_props['episodes']
                        elif 'podcast' in page_props and 'episodes' in page_props['podcast']:
                            episodes_data = page_props['podcast']['episodes']

                        if episodes_data:
                            self.logger.info(f"Found {len(episodes_data)} episodes in JSON data")

                            for ep in episodes_data:
                                # Extract episode details
                                ep_uuid = ep.get('uuid', '')
                                ep_title = ep.get('title', 'Unknown Episode')
                                ep_slug = ep.get('slug', '')
                                podcast_slug = ep.get('podcastSlug', '')
                                podcast_uuid = ep.get('podcastUuid', '')

                                # Build episode URL
                                if podcast_slug and ep_slug and podcast_uuid and ep_uuid:
                                    episode_url = f"https://pocketcasts.com/podcast/{podcast_slug}/{podcast_uuid}/{ep_slug}/{ep_uuid}"
                                else:
                                    episode_url = f"https://pocketcasts.com/episode/{ep_uuid}"

                                # Extract published date
                                published = None
                                if ep.get('published'):
                                    try:
                                        published = datetime.fromisoformat(ep['published'].replace('Z', '+00:00'))
                                    except:
                                        pass

                                # Extract duration
                                duration = ep.get('duration', 0)

                                episodes.append({
                                    'title': ep_title,
                                    'url': episode_url,
                                    'platform': 'pocketcasts',
                                    'published': published,
                                    'audio_url': None,  # PocketCasts doesn't expose direct audio URLs
                                    'duration': duration,
                                    'channel_title': podcast_title,
                                    'channel_link': url
                                })

                            break

                except json.JSONDecodeError:
                    continue

            if not episodes:
                self.logger.warning("No episodes found in PocketCasts page JSON")

            return episodes[:Config.RSS_FEED_ENTRY_LIMIT]

        except Exception as e:
            self.logger.error(f"Error extracting episodes from PocketCasts: {e}")
            return []

    def _is_recent_post(self, post_url: str, published_date: Optional[datetime] = None) -> bool:
        """Check if a post is recent (within last 3 days)"""
        # If we have a published date from RSS feed, use it directly
        if published_date:
            days_ago = (datetime.now() - published_date).days
            return days_ago <= Config.RSS_POST_RECENCY_DAYS

        try:
            response = self.session.get(post_url, timeout=Config.SHORT_TIMEOUT)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for date indicators
            date_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="date"]',
                'time[datetime]',
                '.date',
                '.published',
                '.post-date'
            ]

            for selector in date_selectors:
                elements = soup.select(selector)
                for element in elements:
                    date_str = element.get('content') or element.get('datetime') or element.get_text()
                    if date_str:
                        try:
                            # Try to parse various date formats
                            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%B %d, %Y', '%d %B %Y']:
                                try:
                                    post_date = datetime.strptime(date_str[:19], fmt)
                                    days_ago = (datetime.now() - post_date).days
                                    return days_ago <= Config.RSS_POST_RECENCY_DAYS
                                except ValueError:
                                    continue
                        except Exception:
                            continue

            # If no date found, assume it might be recent
            return True

        except Exception as e:
            self.logger.warning(f"Error checking post date for {post_url}: {e}")
            return True  # Assume recent if we can't determine

    def _save_post_to_queue(self, post: Dict, source_feed: str, user_id: str) -> Optional[str]:
        """Save post to content_queue table with user_id and organization_id"""
        try:
            # Get user's organization_id from the users table
            user_result = self.supabase.table('users').select('organization_id').eq('id', user_id).execute()

            if not user_result.data or len(user_result.data) == 0:
                self.logger.error(f"User {user_id} not found in users table")
                return None

            organization_id = user_result.data[0]['organization_id']

            # Determine content_type based on the ACTUAL URL we're saving
            # Check if URL contains an audio file extension (even with query params)
            # e.g., "episode.mp3?tracking=xyz" should be detected as audio
            from urllib.parse import urlparse
            url_lower = post['url'].lower()
            parsed_url = urlparse(url_lower)
            url_path = parsed_url.path  # Gets path without query params
            is_audio_file = any(ext in url_path for ext in ['.mp3', '.m4a', '.wav', '.ogg', '.aac', '.flac'])

            # Content type describes what the URL points to:
            # - 'podcast/audio' if URL is an audio file
            # - 'article' if URL is a webpage
            content_type = 'podcast/audio' if is_audio_file else 'article'

            # Extract channel title from RSS metadata
            channel_title = post.get('channel_title')
            if not channel_title:
                # Fallback: extract from URL (best effort)
                channel_title, _ = self._extract_channel_info(post['url'], source_feed)

            # IMPORTANT: content_queue is populated from multiple sources (RSS feeds AND PocketCasts history)
            # channel_title is duplicated (not normalized) because:
            # - PocketCasts entries don't have a corresponding entry in content_sources table
            # - Different discovery mechanisms provide different metadata (RSS vs PocketCasts API)
            record = {
                'url': post['url'],  # The actual article/episode URL to process
                'title': post['title'],  # Episode/article title
                'content_type': content_type,  # 'podcast/audio' or 'article' (based on URL extension)
                'source': 'rss_feed',  # Discovery mechanism for this flow (vs 'podcast_history')
                'channel_title': channel_title,  # Podcast/newsletter name (from RSS metadata)
                # 'video_url': None,  # REMOVED - YouTube discovery happens in Article Processor
                'audio_url': post.get('audio_url'),  # Direct audio file URL from RSS enclosure
                'platform': post.get('platform', 'generic'),  # 'podcast_rss' or 'rss_feed' (from source_type)
                'found_at': datetime.now().isoformat(),
                'published_date': post['published'].isoformat() if post.get('published') else None,
                'duration_seconds': post.get('duration'),
                'status': 'discovered',
                'user_id': user_id,
                'organization_id': organization_id
            }

            result = self.supabase.table('content_queue').upsert(
                record,
                on_conflict='url'
            ).execute()

            if result.data:
                return result.data[0]['id']
            return None

        except Exception as e:
            self.logger.error(f"Error saving post to queue: {e}")
            return None

    # REMOVED: YouTube discovery moved to Article Processor
    # def _discover_youtube_url_for_post() - deleted

    def _extract_channel_info(self, url: str, source_feed: str = None) -> tuple:
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

    async def get_discovered_posts(self, user_id: str, limit: int = 200) -> List[Dict]:
        """Get discovered posts from content_queue for a specific user (RSS feed content only)"""
        try:
            result = self.supabase.table('content_queue').select('*').eq(
                'user_id', user_id
            ).eq(
                'source', 'rss_feed'
            ).order('found_at', desc=True).limit(limit).execute()

            # Transform to match expected format
            posts = []
            for row in result.data:
                posts.append({
                    'id': row['id'],
                    'title': row['title'],
                    'url': row['url'],
                    'content_type': row.get('content_type', 'article'),
                    'channel_title': row.get('channel_title'),
                    'channel_url': row.get('channel_url'),
                    'platform': row.get('platform', 'generic'),
                    'source_feed': row.get('source_feed'),
                    'published_date': row.get('published_date'),
                    'found_at': row.get('found_at'),
                    'status': row.get('status', 'discovered'),
                    'is_new': False  # Will be set by frontend based on newly_discovered_ids
                })

            return posts

        except Exception as e:
            self.logger.error(f"Error getting discovered posts: {e}")
            return []
