#!/usr/bin/env python3
"""
Migration script to import existing JSON data into content_queue table

Migrates:
- processed_podcasts.json (99 podcast episodes)
- processed_posts.json (36 articles/posts)

Into the unified content_queue table in Supabase.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import re
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
root_env = Path(__file__).parent.parent.parent.parent / '.env.local'
load_dotenv(root_env)


def extract_channel_info_from_url(url: str, platform: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract channel title and URL from article URL

    Args:
        url: Article URL
        platform: Platform type

    Returns:
        Tuple of (channel_title, channel_url)
    """
    # Common patterns
    if 'stratechery.com' in url:
        return 'Stratechery', 'https://stratechery.com'
    elif 'lennysnewsletter.com' in url:
        return "Lenny's Newsletter", 'https://www.lennysnewsletter.com'
    elif 'creatoreconomy.so' in url:
        return 'Creator Economy', 'https://creatoreconomy.so'
    elif 'akashbajwa.co' in url:
        return 'Akash Bajwa', 'https://www.akashbajwa.co'

    # Try to extract domain as fallback
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain, f"https://{parsed.netloc}"
    except:
        return None, None


def construct_pocketcasts_channel_url(podcast_uuid: str) -> str:
    """
    Construct PocketCasts channel URL from podcast UUID

    Args:
        podcast_uuid: PocketCasts podcast UUID

    Returns:
        Channel URL
    """
    return f"https://pocketcasts.com/podcast/{podcast_uuid}"


def migrate_podcasts(supabase: Client, json_path: str) -> int:
    """
    Migrate processed_podcasts.json to content_queue

    Args:
        supabase: Supabase Client instance
        json_path: Path to processed_podcasts.json

    Returns:
        Number of records migrated
    """
    print(f"\n📂 Loading podcasts from: {json_path}")

    with open(json_path, 'r') as f:
        podcasts = json.load(f)

    print(f"   Found {len(podcasts)} podcast episodes")

    migrated = 0
    skipped = 0
    errors = 0

    for content_hash, podcast in podcasts.items():
        try:
            # Map to content_queue schema
            record = {
                'url': podcast['episode_url'],
                'title': podcast['episode_title'],
                'content_type': 'podcast_episode',
                'channel_title': podcast['podcast_title'],
                'channel_url': construct_pocketcasts_channel_url(podcast['podcast_uuid']),
                'video_url': podcast.get('podcast_video_url'),
                'platform': 'pocketcasts',
                'source_feed': None,  # PocketCasts episodes don't come from RSS
                'found_at': podcast['found_at'],
                'published_date': podcast.get('published_date'),
                'status': podcast.get('status', 'discovered'),
                'podcast_uuid': podcast['podcast_uuid'],
                'episode_uuid': podcast['episode_uuid'],
                'duration_seconds': podcast.get('duration'),
                'played_up_to': podcast.get('played_up_to'),
                'progress_percent': podcast.get('progress_percent'),
                'playing_status': podcast.get('playing_status')
            }

            # Insert into Supabase (upsert to handle duplicates)
            result = supabase.table('content_queue').upsert(
                record,
                on_conflict='url'
            ).execute()

            migrated += 1

            if migrated % 10 == 0:
                print(f"   ✓ Migrated {migrated} podcasts...")

        except Exception as e:
            print(f"   ✗ Error migrating podcast '{podcast.get('episode_title', 'unknown')}': {e}")
            errors += 1

    print(f"\n✅ Podcast migration complete:")
    print(f"   • Migrated: {migrated}")
    print(f"   • Errors: {errors}")

    return migrated


def migrate_posts(supabase: Client, json_path: str) -> int:
    """
    Migrate processed_posts.json to content_queue

    Args:
        supabase: Supabase Client instance
        json_path: Path to processed_posts.json

    Returns:
        Number of records migrated
    """
    print(f"\n📂 Loading posts from: {json_path}")

    with open(json_path, 'r') as f:
        posts = json.load(f)

    print(f"   Found {len(posts)} posts/articles")

    migrated = 0
    errors = 0

    for content_hash, post in posts.items():
        try:
            # Determine channel info
            channel_title, channel_url = extract_channel_info_from_url(
                post['url'],
                post['platform']
            )

            # If source_feed is available and channel_url not extracted, use source_feed
            if not channel_url and post.get('source_feed'):
                channel_url = post['source_feed']

            # Map to content_queue schema
            record = {
                'url': post['url'],
                'title': post['title'],
                'content_type': 'article',  # All posts are articles
                'channel_title': channel_title,
                'channel_url': channel_url,
                'video_url': None,  # Will be populated by article_summarizer
                'platform': post['platform'],
                'source_feed': post.get('source_feed'),
                'found_at': post['found_at'],
                'published_date': post.get('published_date'),
                'status': post.get('status', 'discovered'),
                # Podcast-specific fields are NULL for articles
                'podcast_uuid': None,
                'episode_uuid': None,
                'duration_seconds': None,
                'played_up_to': None,
                'progress_percent': None,
                'playing_status': None
            }

            # Insert into Supabase (upsert to handle duplicates)
            result = supabase.table('content_queue').upsert(
                record,
                on_conflict='url'
            ).execute()

            migrated += 1

            if migrated % 10 == 0:
                print(f"   ✓ Migrated {migrated} posts...")

        except Exception as e:
            print(f"   ✗ Error migrating post '{post.get('title', 'unknown')}': {e}")
            errors += 1

    print(f"\n✅ Post migration complete:")
    print(f"   • Migrated: {migrated}")
    print(f"   • Errors: {errors}")

    return migrated


def verify_migration(supabase: Client, expected_podcasts: int, expected_posts: int):
    """
    Verify migration by checking counts

    Args:
        supabase: Supabase Client instance
        expected_podcasts: Expected number of podcasts
        expected_posts: Expected number of posts
    """
    print("\n🔍 Verifying migration...")

    # Count by content_type
    podcast_count = supabase.table('content_queue').select(
        'id', count='exact'
    ).eq('content_type', 'podcast_episode').execute()

    article_count = supabase.table('content_queue').select(
        'id', count='exact'
    ).eq('content_type', 'article').execute()

    total_count = supabase.table('content_queue').select(
        'id', count='exact'
    ).execute()

    print(f"\n📊 Migration Results:")
    print(f"   Podcast episodes: {podcast_count.count} (expected {expected_podcasts})")
    print(f"   Articles: {article_count.count} (expected {expected_posts})")
    print(f"   Total: {total_count.count} (expected {expected_podcasts + expected_posts})")

    # Check for records with video URLs
    with_video = supabase.table('content_queue').select(
        'id', count='exact'
    ).not_.is_('video_url', 'null').execute()

    print(f"   Content with video URLs: {with_video.count}")

    # Status breakdown
    discovered = supabase.table('content_queue').select(
        'id', count='exact'
    ).eq('status', 'discovered').execute()

    print(f"   Status 'discovered': {discovered.count}")

    if podcast_count.count == expected_podcasts and article_count.count == expected_posts:
        print("\n✅ Migration verified successfully!")
        return True
    else:
        print("\n⚠️ Migration counts don't match expected values")
        return False


def main():
    """Main migration function"""
    print("="*80)
    print("CONTENT QUEUE MIGRATION")
    print("="*80)

    # Initialize Supabase client
    print("\n🔌 Connecting to Supabase...")
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env.local")
        return 1

    supabase: Client = create_client(supabase_url, supabase_key)
    print("   ✓ Connected")

    # Paths to JSON files
    base_dir = Path(__file__).parent.parent
    podcasts_path = base_dir / 'output' / 'processed_podcasts.json'
    posts_path = base_dir / 'output' / 'processed_posts.json'

    # Check files exist
    if not podcasts_path.exists():
        print(f"❌ Error: {podcasts_path} not found")
        return 1

    if not posts_path.exists():
        print(f"❌ Error: {posts_path} not found")
        return 1

    # Migrate podcasts
    podcast_count = migrate_podcasts(supabase, str(podcasts_path))

    # Migrate posts
    post_count = migrate_posts(supabase, str(posts_path))

    # Verify migration
    verify_migration(supabase, podcast_count, post_count)

    print("\n" + "="*80)
    print("MIGRATION COMPLETE")
    print("="*80)

    return 0


if __name__ == '__main__':
    sys.exit(main())
