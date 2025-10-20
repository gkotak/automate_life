#!/usr/bin/env python3
"""
Backfill source field for existing articles in Supabase database

Usage:
    python3 backfill_sources.py [--dry-run]
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import argparse

# Load environment variables
root_env = Path(__file__).parent.parent.parent.parent / '.env.local'
if root_env.exists():
    load_dotenv(root_env)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.article_summarizer import ArticleSummarizer


def backfill_sources(dry_run=False, force=False):
    """Backfill source field for all articles"""

    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env.local")
        return

    supabase = create_client(supabase_url, supabase_key)

    # Initialize ArticleSummarizer to use its source extraction logic
    summarizer = ArticleSummarizer()

    print("=" * 80)
    print("BACKFILLING SOURCE FIELD FOR EXISTING ARTICLES")
    print("=" * 80)

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made to the database")
    if force:
        print("🔄 FORCE MODE - Will update all articles even if source exists")
    print()

    # Fetch all articles
    print("📥 Fetching all articles from database...")
    result = supabase.table('articles').select('id, url, title, source, platform').execute()

    articles = result.data
    print(f"✅ Found {len(articles)} articles")
    print()

    # Track statistics
    updated_count = 0
    skipped_count = 0
    error_count = 0

    # Process each article
    for idx, article in enumerate(articles, 1):
        article_id = article['id']
        url = article['url']
        title = article['title']
        current_source = article.get('source')

        print(f"[{idx}/{len(articles)}] Processing article ID {article_id}")
        print(f"   Title: {title[:60]}...")
        print(f"   URL: {url[:60]}...")

        # Skip if source already exists (unless force mode)
        if current_source and not force:
            print(f"   ⏭️  Source already set: '{current_source}' - skipping")
            skipped_count += 1
            print()
            continue

        if current_source and force:
            print(f"   🔄 Current source: '{current_source}' - will update")

        try:
            # Build metadata dict (minimal info needed for source extraction)
            metadata = {
                'url': url,
                'title': title,
                'platform': article.get('platform')
            }

            # Extract source
            source = summarizer._extract_source(url, metadata)
            print(f"   ✅ Extracted source: '{source}'")

            # Update database (unless dry run)
            if not dry_run:
                update_result = supabase.table('articles').update({
                    'source': source
                }).eq('id', article_id).execute()

                if update_result.data:
                    print(f"   💾 Updated in database")
                    updated_count += 1
                else:
                    print(f"   ⚠️  Database update returned no data")
                    error_count += 1
            else:
                print(f"   🔍 [DRY RUN] Would update source to: '{source}'")
                updated_count += 1

        except Exception as e:
            print(f"   ❌ Error processing article: {e}")
            error_count += 1

        print()

    # Print summary
    print("=" * 80)
    print("BACKFILL COMPLETE")
    print("=" * 80)
    print(f"Total articles:     {len(articles)}")
    print(f"Updated:            {updated_count}")
    print(f"Skipped (has source): {skipped_count}")
    print(f"Errors:             {error_count}")

    if dry_run:
        print()
        print("🔍 This was a DRY RUN - no changes were made to the database")
        print("   Run without --dry-run to apply changes")


def main():
    parser = argparse.ArgumentParser(description='Backfill source field for existing articles')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without updating database')
    parser.add_argument('--force', action='store_true', help='Update all articles even if source already exists')
    args = parser.parse_args()

    backfill_sources(dry_run=args.dry_run, force=args.force)


if __name__ == '__main__':
    main()
