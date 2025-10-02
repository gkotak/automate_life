#!/usr/bin/env python3
"""
URL Utilities for Video Summarizer
Provides URL normalization and ID generation functions to prevent duplicates
"""

import hashlib
from urllib.parse import urlparse, urlunparse


def normalize_url(url):
    """
    Normalize URL by removing query parameters and fragments to create base URL.
    This prevents duplicates when URLs have different access tokens or tracking parameters.

    Args:
        url (str): The full URL with potential parameters

    Returns:
        str: The base URL without parameters

    Examples:
        >>> normalize_url("https://example.com/article?token=abc123&utm_source=email")
        'https://example.com/article'

        >>> normalize_url("https://stratechery.com/2025/article/?access_token=xyz")
        'https://stratechery.com/2025/article/'
    """
    try:
        parsed = urlparse(url)
        # Remove query parameters and fragment
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            '',  # params
            '',  # query
            ''   # fragment
        ))
        return normalized
    except Exception:
        # If URL parsing fails, return original URL
        return url


def generate_post_id(title, url):
    """
    Generate a unique ID for a post based on title and normalized base URL.
    This prevents duplicate entries when URLs have different parameters.

    Args:
        title (str): The title of the post
        url (str): The URL of the post

    Returns:
        str: MD5 hash of the normalized content

    Examples:
        >>> generate_post_id("Test Article", "https://example.com/article?token=123")
        # Returns MD5 hash of "Test Article|https://example.com/article"
    """
    base_url = normalize_url(url)
    content = f"{title}|{base_url}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def is_same_base_url(url1, url2):
    """
    Check if two URLs have the same base (ignoring parameters).

    Args:
        url1 (str): First URL
        url2 (str): Second URL

    Returns:
        bool: True if both URLs have the same base

    Examples:
        >>> is_same_base_url(
        ...     "https://example.com/article?token=123",
        ...     "https://example.com/article?token=456"
        ... )
        True
    """
    return normalize_url(url1) == normalize_url(url2)