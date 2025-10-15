#!/usr/bin/env python3
"""
PocketCasts Podcast Checker - Tracks in-progress podcast episodes
Fetches from PocketCasts API and saves new episodes for processing
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import our base classes
sys.path.append(str(Path(__file__).parent.parent))
from common.base import BaseProcessor
from common.config import Config
from common.url_utils import generate_post_id
from common.pocketcasts_auth import PocketCastsAuth


class PocketCastsChecker(BaseProcessor):
    """Check PocketCasts for in-progress podcast episodes"""

    def __init__(self):
        super().__init__("pocketcasts_checker")

        # Setup specific files for podcast tracking
        self.podcasts_file = self.base_dir / "programs" / "check_new_posts" / "output" / "processed_podcasts_pocketcasts.json"

        # Initialize PocketCasts authentication
        self.pocketcasts_auth = PocketCastsAuth(self.logger)

        # Load existing podcasts
        self.podcasts = self._load_tracked_podcasts()

    def _load_tracked_podcasts(self) -> Dict[str, Any]:
        """Load previously tracked podcasts from JSON file"""
        try:
            if self.podcasts_file.exists():
                with open(self.podcasts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            self.logger.error(f"❌ Error loading podcasts: {e}")
            return {}

    def _save_tracked_podcasts(self, podcasts: Dict[str, Any]):
        """Save tracked podcasts to JSON file"""
        try:
            # Ensure directory exists
            self.podcasts_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.podcasts_file, 'w', encoding='utf-8') as f:
                json.dump(podcasts, f, indent=2, ensure_ascii=False)

            self.logger.info(f"💾 Saved {len(podcasts)} podcasts to {self.podcasts_file}")
        except Exception as e:
            self.logger.error(f"❌ Error saving podcasts: {e}")
            raise

    def _get_episode_hash(self, episode_uuid: str, episode_title: str) -> str:
        """
        Generate a unique hash for an episode

        Args:
            episode_uuid: PocketCasts episode UUID
            episode_title: Episode title

        Returns:
            Unique hash for the episode
        """
        # Use PocketCasts episode UUID as the primary identifier
        return generate_post_id(episode_title, episode_uuid)

    def _fetch_in_progress_episodes(self) -> List[Dict]:
        """
        Fetch listening history from PocketCasts (episodes with progress > 0)

        Returns:
            List of episodes with playback progress
        """
        headers = self.pocketcasts_auth.get_headers()
        if not headers:
            self.logger.error("❌ Failed to get authenticated headers")
            return []

        self.logger.info(f"🎵 Fetching listening history from PocketCasts...")

        try:
            import requests

            response = requests.post(
                "https://api.pocketcasts.com/user/history",
                headers=headers,
                json={}
            )

            response.raise_for_status()
            data = response.json()

            episodes = data.get('episodes', [])
            total = data.get('total', 0)

            # Filter for episodes that have been started (playedUpTo > 0)
            in_progress = [ep for ep in episodes if ep.get('playedUpTo', 0) > 0]

            self.logger.info(f"✅ Retrieved {total} total episodes, {len(in_progress)} with progress")

            return in_progress

        except Exception as e:
            self.logger.error(f"❌ Error fetching history: {e}")
            import traceback
            self.logger.debug(f"Full error traceback:\n{traceback.format_exc()}")
            return []

    def _search_podcast_full_url(self, episode_title: str, podcast_title: str) -> Optional[str]:
        """
        Search web for YouTube video or article URL for podcast episode

        Args:
            episode_title: Episode title
            podcast_title: Podcast name

        Returns:
            URL string (YouTube preferred) or None if not found
        """
        try:
            import requests
            from urllib.parse import quote_plus

            # Construct search query
            query = f"{podcast_title} {episode_title}"
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"

            self.logger.info(f"      🔍 [SEARCH] Searching for episode URL...")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(search_url, headers=headers, timeout=10)

            if response.status_code != 200:
                self.logger.warning(f"      ⚠️ [SEARCH] Search failed with status {response.status_code}")
                return None

            html = response.text

            # Look for YouTube URLs first (highest priority)
            import re
            youtube_patterns = [
                r'https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
                r'https://youtu\.be/([a-zA-Z0-9_-]{11})'
            ]

            for pattern in youtube_patterns:
                match = re.search(pattern, html)
                if match:
                    youtube_url = match.group(0)
                    self.logger.info(f"      ✅ [SEARCH] Found YouTube URL: {youtube_url[:60]}...")
                    return youtube_url

            # Fallback: Look for podcast host URLs (common podcast platforms)
            host_patterns = [
                r'https://[^"\s]+(?:podcasts\.apple\.com|spotify\.com/episode|pca\.st|overcast\.fm|castbox\.fm)[^"\s]+',
                r'https://[^"\s]+\.libsyn\.com[^"\s]+',
                r'https://[^"\s]+\.simplecast\.com[^"\s]+',
                r'https://[^"\s]+\.transistor\.fm[^"\s]+'
            ]

            for pattern in host_patterns:
                match = re.search(pattern, html)
                if match:
                    host_url = match.group(0).rstrip('"\'>')
                    self.logger.info(f"      ✅ [SEARCH] Found podcast host URL: {host_url[:60]}...")
                    return host_url

            self.logger.info(f"      ℹ️ [SEARCH] No YouTube or podcast URL found")
            return None

        except Exception as e:
            self.logger.warning(f"      ⚠️ [SEARCH] Error searching for URL: {e}")
            return None

    def _extract_episode_details(self, episode: Dict) -> Optional[Dict]:
        """
        Extract episode details from PocketCasts API response

        Args:
            episode: Episode from PocketCasts history API

        Returns:
            Dictionary with episode details
        """
        try:
            # Extract episode information (matching API response keys)
            episode_uuid = episode.get('uuid', '')
            episode_title = episode.get('title', 'Unknown Episode')
            podcast_title = episode.get('podcastTitle', 'Unknown Podcast')
            podcast_uuid = episode.get('podcastUuid', '')

            # Extract playback information
            duration = episode.get('duration', 0)  # in seconds
            played_up_to = episode.get('playedUpTo', 0)  # in seconds
            is_deleted = episode.get('isDeleted', False)
            playing_status = episode.get('playingStatus', 0)  # 1=unplayed, 2=playing, 3=played

            # Calculate progress
            progress_percent = (played_up_to / duration * 100) if duration > 0 else 0

            # Extract timestamps
            published_date = episode.get('published', '')

            # Build episode URL
            podcast_slug = episode.get('podcastSlug', '')
            episode_slug = episode.get('slug', '')
            if podcast_slug and episode_slug:
                episode_url = f"https://pocketcasts.com/{podcast_slug}/{episode_slug}"
            else:
                episode_url = f"https://pocketcasts.com/episode/{episode_uuid}"

            # Build episode details
            episode_details = {
                'episode_uuid': episode_uuid,
                'episode_title': episode_title,
                'podcast_title': podcast_title,
                'podcast_uuid': podcast_uuid,
                'duration': duration,
                'played_up_to': played_up_to,
                'progress_percent': progress_percent,
                'is_deleted': is_deleted,
                'playing_status': playing_status,
                'published_date': published_date,
                'episode_url': episode_url
            }

            return episode_details

        except Exception as e:
            self.logger.warning(f"⚠️ Error extracting episode details: {e}")
            return None

    def check_for_new_podcasts(self):
        """Main method to check PocketCasts for new podcast episodes"""
        self.logger.info("🎧 Starting PocketCasts podcast check...")

        # Load tracking data
        tracked_podcasts = self._load_tracked_podcasts()
        self.logger.info(f"📋 Loaded {len(tracked_podcasts)} previously tracked podcasts")

        new_podcasts_found = 0
        total_episodes_checked = 0
        new_podcasts_for_processing = []

        # Fetch in-progress episodes
        in_progress_episodes = self._fetch_in_progress_episodes()

        if not in_progress_episodes:
            self.logger.warning("❌ No in-progress episodes found")
            self.log_session_summary(
                total_episodes_checked=0,
                new_podcasts_discovered=0,
                total_tracked_podcasts=len(tracked_podcasts),
                summary="No in-progress episodes found"
            )
            return "No in-progress episodes found"

        self.logger.info(f"🔍 Processing {len(in_progress_episodes)} in-progress episodes...")

        # Process each episode
        for idx, episode in enumerate(in_progress_episodes, 1):
            # Extract episode details
            episode_details = self._extract_episode_details(episode)

            if not episode_details:
                continue  # Failed to extract details, skip

            total_episodes_checked += 1

            episode_uuid = episode_details['episode_uuid']
            episode_title = episode_details['episode_title']
            podcast_title = episode_details['podcast_title']
            progress = episode_details['progress_percent']
            playing_status = episode_details['playing_status']

            # Status mapping: 1=unplayed, 2=playing, 3=played
            status_text = {1: 'Unplayed', 2: 'In Progress', 3: 'Completed'}.get(playing_status, 'Unknown')

            self.logger.info(f"   🎙️ EPISODE {total_episodes_checked}: {episode_title[:60]}...")
            self.logger.info(f"      📺 Podcast: {podcast_title}")
            self.logger.info(f"      ▶️ Progress: {progress:.1f}% | Status: {status_text}")

            # Generate episode hash
            episode_hash = self._get_episode_hash(episode_uuid, episode_title)
            self.logger.info(f"      🆔 Episode hash: {episode_hash}")

            # Check if we've already tracked this episode
            if episode_hash not in tracked_podcasts:
                self.logger.info("      ✅ Episode is NEW (not in tracking database)")
                new_podcasts_found += 1

                # Search for full URL (YouTube or article)
                podcast_full_url = self._search_podcast_full_url(episode_title, podcast_title)

                # Add to processing list
                new_podcasts_for_processing.append({
                    'episode_title': episode_title,
                    'podcast_title': podcast_title,
                    'episode_url': episode_details['episode_url'],
                    'podcast_full_url': podcast_full_url,
                    'progress_percent': progress,
                    'playing_status': playing_status,
                    'status_text': status_text,
                    'published_date': episode_details['published_date'],
                    'episode_hash': episode_hash
                })

                # Track this episode
                tracked_podcasts[episode_hash] = {
                    'episode_title': episode_title,
                    'podcast_title': podcast_title,
                    'podcast_uuid': episode_details['podcast_uuid'],
                    'episode_uuid': episode_uuid,
                    'episode_url': episode_details['episode_url'],
                    'podcast_full_url': podcast_full_url,
                    'duration': episode_details['duration'],
                    'played_up_to': episode_details['played_up_to'],
                    'progress_percent': progress,
                    'playing_status': playing_status,
                    'published_date': episode_details['published_date'],
                    'found_at': datetime.now().isoformat(),
                    'status': 'discovered',
                    'platform': 'pocketcasts'
                }

                self.logger.info(f"      📋 NEW PODCAST ADDED TO TRACKING")
            else:
                self.logger.info(f"      ♻️ Episode already tracked, skipping...")

        # Clean up old tracking entries (older than 30 days)
        self.logger.info(f"🧹 Cleaning up old tracking entries (>{Config.TRACKING_CLEANUP_DAYS} days)...")
        cutoff_date = datetime.now() - timedelta(days=Config.TRACKING_CLEANUP_DAYS)
        cleaned_tracked = {}
        removed_count = 0

        for episode_hash, episode_data in tracked_podcasts.items():
            try:
                found_at = datetime.fromisoformat(episode_data.get('found_at', ''))
                if found_at > cutoff_date:
                    cleaned_tracked[episode_hash] = episode_data
                else:
                    removed_count += 1
                    self.logger.info(f"   🗑️ Removing old entry: {episode_data.get('episode_title', 'Unknown')[:40]}...")
            except:
                # Keep entries without valid dates
                cleaned_tracked[episode_hash] = episode_data

        self.logger.info(f"   📊 Cleanup complete: Removed {removed_count} old entries")

        # Save updated tracking data
        self._save_tracked_podcasts(cleaned_tracked)

        # Show summary of new podcasts
        output_summary = None
        if new_podcasts_for_processing:
            output_summary = self._show_new_podcasts_summary(new_podcasts_for_processing)

        # Log session summary
        self.log_session_summary(
            total_episodes_checked=total_episodes_checked,
            new_podcasts_discovered=new_podcasts_found,
            total_tracked_podcasts=len(cleaned_tracked),
            summary=output_summary or "No new podcasts found"
        )

        if new_podcasts_found > 0:
            self.logger.info(f"🎉 SUCCESS: Found {new_podcasts_found} new podcast episodes!")
        else:
            self.logger.info("✨ No new podcast episodes found")

        return output_summary

    def _show_new_podcasts_summary(self, new_podcasts: List[Dict]) -> str:
        """Show summary of new podcast episodes found"""
        try:
            if not new_podcasts:
                return None

            self.logger.info(f"📋 Found {len(new_podcasts)} new podcast episodes:")
            self.logger.info("=" * 80)

            for i, podcast in enumerate(new_podcasts, 1):
                published_date = podcast.get('published_date', 'Unknown')
                if published_date and published_date != 'Unknown':
                    # Format timestamp
                    try:
                        published_dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        published_date = published_dt.strftime('%Y-%m-%d')
                    except:
                        pass

                progress = podcast.get('progress_percent', 0)
                status_text = podcast.get('status_text', 'Unknown')

                self.logger.info(f"{i}. {podcast['episode_title'][:70]}...")
                self.logger.info(f"   🎙️ {podcast['podcast_title']}")
                self.logger.info(f"   ▶️ {status_text}: {progress:.1f}% | Published: {published_date}")

                # Show podcast_full_url if available
                if podcast.get('podcast_full_url'):
                    self.logger.info(f"   🌐 Full URL: {podcast['podcast_full_url']}")

                self.logger.info(f"   🔗 PocketCasts: {podcast['episode_url']}")

            self.logger.info("=" * 80)
            self.logger.info("💡 These podcast episodes have been tracked.")
            self.logger.info("   Future integration: Process with article summarizer for transcripts")

            return f"Found {len(new_podcasts)} new podcast episodes"

        except Exception as e:
            self.logger.error(f"❌ Error showing podcast summary: {e}")
            return None


def main():
    """Main entry point"""
    checker = PocketCastsChecker()

    try:
        summary = checker.check_for_new_podcasts()
        # Print summary to stdout for shell script to capture (if any new podcasts found)
        if summary:
            print(summary)
    except KeyboardInterrupt:
        checker.logger.info("Process interrupted by user")
    except Exception as e:
        checker.logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
