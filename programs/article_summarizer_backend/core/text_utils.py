#!/usr/bin/env python3
"""
Text Utilities

Provides text manipulation functions for article processing.
"""

import re
from datetime import datetime
from typing import Optional, Tuple
from difflib import SequenceMatcher


def sanitize_filename(title: str) -> str:
    """
    Sanitize title for use as filename

    Args:
        title: Article title

    Returns:
        Sanitized filename (max 100 characters)

    Examples:
        >>> sanitize_filename("Hello World — A Test Article")
        'Hello_World_-_A_Test_Article'
        >>> sanitize_filename("Invalid: <chars>")
        'Invalid_chars'
    """
    # Replace em dashes and en dashes with regular hyphens
    sanitized = title.replace('–', '-').replace('—', '-').replace('−', '-')

    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)

    # Replace spaces and multiple spaces with underscores
    sanitized = re.sub(r'\s+', '_', sanitized)

    # Remove any remaining problematic Unicode characters and keep only ASCII
    sanitized = ''.join(char if ord(char) < 128 else '_' for char in sanitized)

    # Clean up multiple underscores
    sanitized = re.sub(r'_{2,}', '_', sanitized)

    # Limit length
    return sanitized[:100] if len(sanitized) > 100 else sanitized


def calculate_title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity ratio between two titles using SequenceMatcher

    Args:
        title1: First title
        title2: Second title

    Returns:
        Similarity ratio between 0.0 and 1.0 (0-100%)

    Examples:
        >>> calculate_title_similarity("AI Engineering 101", "AI Engineering 101")
        1.0
        >>> calculate_title_similarity("Hello World", "Hello")
        0.67
    """
    return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()


def check_title_and_date_match(
    title1: str,
    title2: str,
    date1: Optional[datetime] = None,
    date2: Optional[datetime] = None,
    strong_threshold: float = 0.65,
    weak_threshold: float = 0.50,
    date_tolerance_days: int = 1
) -> Tuple[bool, float, str]:
    """
    Check if two titles match using fuzzy matching with optional date validation

    Matching criteria:
    - Strong match: title similarity >= strong_threshold (default 65%)
    - Combined match: title similarity >= weak_threshold (default 50%) AND dates within tolerance (default 1 day)

    Args:
        title1: First title to compare
        title2: Second title to compare
        date1: Optional publication date for first content
        date2: Optional publication date for second content
        strong_threshold: Minimum similarity for strong match (0.0-1.0)
        weak_threshold: Minimum similarity when combined with date match (0.0-1.0)
        date_tolerance_days: Maximum days difference for date match

    Returns:
        Tuple of (matches: bool, similarity_ratio: float, match_type: str)
        match_type can be: "strong_title", "title_plus_date", or "no_match"

    Examples:
        >>> # Strong title match
        >>> check_title_and_date_match("AI Engineering 101", "AI Engineering 101 with Chip")[0]
        True

        >>> # Weak title + date match
        >>> from datetime import datetime, timedelta
        >>> d1 = datetime(2024, 10, 23)
        >>> d2 = d1 + timedelta(hours=6)
        >>> check_title_and_date_match("AI Eng 101", "Artificial Intelligence Engineering", d1, d2)[0]
        False  # Title too different even with date match
    """
    # Calculate title similarity
    similarity = calculate_title_similarity(title1, title2)

    # Check strong title match first (65% by default)
    if similarity >= strong_threshold:
        return True, similarity, "strong_title"

    # Check combined match (50% title + date within 1 day)
    if similarity >= weak_threshold and date1 and date2:
        date_diff_days = abs((date1 - date2).days)
        if date_diff_days <= date_tolerance_days:
            return True, similarity, "title_plus_date"

    # No match
    return False, similarity, "no_match"
