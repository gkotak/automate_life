#!/usr/bin/env python3
"""
Post Manager - Enhanced JSON-based post tracking and batch processing utility
Replaces the need for found_urls_*.md files with flexible filtering and batch operations
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess

# Import our base class
sys.path.append(str(Path(__file__).parent.parent))
from common.base import BaseProcessor
from common.config import Config


class PostManager(BaseProcessor):
    def __init__(self):
        super().__init__("post_manager")
        self.posts_file = self.base_dir / "programs" / "article_summarizer" / "output" / "processed_posts.json"

        # Enhanced status options
        self.valid_statuses = [
            "discovered",      # Found but not yet processed
            "processing",      # Currently being processed
            "completed",       # Successfully processed
            "failed",          # Processing failed
            "skipped",         # Manually skipped
            "queued"          # Queued for processing
        ]

        # Load existing posts
        self.posts = self._load_posts()

    def _load_posts(self) -> Dict[str, Any]:
        """Load existing posts from JSON file"""
        try:
            if self.posts_file.exists():
                with open(self.posts_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)

                # Migrate old status format to new enhanced format
                for post_id, post_data in posts.items():
                    if post_data.get('status') == 'found_not_processed':
                        post_data['status'] = 'discovered'

                    # Add missing fields for backward compatibility
                    post_data.setdefault('processed_at', None)
                    post_data.setdefault('summary_file', None)
                    post_data.setdefault('tags', [])
                    post_data.setdefault('priority', 'medium')

                return posts
            else:
                return {}
        except Exception as e:
            self.logger.error(f"❌ Error loading posts: {e}")
            return {}

    def _save_posts(self):
        """Save posts to JSON file"""
        try:
            with open(self.posts_file, 'w', encoding='utf-8') as f:
                json.dump(self.posts, f, indent=2, ensure_ascii=False)
            self.logger.info(f"💾 Posts saved to {self.posts_file}")
        except Exception as e:
            self.logger.error(f"❌ Error saving posts: {e}")
            raise

    def list_posts(self,
                   status: Optional[str] = None,
                   since: Optional[str] = None,
                   source: Optional[str] = None,
                   platform: Optional[str] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List posts with optional filtering

        Args:
            status: Filter by status (discovered, processing, completed, etc.)
            since: Filter posts published since date (YYYY-MM-DD)
            source: Filter by source feed (partial match)
            platform: Filter by platform (rss_feed, generic)
            limit: Limit number of results
        """
        filtered_posts = []

        for post_id, post_data in self.posts.items():
            # Apply filters
            if status and post_data.get('status') != status:
                continue

            if since:
                try:
                    since_date = datetime.fromisoformat(since)
                    if post_data.get('published_date'):
                        pub_date = datetime.fromisoformat(post_data['published_date'].replace('T', ' ').replace('Z', ''))
                        if pub_date < since_date:
                            continue
                    elif post_data.get('found_at'):
                        found_date = datetime.fromisoformat(post_data['found_at'].replace('T', ' ').replace('Z', ''))
                        if found_date < since_date:
                            continue
                except ValueError:
                    self.logger.warning(f"⚠️ Invalid date format: {since}")
                    continue

            if source and source.lower() not in post_data.get('source_feed', '').lower():
                continue

            if platform and post_data.get('platform') != platform:
                continue

            # Add post_id to the data for reference
            post_with_id = {**post_data, 'post_id': post_id}
            filtered_posts.append(post_with_id)

        # Sort by found_at (newest first)
        filtered_posts.sort(key=lambda x: x.get('found_at', ''), reverse=True)

        # Apply limit
        if limit:
            filtered_posts = filtered_posts[:limit]

        return filtered_posts

    def update_status(self, post_ids: List[str], status: str, summary_file: Optional[str] = None):
        """Update status for multiple posts"""
        if status not in self.valid_statuses:
            raise ValueError(f"Invalid status: {status}. Valid statuses: {self.valid_statuses}")

        updated_count = 0
        for post_id in post_ids:
            if post_id in self.posts:
                self.posts[post_id]['status'] = status
                if status in ['completed', 'failed', 'skipped']:
                    self.posts[post_id]['processed_at'] = datetime.now().isoformat()
                if summary_file:
                    self.posts[post_id]['summary_file'] = summary_file
                updated_count += 1
            else:
                self.logger.warning(f"⚠️ Post ID not found: {post_id}")

        if updated_count > 0:
            self._save_posts()
            self.logger.info(f"✅ Updated {updated_count} posts to status: {status}")

        return updated_count

    def process_posts(self, post_ids: List[str], dry_run: bool = False) -> List[str]:
        """
        Process multiple posts using the summarize_article.sh script

        Args:
            post_ids: List of post IDs to process
            dry_run: If True, just show what would be processed without actually doing it

        Returns:
            List of successfully processed post IDs
        """
        script_path = self.base_dir / "programs" / "article_summarizer" / "scripts" / "summarize_article.sh"

        if not script_path.exists():
            raise FileNotFoundError(f"summarize_article.sh not found at {script_path}")

        successful = []
        failed = []

        for post_id in post_ids:
            if post_id not in self.posts:
                self.logger.warning(f"⚠️ Post ID not found: {post_id}")
                continue

            post_data = self.posts[post_id]
            url = post_data['url']
            title = post_data['title']

            self.logger.info(f"🚀 Processing: {title[:50]}...")

            if dry_run:
                self.logger.info(f"🔍 DRY RUN: Would process {url}")
                successful.append(post_id)
                continue

            try:
                # Update status to processing
                self.update_status([post_id], 'processing')

                # Run the summarize script
                result = subprocess.run(
                    [str(script_path), url],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                if result.returncode == 0:
                    self.logger.info(f"✅ Successfully processed: {title[:50]}...")
                    self.update_status([post_id], 'completed')
                    successful.append(post_id)
                else:
                    self.logger.error(f"❌ Failed to process: {title[:50]}...")
                    self.logger.error(f"Error output: {result.stderr}")
                    self.update_status([post_id], 'failed')
                    failed.append(post_id)

            except subprocess.TimeoutExpired:
                self.logger.error(f"⏰ Timeout processing: {title[:50]}...")
                self.update_status([post_id], 'failed')
                failed.append(post_id)
            except Exception as e:
                self.logger.error(f"❌ Error processing {title[:50]}...: {e}")
                self.update_status([post_id], 'failed')
                failed.append(post_id)

        # Log summary
        self.log_session_summary(
            total_attempted=len(post_ids),
            successful=len(successful),
            failed=len(failed),
            dry_run=dry_run
        )

        return successful

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about posts"""
        stats = {
            'total_posts': len(self.posts),
            'by_status': {},
            'by_platform': {},
            'by_source': {},
            'recent_activity': {}
        }

        # Count by status
        for post_data in self.posts.values():
            status = post_data.get('status', 'unknown')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1

        # Count by platform
        for post_data in self.posts.values():
            platform = post_data.get('platform', 'unknown')
            stats['by_platform'][platform] = stats['by_platform'].get(platform, 0) + 1

        # Count by source (simplified domain)
        for post_data in self.posts.values():
            source_feed = post_data.get('source_feed', '')
            if 'stratechery' in source_feed:
                source = 'stratechery'
            elif 'lennysnewsletter' in source_feed:
                source = 'lennysnewsletter'
            elif 'creatoreconomy' in source_feed:
                source = 'creatoreconomy'
            else:
                source = 'other'
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1

        # Recent activity (last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_count = 0
        for post_data in self.posts.values():
            if post_data.get('found_at'):
                try:
                    found_date = datetime.fromisoformat(post_data['found_at'].replace('T', ' ').replace('Z', ''))
                    if found_date >= seven_days_ago:
                        recent_count += 1
                except ValueError:
                    pass
        stats['recent_activity']['last_7_days'] = recent_count

        return stats

    def export_urls(self, post_ids: List[str], format: str = 'list') -> str:
        """Export URLs for external processing"""
        urls = []
        for post_id in post_ids:
            if post_id in self.posts:
                urls.append(self.posts[post_id]['url'])

        if format == 'list':
            return '\n'.join(urls)
        elif format == 'json':
            return json.dumps(urls, indent=2)
        elif format == 'csv':
            return '\n'.join([f'"{url}"' for url in urls])
        else:
            raise ValueError(f"Unsupported format: {format}")


def main():
    parser = argparse.ArgumentParser(description='Post Manager - Enhanced post tracking and batch processing')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # List command
    list_parser = subparsers.add_parser('list', help='List posts with filtering')
    list_parser.add_argument('--status', choices=['discovered', 'processing', 'completed', 'failed', 'skipped', 'queued'],
                            help='Filter by status')
    list_parser.add_argument('--since', help='Filter posts since date (YYYY-MM-DD)')
    list_parser.add_argument('--source', help='Filter by source feed (partial match)')
    list_parser.add_argument('--platform', choices=['rss_feed', 'generic'], help='Filter by platform')
    list_parser.add_argument('--limit', type=int, help='Limit number of results')
    list_parser.add_argument('--format', choices=['table', 'json', 'urls'], default='table',
                            help='Output format')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update post status')
    update_parser.add_argument('post_ids', nargs='+', help='Post IDs to update')
    update_parser.add_argument('--status', required=True,
                              choices=['discovered', 'processing', 'completed', 'failed', 'skipped', 'queued'],
                              help='New status')
    update_parser.add_argument('--summary-file', help='Path to summary file (for completed posts)')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process posts using summarize_article.sh')
    process_parser.add_argument('post_ids', nargs='+', help='Post IDs to process')
    process_parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without doing it')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show post statistics')

    # Bulk commands
    bulk_parser = subparsers.add_parser('bulk', help='Bulk operations')
    bulk_parser.add_argument('--status', help='Filter by status for bulk operation')
    bulk_parser.add_argument('--since', help='Filter posts since date (YYYY-MM-DD)')
    bulk_parser.add_argument('--source', help='Filter by source feed')
    bulk_parser.add_argument('--action', choices=['process', 'skip', 'queue'], required=True,
                            help='Bulk action to perform')
    bulk_parser.add_argument('--limit', type=int, default=10, help='Limit number of posts for bulk action')
    bulk_parser.add_argument('--dry-run', action='store_true', help='Preview bulk action without executing')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        manager = PostManager()

        if args.command == 'list':
            posts = manager.list_posts(
                status=args.status,
                since=args.since,
                source=args.source,
                platform=args.platform,
                limit=args.limit
            )

            if args.format == 'json':
                print(json.dumps(posts, indent=2))
            elif args.format == 'urls':
                for post in posts:
                    print(post['url'])
            else:  # table format
                if not posts:
                    print("No posts found matching criteria.")
                    return

                print(f"\n📊 Found {len(posts)} posts:")
                print("-" * 100)
                for post in posts:
                    status_emoji = {
                        'discovered': '🆕',
                        'processing': '⚙️',
                        'completed': '✅',
                        'failed': '❌',
                        'skipped': '⏭️',
                        'queued': '⏳'
                    }.get(post.get('status'), '❓')

                    published = post.get('published_date', 'Unknown')
                    if published and published != 'Unknown':
                        published = published[:10]  # Just the date part

                    print(f"{status_emoji} {post['title'][:60]}...")
                    print(f"   📅 {published} | 🆔 {post['post_id'][:8]}... | 🔗 {post.get('platform', 'unknown')}")
                    print(f"   🔗 {post['url'][:80]}...")
                    print()

        elif args.command == 'update':
            count = manager.update_status(args.post_ids, args.status, args.summary_file)
            print(f"✅ Updated {count} posts to status: {args.status}")

        elif args.command == 'process':
            successful = manager.process_posts(args.post_ids, args.dry_run)
            if args.dry_run:
                print(f"🔍 DRY RUN: Would process {len(successful)} posts")
            else:
                print(f"✅ Successfully processed {len(successful)} posts")

        elif args.command == 'stats':
            stats = manager.get_statistics()
            print("\n📊 Post Statistics:")
            print(f"📝 Total posts: {stats['total_posts']}")

            print("\n📈 By Status:")
            for status, count in stats['by_status'].items():
                emoji = {
                    'discovered': '🆕',
                    'processing': '⚙️',
                    'completed': '✅',
                    'failed': '❌',
                    'skipped': '⏭️',
                    'queued': '⏳'
                }.get(status, '❓')
                print(f"  {emoji} {status}: {count}")

            print("\n🌐 By Platform:")
            for platform, count in stats['by_platform'].items():
                print(f"  📡 {platform}: {count}")

            print("\n📰 By Source:")
            for source, count in stats['by_source'].items():
                print(f"  🔗 {source}: {count}")

            print(f"\n🕒 Recent Activity:")
            print(f"  📅 Last 7 days: {stats['recent_activity']['last_7_days']} posts")

        elif args.command == 'bulk':
            # Get posts matching criteria
            posts = manager.list_posts(
                status=args.status,
                since=args.since,
                source=args.source,
                limit=args.limit
            )

            if not posts:
                print("No posts found matching criteria.")
                return

            post_ids = [post['post_id'] for post in posts]

            if args.dry_run:
                print(f"🔍 DRY RUN: Would {args.action} {len(post_ids)} posts:")
                for post in posts[:5]:  # Show first 5 as preview
                    print(f"  - {post['title'][:60]}...")
                if len(posts) > 5:
                    print(f"  ... and {len(posts) - 5} more")
                return

            if args.action == 'process':
                successful = manager.process_posts(post_ids)
                print(f"✅ Bulk processed {len(successful)} posts")
            elif args.action == 'skip':
                count = manager.update_status(post_ids, 'skipped')
                print(f"⏭️ Bulk skipped {count} posts")
            elif args.action == 'queue':
                count = manager.update_status(post_ids, 'queued')
                print(f"⏳ Bulk queued {count} posts")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()