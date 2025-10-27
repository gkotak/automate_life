"""
Podcast checking service - refactored for API usage
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from supabase import create_client, Client

from core.podcast_auth import PodcastAuth


class PodcastCheckerService:
    """Service for checking PocketCasts for new podcast episodes"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.logger.info("Connected to Supabase")

        # Initialize PocketCasts authentication
        self.podcast_auth = PodcastAuth(self.logger)

    async def check_for_new_podcasts(self) -> Dict:
        """
        Check PocketCasts for new podcast episodes

        Returns:
            Dictionary with results including newly_discovered_ids
        """
        self.logger.info("Starting PocketCasts podcast check...")

        # Fetch in-progress episodes
        in_progress_episodes = await self._fetch_in_progress_episodes()

        if not in_progress_episodes:
            self.logger.warning("No episodes found in PocketCasts history")
            return {
                "new_podcasts_found": 0,
                "total_episodes_checked": 0,
                "message": "No episodes found in PocketCasts history",
                "newly_discovered_ids": []
            }

        self.logger.info(f"Processing {len(in_progress_episodes)} episodes from history...")

        new_podcasts_found = 0
        total_episodes_checked = 0
        newly_discovered_ids = []

        # Load existing podcasts from database
        existing_urls = self._get_existing_podcast_urls()

        # Process each episode
        for episode in in_progress_episodes:
            episode_details = self._extract_episode_details(episode)

            if not episode_details:
                continue

            total_episodes_checked += 1

            episode_url = episode_details['episode_url']

            # Check if we've already tracked this episode
            if episode_url not in existing_urls:
                self.logger.info(f"New episode found: {episode_details['episode_title']}")
                new_podcasts_found += 1

                # Save to database and get the ID
                episode_id = self._save_podcast_episode(episode_details)
                if episode_id:
                    newly_discovered_ids.append(episode_id)

        message = f"Found {new_podcasts_found} new podcast episodes" if new_podcasts_found > 0 else "No new podcasts found"

        self.logger.info(f"Check complete: {message}")

        return {
            "new_podcasts_found": new_podcasts_found,
            "total_episodes_checked": total_episodes_checked,
            "message": message,
            "newly_discovered_ids": newly_discovered_ids
        }

    async def _fetch_in_progress_episodes(self) -> List[Dict]:
        """
        Fetch listening history from PocketCasts web page using centralized browser_fetcher

        Returns:
            List of all episodes from history
        """
        from core.browser_fetcher import BrowserFetcher
        from bs4 import BeautifulSoup
        import json

        # Get cookies from auth
        cookies = self.podcast_auth.get_cookies()
        if not cookies:
            self.logger.error("Failed to get authentication cookies")
            return []

        # Use centralized browser fetcher
        browser_fetcher = BrowserFetcher(self.logger)
        if not browser_fetcher.is_available():
            self.logger.error("Browser fetcher not available (Playwright not installed)")
            return []

        self.logger.info("Fetching listening history from PocketCasts using centralized browser fetcher...")

        try:
            # Fetch page content using browser fetcher
            history_url = "https://pocketcasts.com/history"
            success, content, message = await browser_fetcher.fetch_with_playwright_async(history_url, cookies)

            if not success or not content:
                self.logger.error(f"Failed to fetch history page: {message}")
                return []

            # Parse the page to extract episode data
            soup = BeautifulSoup(content, 'html.parser')
            episodes = []

            # Look for JSON data embedded in script tags
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                try:
                    data = json.loads(script.string)

                    # Navigate through the JSON structure to find episodes
                    if isinstance(data, dict):
                        # Try common paths where episode data might be
                        props = data.get('props', {})
                        page_props = props.get('pageProps', {})

                        # Look for episodes array
                        if 'episodes' in page_props:
                            episodes = page_props['episodes']
                            break
                        elif 'history' in page_props:
                            episodes = page_props.get('history', {}).get('episodes', [])
                            break
                        elif 'initialData' in page_props:
                            initial_data = page_props['initialData']
                            episodes = initial_data.get('episodes', [])
                            break

                except Exception as e:
                    self.logger.debug(f"Error parsing script tag: {e}")
                    continue

            if not episodes:
                self.logger.warning("No episodes found in page data")
                self.logger.debug(f"Page title: {soup.title.string if soup.title else 'No title'}")

            self.logger.info(f"Retrieved {len(episodes)} episodes from history")

            return episodes

        except Exception as e:
            self.logger.error(f"Error fetching history: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return []

    def _extract_episode_details(self, episode: Dict) -> Optional[Dict]:
        """
        Extract episode details from PocketCasts API response

        Args:
            episode: Episode from PocketCasts history API

        Returns:
            Dictionary with episode details
        """
        try:
            episode_uuid = episode.get('uuid', '')
            episode_title = episode.get('title', 'Unknown Episode')
            podcast_title = episode.get('podcastTitle', 'Unknown Podcast')
            podcast_uuid = episode.get('podcastUuid', '')

            duration = episode.get('duration', 0)
            played_up_to = episode.get('playedUpTo', 0)
            playing_status = episode.get('playingStatus', 0)

            progress_percent = (played_up_to / duration * 100) if duration > 0 else 0

            published_date = episode.get('published', '')

            # Build episode URL
            podcast_slug = episode.get('podcastSlug', '')
            episode_slug = episode.get('slug', '')
            if podcast_slug and episode_slug and podcast_uuid and episode_uuid:
                episode_url = f"https://pocketcasts.com/podcast/{podcast_slug}/{podcast_uuid}/{episode_slug}/{episode_uuid}"
            else:
                episode_url = f"https://pocketcasts.com/episode/{episode_uuid}"

            return {
                'episode_uuid': episode_uuid,
                'episode_title': episode_title,
                'podcast_title': podcast_title,
                'podcast_uuid': podcast_uuid,
                'duration': duration,
                'played_up_to': played_up_to,
                'progress_percent': progress_percent,
                'playing_status': playing_status,
                'published_date': published_date,
                'episode_url': episode_url
            }

        except Exception as e:
            self.logger.warning(f"Error extracting episode details: {e}")
            return None

    def _get_existing_podcast_urls(self) -> set:
        """Get all existing podcast URLs from database"""
        try:
            result = self.supabase.table('content_queue').select('url').eq(
                'content_type', 'podcast_episode'
            ).execute()

            return set(row['url'] for row in result.data)

        except Exception as e:
            self.logger.error(f"Error fetching existing podcasts: {e}")
            return set()

    def _save_podcast_episode(self, episode_details: Dict) -> Optional[str]:
        """
        Save podcast episode to database

        Returns:
            The ID of the saved episode, or None on error
        """
        try:
            record = {
                'url': episode_details['episode_url'],
                'title': episode_details['episode_title'],
                'content_type': 'podcast_episode',
                'channel_title': episode_details['podcast_title'],
                'channel_url': f"https://pocketcasts.com/podcast/{episode_details['podcast_uuid']}",
                'video_url': None,  # Can be enhanced with YouTube search later
                'platform': 'pocketcasts',
                'source_feed': None,
                'found_at': datetime.now().isoformat(),
                'published_date': episode_details.get('published_date'),
                'status': 'discovered',
                'podcast_uuid': episode_details['podcast_uuid'],
                'episode_uuid': episode_details['episode_uuid'],
                'duration_seconds': episode_details.get('duration'),
                'played_up_to': episode_details.get('played_up_to'),
                'progress_percent': episode_details.get('progress_percent'),
                'playing_status': episode_details.get('playing_status')
            }

            result = self.supabase.table('content_queue').upsert(
                record,
                on_conflict='url'
            ).execute()

            self.logger.info(f"Saved podcast episode: {episode_details['episode_title']}")

            # Return the ID if available
            if result.data and len(result.data) > 0:
                return result.data[0].get('id')
            return None

        except Exception as e:
            self.logger.error(f"Error saving podcast episode: {e}")
            raise

    async def get_discovered_podcasts(self, limit: int = 100) -> List[Dict]:
        """
        Get discovered podcast episodes from database

        Args:
            limit: Maximum number of podcasts to return

        Returns:
            List of podcast episodes
        """
        try:
            result = self.supabase.table('content_queue').select('*').eq(
                'content_type', 'podcast_episode'
            ).order('found_at', desc=True).limit(limit).execute()

            podcasts = []
            for row in result.data:
                # Check if this is new (found in last 24 hours)
                is_new = False
                if row.get('found_at'):
                    try:
                        found_at = datetime.fromisoformat(row['found_at'].replace('Z', '+00:00'))
                        is_new = (datetime.now() - found_at.replace(tzinfo=None)).total_seconds() < 86400
                    except:
                        pass

                podcasts.append({
                    'id': row.get('id'),
                    'episode_title': row.get('title', ''),
                    'podcast_title': row.get('channel_title', ''),
                    'episode_url': row.get('url', ''),
                    'podcast_video_url': row.get('video_url'),
                    'progress_percent': float(row.get('progress_percent', 0)) if row.get('progress_percent') else None,
                    'published_date': row.get('published_date'),
                    'found_at': row.get('found_at'),
                    'status': row.get('status', 'discovered'),
                    'is_new': is_new,
                    'duration_seconds': row.get('duration_seconds')
                })

            return podcasts

        except Exception as e:
            self.logger.error(f"Error fetching discovered podcasts: {e}")
            raise
