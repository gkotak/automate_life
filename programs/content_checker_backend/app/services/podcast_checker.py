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
        Fetch listening history from PocketCasts web page

        Returns:
            List of all episodes from history
        """
        from bs4 import BeautifulSoup
        import json

        # Fetch history page HTML (authentication happens inside this method)
        content = await self.podcast_auth.fetch_history_page()
        if not content:
            self.logger.error("Failed to fetch history page")
            return []

        self.logger.info("Parsing history page for episodes...")

        try:
            # Check if content is JSON (from API interception) or HTML
            episodes = []

            try:
                # Try parsing as JSON first (from API interception)
                api_responses = json.loads(content)
                self.logger.info(f"Content is JSON with {len(api_responses)} API responses")

                # Extract episodes from API responses - ONLY from history endpoint
                seen_episode_ids = set()
                history_responses = [r for r in api_responses if isinstance(r, dict) and '/user/history' in r.get('url', '')]

                self.logger.info(f"Found {len(history_responses)} history API responses (out of {len(api_responses)} total)")

                for idx, response in enumerate(history_responses):
                    url = response.get('url', '')
                    self.logger.info(f"Processing history response {idx + 1}/{len(history_responses)}: {url}")

                    # Handle wrapped response format (with url, status, data)
                    data = response.get('data', response)

                    if 'episodes' in data:
                        # Deduplicate episodes by ID
                        new_episodes = []
                        for ep in data['episodes']:
                            ep_id = ep.get('uuid', '')
                            if ep_id and ep_id not in seen_episode_ids:
                                seen_episode_ids.add(ep_id)
                                new_episodes.append(ep)

                        self.logger.info(f"  └─ {len(data['episodes'])} episodes in response ({len(new_episodes)} new, {len(data['episodes']) - len(new_episodes)} duplicates)")
                        episodes.extend(new_episodes)
                    elif 'history' in data:
                        history_data = data['history']
                        if isinstance(history_data, list):
                            self.logger.info(f"  └─ 'history' list with {len(history_data)} items")
                            episodes.extend(history_data)
                        elif isinstance(history_data, dict) and 'episodes' in history_data:
                            self.logger.info(f"  └─ 'history.episodes' with {len(history_data['episodes'])} items")
                            episodes.extend(history_data['episodes'])

                if episodes:
                    self.logger.info(f"✅ Extracted {len(episodes)} episodes from API responses")
                    return episodes
                else:
                    self.logger.warning(f"⚠️  No episodes found in {len(api_responses)} API responses")

            except json.JSONDecodeError:
                # Not JSON, fallback to HTML parsing
                self.logger.info("Content is not JSON, parsing as HTML...")

            # Parse the page to extract episode data from HTML
            soup = BeautifulSoup(content, 'html.parser')

            # Look for JSON data embedded in script tags
            scripts = soup.find_all('script', type='application/json')
            self.logger.info(f"Found {len(scripts)} script tags with type='application/json'")

            for idx, script in enumerate(scripts):
                try:
                    if not script.string:
                        continue

                    data = json.loads(script.string)

                    # Log the structure for debugging
                    if isinstance(data, dict):
                        self.logger.info(f"Script {idx} keys: {list(data.keys())}")

                        # Try common paths where episode data might be
                        props = data.get('props', {})
                        page_props = props.get('pageProps', {})

                        if props:
                            self.logger.info(f"Script {idx} has 'props' with keys: {list(props.keys())}")
                        if page_props:
                            self.logger.info(f"Script {idx} pageProps keys: {list(page_props.keys())}")

                        # Look for episodes array in various locations
                        if 'episodes' in page_props:
                            episodes = page_props['episodes']
                            self.logger.info(f"Found episodes in pageProps.episodes: {len(episodes)} episodes")
                            break
                        elif 'history' in page_props:
                            episodes = page_props.get('history', {}).get('episodes', [])
                            if episodes:
                                self.logger.info(f"Found episodes in pageProps.history.episodes: {len(episodes)} episodes")
                                break
                        elif 'initialData' in page_props:
                            initial_data = page_props['initialData']
                            episodes = initial_data.get('episodes', [])
                            if episodes:
                                self.logger.info(f"Found episodes in pageProps.initialData.episodes: {len(episodes)} episodes")
                                break

                except Exception as e:
                    self.logger.debug(f"Error parsing script tag {idx}: {e}")
                    continue

            if not episodes:
                self.logger.warning("No episodes found in page data")
                self.logger.info(f"Page title: {soup.title.string if soup.title else 'No title'}")
                # Save the HTML for manual inspection
                with open('/tmp/pocketcasts_history_debug.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                self.logger.info("Saved HTML to /tmp/pocketcasts_history_debug.html for inspection")

            self.logger.info(f"Retrieved {len(episodes)} episodes from history")

            return episodes

        except Exception as e:
            self.logger.error(f"Error parsing history page: {e}")
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
            # Handle published_date - convert empty string to None
            published_date = episode_details.get('published_date')
            if published_date == '' or not published_date:
                published_date = None

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
                'published_date': published_date,
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
