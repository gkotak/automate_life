#!/usr/bin/env python3
"""
Cleanup Expired Media from Supabase Storage

This script removes media files that have exceeded their TTL from the article-media
bucket and clears the corresponding database references.

Key behaviors:
- Only cleans up media from 'article-media' bucket (TTL media)
- NEVER deletes media from 'uploaded-media' bucket (permanent direct uploads)
- TTL is calculated from MEDIA_RETENTION_DAYS env var (default: 30 days)
- Updates database to clear media_storage_* columns after deletion

Usage:
    python3 scripts/cleanup_expired_media.py [--dry-run]

Schedule as Railway cron job:
    0 3 * * * python3 scripts/cleanup_expired_media.py
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_expired_media(dry_run: bool = False):
    """
    Delete expired media from storage and clear database references.

    Only processes media in the 'article-media' bucket. Media in 'uploaded-media'
    (direct uploads) is permanent and never cleaned up.

    Args:
        dry_run: If True, only log what would be deleted without actually deleting
    """
    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    # Get retention period
    retention_days = int(os.getenv('MEDIA_RETENTION_DAYS', '30'))
    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    logger.info(f"🧹 Starting media cleanup (retention: {retention_days} days)")
    logger.info(f"   Cutoff date: {cutoff.isoformat()}")
    if dry_run:
        logger.info("   DRY RUN MODE - no actual deletions will occur")

    total_deleted = 0
    total_errors = 0

    # Process both articles and private_articles tables
    for table in ['articles', 'private_articles']:
        logger.info(f"\n📋 Processing {table}...")

        try:
            # Find articles with expired media in article-media bucket
            # Only target 'article-media' bucket - NEVER 'uploaded-media'
            result = supabase.table(table).select(
                'id, media_storage_path, media_storage_bucket, media_uploaded_at, media_size_bytes'
            ).eq(
                'media_storage_bucket', 'article-media'
            ).lt(
                'media_uploaded_at', cutoff.isoformat()
            ).not_.is_(
                'media_storage_path', 'null'
            ).execute()

            expired_articles = result.data or []
            logger.info(f"   Found {len(expired_articles)} articles with expired media")

            for article in expired_articles:
                article_id = article['id']
                storage_path = article['media_storage_path']
                size_bytes = article.get('media_size_bytes', 0)
                size_mb = round(size_bytes / 1024 / 1024, 1) if size_bytes else 0

                if dry_run:
                    logger.info(f"   [DRY RUN] Would delete: {storage_path} ({size_mb}MB) for article {article_id}")
                    total_deleted += 1
                    continue

                try:
                    # Step 1: Delete from storage
                    try:
                        supabase.storage.from_('article-media').remove([storage_path])
                        logger.info(f"   🗑️ Deleted from storage: {storage_path} ({size_mb}MB)")
                    except Exception as storage_error:
                        # File might already be deleted, continue with DB cleanup
                        logger.warning(f"   ⚠️ Storage delete failed (may already be gone): {storage_error}")

                    # Step 2: Clear database columns
                    supabase.table(table).update({
                        'media_storage_path': None,
                        'media_storage_bucket': None,
                        'media_uploaded_at': None,
                        'media_content_type': None,
                        'media_size_bytes': None,
                        'media_duration_seconds': None
                    }).eq('id', article_id).execute()

                    logger.info(f"   ✅ Cleared database fields for article {article_id}")
                    total_deleted += 1

                except Exception as e:
                    logger.error(f"   ❌ Error processing article {article_id}: {e}")
                    total_errors += 1

        except Exception as e:
            logger.error(f"   ❌ Error querying {table}: {e}")
            total_errors += 1

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"🏁 Cleanup complete!")
    logger.info(f"   {'Would delete' if dry_run else 'Deleted'}: {total_deleted} media files")
    if total_errors > 0:
        logger.info(f"   Errors: {total_errors}")

    return total_deleted, total_errors


def main():
    parser = argparse.ArgumentParser(
        description='Cleanup expired media from Supabase Storage'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    args = parser.parse_args()

    cleanup_expired_media(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
