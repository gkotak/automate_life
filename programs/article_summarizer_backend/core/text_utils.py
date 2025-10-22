#!/usr/bin/env python3
"""
Text Utilities

Provides text manipulation functions for article processing.
"""

import re


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
