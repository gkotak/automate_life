#!/usr/bin/env python3
"""
Legacy URL Migration Tool
Migrates data from found_urls_*.md files to JSON format and cleans up redundant files
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Import our base class
sys.path.append(str(Path(__file__).parent.parent))
from common.base import BaseProcessor
from common.url_utils import normalize_url, generate_post_id


class LegacyMigrator(BaseProcessor):
    def __init__(self):
        super().__init__("legacy_migrator")
        self.posts_file = self.base_dir / "programs" / "video_summarizer" / "output" / "processed_posts.json"

    def _load_existing_posts(self) -> Dict[str, Any]:
        """Load existing posts from JSON file"""
        try:
            if self.posts_file.exists():
                with open(self.posts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"❌ Error loading existing posts: {e}")
            return {}

    def _save_posts(self, posts: Dict[str, Any]):
        """Save posts to JSON file"""
        try:
            with open(self.posts_file, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
            self.logger.info(f"💾 Posts saved to {self.posts_file}")
        except Exception as e:
            self.logger.error(f"❌ Error saving posts: {e}")
            raise

    def _generate_post_id(self, title: str, url: str) -> str:
        """
        Generate a unique ID for a post based on title and normalized base URL.
        This prevents duplicate entries when URLs have different parameters.
        """
        return generate_post_id(title, url)

    def _parse_markdown_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse a found_urls_*.md file and extract post data"""
        posts = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract timestamp from filename (found_urls_YYYYMMDD_HHMMSS.md)
            timestamp_match = re.search(r'found_urls_(\d{8}_\d{6})\.md', file_path.name)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                found_at = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S').isoformat()
            else:
                # Fallback to file modification time
                found_at = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()

            # Parse the markdown content
            # Look for numbered list items with title and URL
            current_post = {}

            lines = content.split('\n')
            for line in lines:
                line = line.strip()

                # Match numbered items like "1. **Title**"
                title_match = re.match(r'^\d+\.\s*\*\*(.+?)\*\*', line)
                if title_match:
                    if current_post and 'title' in current_post and 'url' in current_post:
                        posts.append(current_post)

                    current_post = {
                        'title': title_match.group(1),
                        'found_at': found_at,
                        'status': 'discovered'
                    }
                    continue

                # Match URL lines like "   - URL: https://..."
                url_match = re.match(r'^\s*-\s*URL:\s*(.+)', line)
                if url_match and current_post:
                    current_post['url'] = url_match.group(1).strip()
                    continue

                # Match Platform lines like "   - Platform: rss_feed"
                platform_match = re.match(r'^\s*-\s*Platform:\s*(.+)', line)
                if platform_match and current_post:
                    current_post['platform'] = platform_match.group(1).strip()
                    continue

                # Match Source lines like "   - Source: https://..."
                source_match = re.match(r'^\s*-\s*Source:\s*(.+)', line)
                if source_match and current_post:
                    current_post['source_feed'] = source_match.group(1).strip()
                    continue

                # Match Published lines like "   - Published: 2025-10-01T10:00:00"
                published_match = re.match(r'^\s*-\s*Published:\s*(.+)', line)
                if published_match and current_post:
                    current_post['published_date'] = published_match.group(1).strip()
                    continue

            # Don't forget the last post
            if current_post and 'title' in current_post and 'url' in current_post:
                posts.append(current_post)

            self.logger.info(f"📋 Parsed {len(posts)} posts from {file_path.name}")
            return posts

        except Exception as e:
            self.logger.error(f"❌ Error parsing {file_path}: {e}")
            return []

    def find_legacy_files(self) -> List[Path]:
        """Find all found_urls_*.md files"""
        video_dir = self.base_dir / "programs" / "video_summarizer"
        pattern = "found_urls_*.md"

        legacy_files = list(video_dir.glob(pattern))
        self.logger.info(f"🔍 Found {len(legacy_files)} legacy markdown files")

        for file_path in legacy_files:
            self.logger.info(f"   📄 {file_path.name}")

        return legacy_files

    def migrate_legacy_files(self, dry_run: bool = False) -> Dict[str, int]:
        """Migrate all legacy markdown files to JSON format"""
        legacy_files = self.find_legacy_files()

        if not legacy_files:
            self.logger.info("✨ No legacy files found to migrate")
            return {'files_processed': 0, 'posts_migrated': 0, 'duplicates_skipped': 0}

        # Load existing posts
        existing_posts = self._load_existing_posts()

        stats = {
            'files_processed': 0,
            'posts_migrated': 0,
            'duplicates_skipped': 0
        }

        for file_path in legacy_files:
            self.logger.info(f"🔄 Processing {file_path.name}...")

            posts_from_file = self._parse_markdown_file(file_path)
            stats['files_processed'] += 1

            for post_data in posts_from_file:
                post_id = self._generate_post_id(post_data['title'], post_data['url'])

                if post_id in existing_posts:
                    self.logger.info(f"   ⚠️ Duplicate skipped: {post_data['title'][:50]}...")
                    stats['duplicates_skipped'] += 1
                else:
                    if not dry_run:
                        existing_posts[post_id] = post_data
                    self.logger.info(f"   ✅ Migrated: {post_data['title'][:50]}...")
                    stats['posts_migrated'] += 1

        if not dry_run and stats['posts_migrated'] > 0:
            self._save_posts(existing_posts)
            self.logger.info(f"💾 Saved {len(existing_posts)} total posts ({stats['posts_migrated']} new)")

        return stats

    def cleanup_legacy_files(self, dry_run: bool = False) -> int:
        """Remove legacy markdown files after successful migration"""
        legacy_files = self.find_legacy_files()

        if not legacy_files:
            return 0

        if dry_run:
            self.logger.info(f"🔍 DRY RUN: Would delete {len(legacy_files)} legacy files")
            return len(legacy_files)

        deleted_count = 0
        for file_path in legacy_files:
            try:
                file_path.unlink()
                self.logger.info(f"🗑️ Deleted: {file_path.name}")
                deleted_count += 1
            except Exception as e:
                self.logger.error(f"❌ Error deleting {file_path.name}: {e}")

        return deleted_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Migrate legacy found_urls_*.md files to JSON format')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually doing it')
    parser.add_argument('--cleanup', action='store_true', help='Delete legacy markdown files after migration')
    parser.add_argument('--list-only', action='store_true', help='Only list legacy files, don\'t migrate')

    args = parser.parse_args()

    try:
        migrator = LegacyMigrator()

        if args.list_only:
            migrator.find_legacy_files()
            return

        # Perform migration
        stats = migrator.migrate_legacy_files(dry_run=args.dry_run)

        print(f"\n📊 Migration Summary:")
        print(f"   📄 Files processed: {stats['files_processed']}")
        print(f"   ✅ Posts migrated: {stats['posts_migrated']}")
        print(f"   ⚠️ Duplicates skipped: {stats['duplicates_skipped']}")

        if args.cleanup and not args.dry_run:
            if stats['posts_migrated'] > 0:
                deleted_count = migrator.cleanup_legacy_files(dry_run=False)
                print(f"   🗑️ Legacy files deleted: {deleted_count}")
            else:
                print("   💡 No cleanup performed (no new posts migrated)")
        elif args.cleanup and args.dry_run:
            deleted_count = migrator.cleanup_legacy_files(dry_run=True)
            print(f"   🔍 Would delete {deleted_count} legacy files")

        if args.dry_run:
            print("\n🔍 This was a dry run. Use without --dry-run to perform actual migration.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()