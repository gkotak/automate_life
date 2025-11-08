"""
Core Utilities for Earnings Insights

Re-exports shared utilities from article_summarizer_backend/core

This module adds the article_summarizer_backend directory to Python path
so we can import its core utilities.
"""
import sys
from pathlib import Path

# Get paths
earnings_insights_dir = Path(__file__).parent.parent
project_root = earnings_insights_dir.parent.parent
article_summarizer_backend = project_root / 'programs' / 'article_summarizer_backend'

# Add article_summarizer_backend to Python path
if str(article_summarizer_backend) not in sys.path:
    sys.path.insert(0, str(article_summarizer_backend))

# Now import from core module (which is inside article_summarizer_backend)
from core.transcript_aligner import (
    TranscriptAligner,
    format_aligned_transcript_for_claude,
    format_timestamp
)
from core.browser_fetcher import BrowserFetcher
from core.authentication import AuthenticationManager
from core.content_detector import ContentTypeDetector
from core.claude_client import ClaudeClient

__all__ = [
    'TranscriptAligner',
    'format_aligned_transcript_for_claude',
    'format_timestamp',
    'BrowserFetcher',
    'AuthenticationManager',
    'ContentTypeDetector',
    'ClaudeClient',
]
