#!/usr/bin/env python3
"""
Regenerate AI summary for an article using existing transcript data

This script:
1. Fetches article data from Supabase (including transcript)
2. Reconstructs metadata needed for AI analysis
3. Re-runs ONLY the AI analysis step (skips video download/transcription)
4. Updates the article with new summary, key_insights, quotes, etc.

Usage:
    python3 scripts/regenerate_summary.py <article_id>
    python3 scripts/regenerate_summary.py 123
"""

import sys
import os
import json
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.article_processor import ArticleProcessor
from core.content_detector import ContentType
from core.config import Config
from supabase import create_client

def get_supabase_client():
    """Get Supabase client from environment variables"""
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not supabase_url or not supabase_key:
        logger.error("Missing required environment variables:")
        logger.error("  SUPABASE_URL: " + ("✓ Set" if supabase_url else "✗ Not set"))
        logger.error("  SUPABASE_SERVICE_ROLE_KEY: " + ("✓ Set" if supabase_key else "✗ Not set"))
        logger.error("\nPlease set these environment variables before running this script.")
        raise ValueError("Required environment variables not set")
    return create_client(supabase_url, supabase_key)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_article_from_db(article_id: int) -> dict:
    """Fetch article data from Supabase"""
    supabase = get_supabase_client()

    logger.info(f"Fetching article {article_id} from database...")
    response = supabase.table('articles').select('*').eq('id', article_id).single().execute()

    if not response.data:
        raise ValueError(f"Article {article_id} not found in database")

    return response.data


def reconstruct_metadata(article: dict) -> dict:
    """Reconstruct metadata needed for AI analysis from article data"""

    # Parse transcript data from database
    transcript_text = article.get('transcript_text', '')
    transcripts = {}

    if transcript_text and article.get('video_id'):
        # Reconstruct transcript in the format expected by AI
        # Parse the [MM:SS] format from stored transcript
        transcript_lines = []
        for line in transcript_text.split('\n'):
            if line.strip():
                transcript_lines.append(line)

        # Create transcript data structure
        segments = []
        for line in transcript_lines:
            # Parse [MM:SS] or [H:MM:SS] format
            import re
            match = re.match(r'^\[(\d+):(\d+)(?::(\d+))?\]\s*(.*)$', line)
            if match:
                if match.group(3):  # H:MM:SS format
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    seconds = int(match.group(3))
                    start_time = hours * 3600 + minutes * 60 + seconds
                else:  # MM:SS format
                    minutes = int(match.group(1))
                    seconds = int(match.group(2))
                    start_time = minutes * 60 + seconds

                text = match.group(4) if match.group(3) else match.group(3)
                if not text:
                    text = match.group(4)

                segments.append({
                    'start': start_time,
                    'text': text.strip()
                })

        transcripts[article['video_id']] = {
            'success': True,
            'type': 'existing',
            'transcript': segments,
            'segments': segments
        }

    # Reconstruct content type
    content_source = article.get('content_source', 'article')
    content_type = ContentType(
        has_embedded_video=(content_source == 'video'),
        has_embedded_audio=(content_source == 'audio'),
        is_text_only=(content_source == 'article'),
        video_urls=[{
            'video_id': article.get('video_id'),
            'platform': article.get('platform'),
            'url': article.get('url')
        }] if article.get('video_id') else [],
        audio_urls=[{
            'url': article.get('audio_url'),
            'platform': article.get('platform')
        }] if article.get('audio_url') else []
    )

    # Build metadata
    metadata = {
        'title': article.get('title'),
        'url': article.get('url'),
        'platform': article.get('platform'),
        'content_type': content_type,
        'article_text': article.get('original_article_text', ''),
        'transcripts': transcripts,
        'media_info': {
            'video_urls': content_type.video_urls,
            'audio_urls': content_type.audio_urls
        },
        'extracted_at': article.get('created_at')
    }

    logger.info(f"Reconstructed metadata:")
    logger.info(f"  - Content type: {content_source}")
    logger.info(f"  - Has transcript: {len(transcripts) > 0}")
    logger.info(f"  - Transcript segments: {len(segments) if segments else 0}")
    logger.info(f"  - Video ID: {article.get('video_id')}")
    logger.info(f"  - Platform: {article.get('platform')}")

    return metadata


def update_article_in_db(article_id: int, ai_summary: dict):
    """Update article with new AI-generated data"""
    supabase = get_supabase_client()

    logger.info(f"Updating article {article_id} with new AI summary...")

    update_data = {
        'summary_text': ai_summary.get('summary', ''),
        'key_insights': ai_summary.get('key_insights', []),
        'quotes': ai_summary.get('quotes', []),
        'duration_minutes': ai_summary.get('duration_minutes'),
        'word_count': ai_summary.get('word_count'),
        'topics': ai_summary.get('topics', [])
    }

    response = supabase.table('articles').update(update_data).eq('id', article_id).execute()

    logger.info(f"✅ Successfully updated article {article_id}")
    logger.info(f"  - Key insights: {len(update_data.get('key_insights', []))}")
    logger.info(f"  - Quotes: {len(update_data.get('quotes', []))}")
    logger.info(f"  - Topics: {len(update_data.get('topics', []))}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/regenerate_summary.py <article_id>")
        print("Example: python3 scripts/regenerate_summary.py 123")
        sys.exit(1)

    article_id = int(sys.argv[1])

    try:
        # Step 1: Fetch article from database
        article = fetch_article_from_db(article_id)
        logger.info(f"✅ Fetched article: {article['title']}")

        # Step 2: Reconstruct metadata
        metadata = reconstruct_metadata(article)

        # Step 3: Generate new AI summary using existing transcript
        processor = ArticleProcessor()
        logger.info("🤖 Generating new AI summary...")
        ai_summary = processor._generate_summary_with_ai(article['url'], metadata)

        # Step 4: Update database
        update_article_in_db(article_id, ai_summary)

        logger.info("✅ Done! Article summary regenerated successfully.")
        logger.info(f"View at: http://localhost:3000/article/{article_id}")

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
