"""
Shared pytest fixtures for article_summarizer_backend tests

This file contains fixtures that are available to all test files.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List


@pytest.fixture
def sample_urls() -> Dict[str, str]:
    """Sample URLs for testing"""
    return {
        'youtube': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'youtube_embed': 'https://www.youtube.com/embed/dQw4w9WgXcQ',
        'vimeo': 'https://vimeo.com/123456789',
        'vimeo_embed': 'https://player.vimeo.com/video/123456789',
        'loom': 'https://www.loom.com/share/abc123def456',
        'loom_embed': 'https://www.loom.com/embed/abc123def456',
        'blog_post': 'https://example.com/blog/my-article',
        'blog_with_params': 'https://example.com/blog/my-article?utm_source=twitter&utm_campaign=test',
        'substack': 'https://example.substack.com/p/test-article',
        'medium': 'https://medium.com/@user/test-article-123abc',
    }


@pytest.fixture
def sample_titles() -> Dict[str, str]:
    """Sample article titles for testing"""
    return {
        'simple': 'Simple Test Article',
        'with_special_chars': 'Test Article: A Journey — Part 1',
        'with_unicode': 'Test Article with émojis 🚀 and ñoñ-ASCII',
        'very_long': 'A' * 200,  # 200 character title
        'with_punctuation': 'Why AI? Testing [brackets], (parens), and <angles>!',
    }


@pytest.fixture
def sample_dates() -> Dict[str, datetime]:
    """Sample dates for testing"""
    base_date = datetime(2024, 10, 23, 12, 0, 0)
    return {
        'base': base_date,
        'same_day': base_date + timedelta(hours=6),
        'next_day': base_date + timedelta(days=1),
        'week_later': base_date + timedelta(days=7),
        'month_later': base_date + timedelta(days=30),
    }


@pytest.fixture
def sample_html_iframes() -> Dict[str, str]:
    """Sample HTML iframe tags for testing video detection"""
    return {
        'youtube': '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" frameborder="0"></iframe>',
        'youtube_nocookie': '<iframe src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"></iframe>',
        'vimeo': '<iframe src="https://player.vimeo.com/video/123456789?badge=0&autopause=0"></iframe>',
        'loom': '<iframe src="https://www.loom.com/embed/abc123def456?hide_owner=true"></iframe>',
        'wistia': '<iframe src="https://fast.wistia.net/embed/iframe/xyz789abc" allowtransparency="true"></iframe>',
        'dailymotion': '<iframe src="https://www.dailymotion.com/embed/video/x8abcdef"></iframe>',
        'generic': '<iframe src="https://example.com/video/player"></iframe>',
        'non_video': '<iframe src="https://example.com/embed/map"></iframe>',
    }


@pytest.fixture
def sample_video_ids() -> Dict[str, str]:
    """Expected video IDs extracted from URLs/iframes"""
    return {
        'youtube': 'dQw4w9WgXcQ',
        'vimeo': '123456789',
        'loom': 'abc123def456',
        'wistia': 'xyz789abc',
        'dailymotion': 'x8abcdef',
    }


@pytest.fixture
def mock_html_content() -> str:
    """Sample HTML content with embedded videos"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Article</title></head>
    <body>
        <h1>Test Article with Videos</h1>
        <p>This is a test article with embedded videos.</p>

        <div class="video-container">
            <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>
        </div>

        <p>Some more content here.</p>

        <div class="another-video">
            <iframe src="https://player.vimeo.com/video/123456789"></iframe>
        </div>
    </body>
    </html>
    """
