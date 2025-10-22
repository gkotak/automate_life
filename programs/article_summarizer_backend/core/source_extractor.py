#!/usr/bin/env python3
"""
Source Extraction Utilities

Provides functions for extracting and normalizing source names from URLs.
Handles special cases for YouTube, Pocket Casts, Substack, and other platforms.
"""

import re
import json
import logging
from typing import Optional, Dict
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


def extract_domain(url: str) -> str:
    """
    Extract domain from URL

    Args:
        url: Full URL

    Returns:
        Domain name (e.g., 'example.com')
    """
    return urlparse(url).netloc


def normalize_source_name(source: str) -> str:
    """
    Normalize source name by removing common suffixes like Newsletter, Podcast, Journal, etc.

    Args:
        source: Raw source name

    Returns:
        Normalized source name

    Examples:
        >>> normalize_source_name("Lenny's Newsletter")
        "Lenny's"
        >>> normalize_source_name("TechCrunch Daily")
        "TechCrunch"
    """
    # List of suffixes to remove (case-insensitive)
    suffixes_to_remove = [
        'Newsletter',
        'Podcast',
        'Journal',
        'Magazine',
        'Blog',
        'Daily',
        'Weekly',
        'Show',
        'Network',
        'Media',
        'News'
    ]

    # Build regex pattern to match suffixes at the end
    # Pattern matches: optional space/colon/dash/apostrophe+s, then suffix
    # This will match patterns like:
    # - "Lenny's Newsletter" -> "Lenny's"
    # - "Lenny's Podcast" -> "Lenny's"
    # - "TechCrunch Daily" -> "TechCrunch"
    pattern = r"\s*[-:,]?\s*(?:'s\s+)?(" + '|'.join(suffixes_to_remove) + r")\s*$"

    # Remove matched suffixes (case-insensitive)
    normalized = re.sub(pattern, '', source, flags=re.IGNORECASE)

    # Clean up any trailing whitespace, colons, or dashes
    normalized = normalized.rstrip(' :-,')

    return normalized.strip()


def format_substack_name(domain: str) -> str:
    """
    Format Substack subdomain as source name

    Args:
        domain: Domain like 'example.substack.com'

    Returns:
        Formatted source name

    Examples:
        >>> format_substack_name('lennysnewsletter.substack.com')
        'Lennysnewsletter'
    """
    # Extract subdomain from domain like 'example.substack.com'
    parts = domain.split('.')
    if len(parts) >= 3 and parts[-2] == 'substack':
        subdomain = parts[0]
        # Capitalize and replace hyphens with spaces
        return subdomain.replace('-', ' ').title()
    return "Substack"


def format_domain_name(domain: str) -> str:
    """
    Format domain name nicely (capitalize, spaces)

    Args:
        domain: Domain name

    Returns:
        Formatted name

    Examples:
        >>> format_domain_name('wait-but-why.com')
        'Wait But Why'
    """
    # Remove TLD
    name = domain.rsplit('.', 1)[0]
    # Replace hyphens/underscores with spaces
    name = name.replace('-', ' ').replace('_', ' ')
    # Capitalize words
    return name.title()


def extract_youtube_channel_name(url: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """
    Extract YouTube channel name from video URL

    Args:
        url: YouTube video URL
        session: Optional requests session to use

    Returns:
        Channel name or None if not found
    """
    try:
        if session is None:
            session = requests.Session()

        # Fetch the YouTube page
        response = session.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Try to find channel name from meta tags
        # Method 1: og:site_name sometimes contains channel
        channel_link = soup.find('link', {'itemprop': 'name'})
        if channel_link and channel_link.get('content'):
            return channel_link['content']

        # Method 2: Look for channel name in metadata
        channel_meta = soup.find('meta', {'name': 'author'})
        if channel_meta and channel_meta.get('content'):
            return channel_meta['content']

        # Method 3: Look in structured data (JSON-LD)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Look for author/creator info
                    if 'author' in data and isinstance(data['author'], dict):
                        if 'name' in data['author']:
                            return data['author']['name']
                    if 'creator' in data and isinstance(data['creator'], dict):
                        if 'name' in data['creator']:
                            return data['creator']['name']
            except:
                continue

        return None

    except Exception as e:
        logger.debug(f"Could not extract YouTube channel name: {e}")
        return None


def extract_source(url: str, metadata: Dict, session: Optional[requests.Session] = None) -> str:
    """
    Extract source name from URL

    For YouTube: Extract channel name
    For PocketCasts: Extract podcast name
    For other URLs: Format domain name nicely

    Args:
        url: Article URL
        metadata: Article metadata containing platform info
        session: Optional requests session to use

    Returns:
        Formatted source name (normalized)
    """
    # YouTube - try to extract channel name
    if 'youtube.com' in url or 'youtu.be' in url:
        channel_name = extract_youtube_channel_name(url, session)
        if channel_name:
            return normalize_source_name(channel_name)
        return "YouTube"

    # PocketCasts - extract podcast name from metadata
    if 'pocketcasts.com' in url:
        podcast_name = metadata.get('podcast_title') or metadata.get('podcast_name')
        if podcast_name:
            return normalize_source_name(podcast_name)
        return "Pocket Casts"

    # For other URLs, format domain nicely
    domain = extract_domain(url)

    # Remove common prefixes
    domain = domain.replace('www.', '')

    # Special case mappings for common domains
    domain_mappings = {
        'substack.com': lambda d: format_substack_name(d),
        'medium.com': 'Medium',
        'nytimes.com': 'New York Times',
        'wsj.com': 'Wall Street Journal',
        'ft.com': 'Financial Times',
        'bloomberg.com': 'Bloomberg',
        'techcrunch.com': 'TechCrunch',
        'theverge.com': 'The Verge',
        'arstechnica.com': 'Ars Technica',
        'wired.com': 'Wired',
        'stratechery.com': 'Stratechery',
        'lennysnewsletter.com': "Lenny",
        'akashbajwa.co': 'Akash Bajwa',
    }

    # Check domain mappings
    for key, value in domain_mappings.items():
        if key in domain:
            if callable(value):
                return normalize_source_name(value(domain))
            return value

    # Default: Capitalize domain name
    return normalize_source_name(format_domain_name(domain))
