"""
RSS Feed Discovery Utility

Auto-discovers RSS feeds from web pages to ensure consistent
source URLs between content_sources and known_channels tables.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional, List, Dict
import logging

from core.config import Config


class RSSDiscovery:
    """Discovers RSS feeds from web pages"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update(Config.get_default_headers())

    def discover_rss_feed(self, url: str) -> Optional[str]:
        """
        Auto-discover RSS feed from a web page URL

        Args:
            url: Web page URL (e.g., https://stratechery.com)

        Returns:
            RSS feed URL if found, otherwise None
        """
        try:
            # If it's already an RSS feed, return it
            if self._is_rss_feed(url):
                return url

            self.logger.info(f"🔍 [RSS DISCOVERY] Checking for RSS feed at: {url}")

            response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
            response.raise_for_status()

            # Try to discover from HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Strategy 1: Look for RSS/Atom feed links in <head>
            feed_url = self._discover_from_html_head(soup, url)
            if feed_url:
                self.logger.info(f"✅ [RSS DISCOVERY] Found in HTML head: {feed_url}")
                return feed_url

            # Strategy 2: Try common RSS feed paths
            feed_url = self._try_common_feed_paths(url)
            if feed_url:
                self.logger.info(f"✅ [RSS DISCOVERY] Found via common path: {feed_url}")
                return feed_url

            self.logger.info(f"ℹ️ [RSS DISCOVERY] No RSS feed found, using original URL")
            return url  # Return original if no RSS found

        except Exception as e:
            self.logger.warning(f"⚠️ [RSS DISCOVERY] Error: {e}")
            return url  # Return original on error

    def _is_rss_feed(self, url: str) -> bool:
        """Check if URL is already an RSS feed"""
        url_lower = url.lower()
        rss_indicators = [
            '/rss',
            '/feed',
            '/atom',
            '.rss',
            '.xml',
            'rss.xml',
            'feed.xml',
            'atom.xml',
            'feeds.'
        ]
        return any(indicator in url_lower for indicator in rss_indicators)

    def _discover_from_html_head(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Discover RSS feed from HTML <head> <link> tags"""
        try:
            feed_link_types = [
                'application/rss+xml',
                'application/atom+xml',
                'application/xml'
            ]

            for link in soup.find_all('link', type=feed_link_types):
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    feed_url = urljoin(base_url, href)
                    return feed_url

            return None

        except Exception as e:
            self.logger.debug(f"Error discovering from HTML head: {e}")
            return None

    def _try_common_feed_paths(self, url: str) -> Optional[str]:
        """Try common RSS feed paths"""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            common_paths = [
                '/feed',
                '/rss',
                '/feed.xml',
                '/rss.xml',
                '/atom.xml',
                '/index.xml',
                '/feeds/posts/default'  # Blogger
            ]

            for path in common_paths:
                feed_url = base_url + path
                try:
                    response = self.session.head(feed_url, timeout=5, allow_redirects=True)
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if any(t in content_type for t in ['xml', 'rss', 'atom']):
                            return feed_url
                except:
                    continue

            return None

        except Exception as e:
            self.logger.debug(f"Error trying common paths: {e}")
            return None

    def get_all_feeds(self, url: str) -> List[Dict[str, str]]:
        """
        Get all RSS/Atom feeds found on a page

        Args:
            url: Web page URL

        Returns:
            List of dicts with 'url', 'type', and 'title' keys
        """
        feeds = []

        try:
            response = self.session.get(url, timeout=Config.DEFAULT_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            feed_link_types = [
                'application/rss+xml',
                'application/atom+xml',
                'application/xml'
            ]

            for link in soup.find_all('link', type=feed_link_types):
                href = link.get('href')
                title = link.get('title', 'Untitled Feed')
                feed_type = link.get('type', 'unknown')

                if href:
                    feed_url = urljoin(url, href)
                    feeds.append({
                        'url': feed_url,
                        'type': feed_type,
                        'title': title
                    })

        except Exception as e:
            self.logger.warning(f"Error getting all feeds: {e}")

        return feeds
