#!/usr/bin/env python3
"""
Spotify Podcast Checker - Tracks recently played podcast episodes
Fetches from Spotify API and saves new episodes for processing
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

# Import our base classes
sys.path.append(str(Path(__file__).parent.parent))
from common.base import BaseProcessor
from common.config import Config
from common.url_utils import generate_post_id
from common.spotify_auth import SpotifyAuth


class PodcastChecker(BaseProcessor):
    """Check Spotify for recently played podcast episodes"""

    # Spotify API endpoints
    SAVED_EPISODES_URL = "https://api.spotify.com/v1/me/episodes"
    SHOW_URL = "https://api.spotify.com/v1/shows"
    EPISODE_URL = "https://api.spotify.com/v1/episodes"

    def __init__(self):
        super().__init__("podcast_checker")

        # Setup specific files for podcast tracking
        self.podcasts_file = self.base_dir / "programs" / "check_new_posts" / "output" / "processed_podcasts.json"

        # Initialize Spotify authentication
        self.spotify_auth = SpotifyAuth(self.base_dir, self.logger)

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

    def _get_episode_hash(self, episode_id: str, episode_name: str) -> str:
        """
        Generate a unique hash for an episode

        Args:
            episode_id: Spotify episode ID
            episode_name: Episode name

        Returns:
            Unique hash for the episode
        """
        # Use Spotify's episode ID as the primary identifier
        return generate_post_id(episode_name, episode_id)

    def _fetch_saved_episodes(self, limit: int = 50) -> List[Dict]:
        """
        Fetch user's saved podcast episodes from Spotify

        Args:
            limit: Maximum number of items to fetch (max 50)

        Returns:
            List of saved episode items with playback position
        """
        # Get valid access token
        access_token = self.spotify_auth.get_valid_token()
        if not access_token:
            self.logger.error("❌ Failed to get valid Spotify access token")
            return []

        self.logger.info(f"🎵 Fetching saved podcast episodes from Spotify...")

        try:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }

            params = {
                'limit': min(limit, 50)  # API maximum is 50
            }

            response = requests.get(
                self.SAVED_EPISODES_URL,
                headers=headers,
                params=params,
                timeout=Config.DEFAULT_TIMEOUT
            )

            response.raise_for_status()
            data = response.json()

            items = data.get('items', [])
            self.logger.info(f"✅ Retrieved {len(items)} saved episodes")

            return items

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Error fetching saved episodes: {e}")
            return []

    def _extract_episode_details(self, item: Dict) -> Optional[Dict]:
        """
        Extract episode details from Spotify saved episodes API response

        Args:
            item: Saved episode item from Spotify (/me/episodes)

        Returns:
            Dictionary with episode details including playback position
        """
        try:
            # Extract episode information (saved episodes API uses 'episode' key)
            episode = item.get('episode', {})

            episode_id = episode.get('id')
            episode_name = episode.get('name')
            episode_description = episode.get('description', '')
            duration_ms = episode.get('duration_ms')
            release_date = episode.get('release_date')

            # Extract show information
            show = episode.get('show', {})
            show_name = show.get('name', 'Unknown Show')
            show_id = show.get('id')
            show_publisher = show.get('publisher', '')

            # Extract URLs
            episode_uri = episode.get('uri')  # spotify:episode:xxx
            external_urls = episode.get('external_urls', {})
            web_url = external_urls.get('spotify', '')

            # Extract when the episode was added to library
            added_at = item.get('added_at')

            # Extract playback position (resume point)
            resume_point = episode.get('resume_point', {})
            fully_played = resume_point.get('fully_played', False)
            resume_position_ms = resume_point.get('resume_position_ms', 0)

            # Build episode details
            episode_details = {
                'episode_id': episode_id,
                'episode_name': episode_name,
                'episode_description': episode_description[:200] if episode_description else '',
                'show_name': show_name,
                'show_id': show_id,
                'show_publisher': show_publisher,
                'duration_ms': duration_ms,
                'release_date': release_date,
                'episode_uri': episode_uri,
                'web_url': web_url,
                'added_at': added_at,
                'fully_played': fully_played,
                'resume_position_ms': resume_position_ms,
                'progress_percent': (resume_position_ms / duration_ms * 100) if duration_ms else 0
            }

            return episode_details

        except Exception as e:
            self.logger.warning(f"⚠️ Error extracting episode details: {e}")
            return None

    def _get_show_rss_feed(self, show_id: str) -> Optional[str]:
        """
        Attempt to get RSS feed URL for a show

        Note: Spotify API doesn't directly provide RSS feeds, but we can try to
        fetch show details which might include external links

        Args:
            show_id: Spotify show ID

        Returns:
            RSS feed URL if available, None otherwise
        """
        # Get valid access token
        access_token = self.spotify_auth.get_valid_token()
        if not access_token:
            return None

        try:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }

            response = requests.get(
                f"{self.SHOW_URL}/{show_id}",
                headers=headers,
                timeout=Config.SHORT_TIMEOUT
            )

            response.raise_for_status()
            data = response.json()

            # Spotify API doesn't provide RSS feeds directly
            # This is a placeholder for potential future implementation
            # You might need to use external services or maintain a mapping

            return None

        except Exception as e:
            self.logger.debug(f"Could not fetch show details for RSS feed: {e}")
            return None

    def check_for_new_podcasts(self):
        """Main method to check Spotify for new podcast episodes"""
        self.logger.info("🎧 Starting Spotify podcast check...")

        # Load tracking data
        tracked_podcasts = self._load_tracked_podcasts()
        self.logger.info(f"📋 Loaded {len(tracked_podcasts)} previously tracked podcasts")

        new_podcasts_found = 0
        total_episodes_checked = 0
        new_podcasts_for_processing = []

        # Fetch saved episodes
        saved_episodes = self._fetch_saved_episodes(limit=50)

        if not saved_episodes:
            self.logger.warning("❌ No saved episodes found")
            self.log_session_summary(
                total_episodes_checked=0,
                new_podcasts_discovered=0,
                total_tracked_podcasts=len(tracked_podcasts),
                summary="No saved episodes found"
            )
            return "No saved episodes found"

        self.logger.info(f"🔍 Processing {len(saved_episodes)} saved episodes...")

        # Process each item
        for idx, item in enumerate(saved_episodes, 1):
            # Extract episode details
            episode_details = self._extract_episode_details(item)

            if not episode_details:
                continue  # Failed to extract details, skip

            total_episodes_checked += 1

            episode_id = episode_details['episode_id']
            episode_name = episode_details['episode_name']
            show_name = episode_details['show_name']
            progress = episode_details['progress_percent']
            fully_played = episode_details['fully_played']

            self.logger.info(f"   🎙️ EPISODE {total_episodes_checked}: {episode_name[:60]}...")
            self.logger.info(f"      📺 Show: {show_name}")
            self.logger.info(f"      ▶️ Progress: {progress:.1f}% {'✓ Fully played' if fully_played else ''}")

            # Generate episode hash
            episode_hash = self._get_episode_hash(episode_id, episode_name)
            self.logger.info(f"      🆔 Episode hash: {episode_hash}")

            # Check if we've already tracked this episode
            if episode_hash not in tracked_podcasts:
                # Only track episodes that have been started (progress > 0)
                if progress > 0:
                    self.logger.info("      ✅ Episode is NEW and has been started")
                    new_podcasts_found += 1

                    # Attempt to get RSS feed (may not be available)
                    show_rss_feed = self._get_show_rss_feed(episode_details['show_id'])

                    # Add to processing list
                    new_podcasts_for_processing.append({
                        'episode_name': episode_name,
                        'show_name': show_name,
                        'web_url': episode_details['web_url'],
                        'added_at': episode_details['added_at'],
                        'progress_percent': progress,
                        'fully_played': fully_played,
                        'episode_hash': episode_hash
                    })

                    # Track this episode
                    tracked_podcasts[episode_hash] = {
                        'episode_title': episode_name,
                        'episode_description': episode_details['episode_description'],
                        'show_name': show_name,
                        'show_publisher': episode_details['show_publisher'],
                        'show_id': episode_details['show_id'],
                        'episode_id': episode_id,
                        'episode_url': episode_details['episode_uri'],
                        'web_url': episode_details['web_url'],
                        'show_rss_feed': show_rss_feed,
                        'duration_ms': episode_details['duration_ms'],
                        'release_date': episode_details['release_date'],
                        'added_at': episode_details['added_at'],
                        'progress_percent': progress,
                        'fully_played': fully_played,
                        'found_at': datetime.now().isoformat(),
                        'status': 'discovered',
                        'platform': 'spotify_podcast'
                    }

                    self.logger.info(f"      📋 NEW PODCAST ADDED TO TRACKING")
                else:
                    self.logger.info("      ⏭️ Episode not started yet, skipping...")
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
                added_at = podcast.get('added_at', 'Unknown')
                if added_at and added_at != 'Unknown':
                    # Format timestamp
                    try:
                        added_dt = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                        added_at = added_dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        pass

                progress = podcast.get('progress_percent', 0)
                fully_played = podcast.get('fully_played', False)
                status = '✓ Completed' if fully_played else f'{progress:.1f}% played'

                self.logger.info(f"{i}. {podcast['episode_name'][:70]}...")
                self.logger.info(f"   🎙️ {podcast['show_name']} | ⏰ Added: {added_at}")
                self.logger.info(f"   ▶️ Status: {status}")
                self.logger.info(f"   🔗 {podcast['web_url']}")

            self.logger.info("=" * 80)
            self.logger.info("💡 These podcast episodes have been tracked.")
            self.logger.info("   Future integration: Process with article summarizer for transcripts")

            return f"Found {len(new_podcasts)} new podcast episodes"

        except Exception as e:
            self.logger.error(f"❌ Error showing podcast summary: {e}")
            return None


def main():
    """Main entry point"""
    checker = PodcastChecker()

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
