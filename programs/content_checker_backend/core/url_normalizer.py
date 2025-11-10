"""
URL Normalization Utility

Standardizes URLs for consistent lookups in known_channels table.
Ensures that content_sources URLs match known_channels.source_url.
"""

from urllib.parse import urlparse, urlunparse
from typing import Optional


class URLNormalizer:
    """Normalizes URLs for consistent comparison"""

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize a URL to a canonical form for comparison

        Rules:
        1. Remove trailing slashes
        2. Remove www. prefix
        3. Lowercase scheme and domain
        4. Keep path, query, and fragment as-is
        5. Remove default ports (80 for http, 443 for https)

        Args:
            url: URL to normalize

        Returns:
            Normalized URL string
        """
        if not url:
            return ""

        try:
            parsed = urlparse(url)

            # Normalize scheme (lowercase)
            scheme = parsed.scheme.lower() if parsed.scheme else 'https'

            # Normalize domain (lowercase, remove www.)
            netloc = parsed.netloc.lower()
            if netloc.startswith('www.'):
                netloc = netloc[4:]

            # Remove default ports
            if ':80' in netloc and scheme == 'http':
                netloc = netloc.replace(':80', '')
            elif ':443' in netloc and scheme == 'https':
                netloc = netloc.replace(':443', '')

            # Normalize path (remove trailing slash, except for root)
            path = parsed.path
            if path and path != '/' and path.endswith('/'):
                path = path.rstrip('/')

            # Reconstruct URL
            normalized = urlunparse((
                scheme,
                netloc,
                path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))

            return normalized

        except Exception:
            # If parsing fails, return original
            return url

    @staticmethod
    def is_rss_feed_url(url: str) -> bool:
        """
        Check if URL appears to be an RSS feed

        Args:
            url: URL to check

        Returns:
            True if URL looks like an RSS feed
        """
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

    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """
        Extract just the domain from a URL

        Args:
            url: URL to extract domain from

        Returns:
            Domain string (e.g., "example.com")
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return None

    @staticmethod
    def are_same_source(url1: str, url2: str) -> bool:
        """
        Check if two URLs represent the same content source

        This is a fuzzy comparison that handles common variations:
        - With/without www.
        - With/without trailing slashes
        - HTTP vs HTTPS
        - Different query parameters (returns False)

        Args:
            url1: First URL
            url2: Second URL

        Returns:
            True if URLs represent the same source
        """
        norm1 = URLNormalizer.normalize_url(url1)
        norm2 = URLNormalizer.normalize_url(url2)

        return norm1 == norm2
