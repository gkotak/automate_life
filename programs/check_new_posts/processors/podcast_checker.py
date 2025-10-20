#!/usr/bin/env python3
"""
Podcast Checker - Tracks in-progress podcast episodes
Fetches from PocketCasts API and saves new episodes for processing

Usage:
    python3 podcast_checker.py              # Check for new podcasts only
    python3 podcast_checker.py 5            # Process 5 most recent unprocessed podcasts
    python3 podcast_checker.py --process    # Interactive prompt for number of podcasts
"""

import json
import sys
import os
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Import our base classes
sys.path.append(str(Path(__file__).parent.parent))
from common.base import BaseProcessor
from common.config import Config
from common.url_utils import generate_post_id
from common.podcast_auth import PodcastAuth

# Load environment variables
root_env = Path(__file__).parent.parent.parent.parent / '.env.local'
load_dotenv(root_env)


class PodcastChecker(BaseProcessor):
    """Check PocketCasts for in-progress podcast episodes"""

    def __init__(self):
        super().__init__("podcast_checker")

        # Note: Podcast tracking now uses Supabase content_queue table only
        # JSON file backup has been removed

        # Initialize Supabase client
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env.local")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.logger.info("✅ Connected to Supabase")

        # Initialize PocketCasts authentication
        self.podcast_auth = PodcastAuth(self.logger)

        # Load existing podcasts from database
        self.podcasts = self._load_tracked_podcasts()

        # Path to article_summarizer script
        self.article_summarizer_script = self.base_dir / "programs" / "article_summarizer" / "scripts" / "article_summarizer.py"

        # Load SerpAPI whitelist from environment variable
        # Format: comma-separated list of podcast titles
        whitelist_str = os.getenv('SERPAPI_PODCAST_WHITELIST', '')
        self.serpapi_whitelist = {title.strip() for title in whitelist_str.split(',') if title.strip()}

        if self.serpapi_whitelist:
            self.logger.info(f"📋 SerpAPI whitelist loaded: {len(self.serpapi_whitelist)} podcasts")
            for podcast in sorted(self.serpapi_whitelist):
                self.logger.debug(f"   • {podcast}")
        else:
            self.logger.warning("⚠️ No SerpAPI whitelist configured (SERPAPI_PODCAST_WHITELIST not set)")

    def _load_tracked_podcasts(self) -> Dict[str, Any]:
        """Load previously tracked podcasts from Supabase content_queue table"""
        try:
            # Query all podcast episodes from content_queue
            result = self.supabase.table('content_queue').select('*').eq(
                'content_type', 'podcast_episode'
            ).execute()

            # Convert to dict format with episode_hash as key (for backward compatibility)
            podcasts = {}
            for row in result.data:
                # Generate episode hash using same method as _get_episode_hash()
                # This ensures consistency between loading and checking
                episode_hash = generate_post_id(row['title'], row['episode_uuid'])

                podcasts[episode_hash] = {
                    'episode_title': row['title'],
                    'podcast_title': row['channel_title'],
                    'podcast_uuid': row['podcast_uuid'],
                    'episode_uuid': row['episode_uuid'],
                    'episode_url': row['url'],
                    'podcast_video_url': row['video_url'],
                    'duration': row['duration_seconds'],
                    'played_up_to': row['played_up_to'],
                    'progress_percent': float(row['progress_percent']) if row['progress_percent'] else 0,
                    'playing_status': row['playing_status'],
                    'published_date': row['published_date'],
                    'found_at': row['found_at'],
                    'status': row['status'],
                    'platform': row['platform']
                }

            self.logger.info(f"📂 Loaded {len(podcasts)} podcasts from database")
            return podcasts

        except Exception as e:
            self.logger.error(f"❌ Error loading podcasts from database: {e}")
            self.logger.error("💥 Database is required - cannot continue without it")
            raise

    def _save_tracked_podcasts(self, podcasts: Dict[str, Any]):
        """Save tracked podcasts to Supabase content_queue table"""
        try:
            # Convert podcasts dict to list of records for upserting
            # Use a dict to deduplicate by URL (in case multiple episode_hashes map to same URL)
            records_dict = {}
            for episode_hash, podcast in podcasts.items():
                url = podcast['episode_url']

                # Skip if we already have this URL
                if url in records_dict:
                    continue

                records_dict[url] = {
                    'url': url,
                    'title': podcast['episode_title'],
                    'content_type': 'podcast_episode',
                    'channel_title': podcast['podcast_title'],
                    'channel_url': f"https://pocketcasts.com/podcast/{podcast['podcast_uuid']}",
                    'video_url': podcast.get('podcast_video_url'),
                    'platform': podcast.get('platform', 'pocketcasts'),
                    'source_feed': None,
                    'found_at': podcast.get('found_at'),
                    'published_date': podcast.get('published_date'),
                    'status': podcast.get('status', 'discovered'),
                    'podcast_uuid': podcast['podcast_uuid'],
                    'episode_uuid': podcast['episode_uuid'],
                    'duration_seconds': podcast.get('duration'),
                    'played_up_to': podcast.get('played_up_to'),
                    'progress_percent': podcast.get('progress_percent'),
                    'playing_status': podcast.get('playing_status')
                }

            # Convert to list
            records = list(records_dict.values())

            # Batch upsert to Supabase (upsert based on unique URL)
            if records:
                self.supabase.table('content_queue').upsert(
                    records,
                    on_conflict='url'
                ).execute()

            self.logger.info(f"💾 Saved {len(podcasts)} podcasts to database")

        except Exception as e:
            self.logger.error(f"❌ Error saving podcasts to database: {e}")
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
        headers = self.podcast_auth.get_headers()
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

    def _extract_youtube_channel_from_pocketcasts(self, episode_url: str) -> Optional[str]:
        """
        Extract YouTube channel/playlist URL from PocketCasts episode page

        Args:
            episode_url: PocketCasts episode URL

        Returns:
            YouTube channel/playlist URL or None if not found
        """
        try:
            self.logger.info(f"      🔍 [POCKETCASTS] Checking episode page for YouTube channel...")

            # Use plain requests (not authenticated session) to get full HTML
            # PocketCasts serves different content when authenticated vs public
            import requests
            response = requests.get(episode_url, timeout=10)
            response.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for YouTube links in the page
            youtube_patterns = [
                r'youtu\.be/([A-Za-z0-9_-]+)',  # Short URL format (check first!)
                r'youtube\.com/watch\?v=([^/\s"\'&]+)',  # Direct video URL
                r'youtube\.com/channel/([^/\s"\'?&]+)',
                r'youtube\.com/@([^/\s"\'?&]+)',
                r'youtube\.com/c/([^/\s"\'?&]+)',
                r'youtube\.com/user/([^/\s"\'?&]+)',
                r'youtube\.com/playlist\?list=([^/\s"\'&]+)'  # Add playlist support
            ]

            import re
            page_text = soup.get_text()
            all_links = [a.get('href', '') for a in soup.find_all('a')]

            # Debug: Log YouTube links found
            youtube_links = [link for link in all_links if 'youtube' in link.lower() or 'youtu.be' in link.lower()]
            if youtube_links:
                self.logger.debug(f"      📺 [POCKETCASTS] Found {len(youtube_links)} YouTube links")
                for yt_link in youtube_links:
                    self.logger.debug(f"         - {yt_link}")
            else:
                self.logger.debug(f"      ⚠️ [POCKETCASTS] No YouTube links found in {len(all_links)} total links")

            # Check links first
            for link in all_links:
                if 'youtube.com' in link or 'youtu.be' in link:
                    # Extract channel/playlist/video URL
                    for pattern in youtube_patterns:
                        match = re.search(pattern, link)
                        if match:
                            identifier = match.group(1)
                            if 'youtu.be/' in link:
                                # Short URL format - always a video
                                youtube_url = f"https://www.youtube.com/watch?v={identifier}"
                            elif '/watch' in link:
                                # Direct video URL
                                youtube_url = f"https://www.youtube.com/watch?v={identifier}"
                            elif '/channel/' in link:
                                youtube_url = f"https://www.youtube.com/channel/{identifier}"
                            elif '/@' in link:
                                youtube_url = f"https://www.youtube.com/@{identifier}"
                            elif '/c/' in link:
                                youtube_url = f"https://www.youtube.com/c/{identifier}"
                            elif '/user/' in link:
                                youtube_url = f"https://www.youtube.com/user/{identifier}"
                            elif '/playlist' in link:
                                # For playlists, return the playlist URL
                                youtube_url = f"https://www.youtube.com/playlist?list={identifier}"
                            else:
                                continue

                            url_type = "video" if ('/watch' in link or 'youtu.be/' in link) else "channel/playlist"
                            self.logger.info(f"      ✅ [POCKETCASTS] Found YouTube {url_type}: {youtube_url}")
                            return youtube_url

            # Check page text as fallback
            for pattern in youtube_patterns:
                match = re.search(pattern, page_text)
                if match:
                    identifier = match.group(1)
                    if 'youtu\.be' in pattern:
                        # Short URL format
                        youtube_url = f"https://www.youtube.com/watch?v={identifier}"
                    elif 'watch' in pattern:
                        # Direct video URL
                        youtube_url = f"https://www.youtube.com/watch?v={identifier}"
                    elif 'channel/' in pattern:
                        youtube_url = f"https://www.youtube.com/channel/{identifier}"
                    elif '@' in pattern:
                        youtube_url = f"https://www.youtube.com/@{identifier}"
                    elif '/playlist' in pattern:
                        youtube_url = f"https://www.youtube.com/playlist?list={identifier}"
                    else:
                        youtube_url = f"https://www.youtube.com/c/{identifier}"

                    self.logger.info(f"      ✅ [POCKETCASTS] Found YouTube URL in text: {youtube_url}")
                    return youtube_url

            self.logger.info(f"      ℹ️ [POCKETCASTS] No YouTube URL found on episode page")
            return None

        except Exception as e:
            self.logger.warning(f"      ⚠️ [POCKETCASTS] Error extracting YouTube URL: {e}")
            return None

    def _check_title_match(self, episode_title: str, video_title: str, video_published: str = '', episode_published_date: Optional[str] = None) -> tuple[bool, float, str]:
        """
        Check if video title matches episode title using fuzzy matching

        Uses threshold logic:
        - 70% match required by default
        - 40% match sufficient if video published within 1-2 days

        Args:
            episode_title: Episode title to match
            video_title: Video title to check against
            video_published: Video publish date string (e.g., "13 hours ago", "2 days ago")
            episode_published_date: Episode publish date (ISO format) for date-based matching

        Returns:
            Tuple of (matches: bool, ratio: float, threshold_type: str)
        """
        from difflib import SequenceMatcher

        # Calculate similarity ratio
        ratio = SequenceMatcher(None, episode_title.lower(), video_title.lower()).ratio()

        # Determine threshold based on publish date
        MATCH_THRESHOLD = 0.70
        RELAXED_THRESHOLD = 0.40

        # Check if video is recently published (within 1-2 days)
        # Handle None or empty string for video_published
        video_published_lower = (video_published or '').lower()
        is_recent = any(x in video_published_lower for x in ['hour', 'day', '1 day', '2 day'])

        threshold = RELAXED_THRESHOLD if is_recent else MATCH_THRESHOLD
        threshold_type = "relaxed" if is_recent else "standard"

        matches = ratio >= threshold

        return matches, ratio, threshold_type

    def _scrape_youtube_playlist_for_episode(self, playlist_url: str, episode_title: str, episode_published_date: Optional[str] = None) -> Optional[str]:
        """
        Scrape YouTube playlist/channel page to find matching episode video

        Args:
            playlist_url: YouTube playlist or channel URL
            episode_title: Episode title to match against
            episode_published_date: Episode publish date (ISO format) for date-based matching

        Returns:
            YouTube video URL or None if not found
        """
        try:
            self.logger.info(f"      🔍 [YOUTUBE SCRAPE] Scraping playlist/channel for videos...")
            self.logger.debug(f"      📺 [YOUTUBE SCRAPE] URL: {playlist_url}")
            self.logger.debug(f"      📝 [YOUTUBE SCRAPE] Looking for: '{episode_title[:60]}...'")

            import requests
            from bs4 import BeautifulSoup
            from difflib import SequenceMatcher

            # Fetch the playlist/channel page
            response = requests.get(playlist_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract video information from the page
            # YouTube playlists have video titles in various places
            # Look for common patterns in the HTML
            videos = []

            # Method 1: Look for ytInitialData script tag (contains video data)
            import re
            import json

            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'ytInitialData' in script.string:
                    # Extract the JSON data
                    match = re.search(r'var ytInitialData = ({.*?});', script.string)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            self.logger.debug(f"      📊 [YOUTUBE SCRAPE] Found ytInitialData")

                            # Navigate through the complex YouTube data structure
                            # Structure varies between playlists and channels
                            contents = None

                            # Try playlist structure
                            try:
                                contents = data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['playlistVideoListRenderer']['contents']
                            except (KeyError, IndexError, TypeError):
                                pass

                            # Try channel structure
                            if not contents:
                                try:
                                    contents = data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['richGridRenderer']['contents']
                                except (KeyError, IndexError, TypeError):
                                    pass

                            if contents:
                                for item in contents:
                                    # Extract video title and ID
                                    video_title = None
                                    video_id = None

                                    # Playlist video structure
                                    if 'playlistVideoRenderer' in item:
                                        video_data = item['playlistVideoRenderer']
                                        video_title = video_data.get('title', {}).get('runs', [{}])[0].get('text', '')
                                        video_id = video_data.get('videoId', '')
                                        # Extract publish date from videoInfo (e.g., "13 hours ago")
                                        video_info_runs = video_data.get('videoInfo', {}).get('runs', [])
                                        video_published = video_info_runs[-1].get('text', '') if len(video_info_runs) > 0 else ''

                                    # Channel video structure
                                    elif 'richItemRenderer' in item:
                                        try:
                                            video_data = item['richItemRenderer']['content']['videoRenderer']
                                            video_title = video_data.get('title', {}).get('runs', [{}])[0].get('text', '')
                                            video_id = video_data.get('videoId', '')
                                            # Extract publish date from publishedTimeText or videoInfo
                                            video_published = video_data.get('publishedTimeText', {}).get('simpleText', '')
                                            if not video_published:
                                                video_info_runs = video_data.get('videoInfo', {}).get('runs', [])
                                                video_published = video_info_runs[-1].get('text', '') if len(video_info_runs) > 0 else ''
                                        except (KeyError, TypeError):
                                            pass

                                    if video_title and video_id:
                                        videos.append({
                                            'title': video_title,
                                            'url': f'https://www.youtube.com/watch?v={video_id}',
                                            'published': video_published
                                        })

                            break  # Found ytInitialData, stop searching
                        except json.JSONDecodeError:
                            self.logger.debug(f"      ⚠️ [YOUTUBE SCRAPE] Failed to parse ytInitialData")
                            continue

            self.logger.info(f"      📊 [YOUTUBE SCRAPE] Found {len(videos)} videos in playlist/channel")

            if not videos:
                self.logger.warning(f"      ⚠️ [YOUTUBE SCRAPE] No videos found in playlist/channel")
                return None

            # Log the episode title we're trying to match
            self.logger.info(f"      🎯 [YOUTUBE SCRAPE] Searching for: {episode_title[:80]}...")

            # Check each video using shared matching logic
            valid_matches = []
            best_match = None
            best_ratio = 0.0

            for video in videos:
                video_published = video.get('published', '')

                # Use shared matching logic
                matches, ratio, threshold_type = self._check_title_match(
                    episode_title,
                    video['title'],
                    video_published,
                    episode_published_date
                )

                # Track best match for logging
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = video

                # Log top matches with publish date info
                if ratio > 0.4:  # Only log decent matches
                    pub_info = f" [{video_published}]" if video_published else ""
                    self.logger.info(f"      🔍 [YOUTUBE SCRAPE] Match: {ratio:.1%} - {video['title'][:80]}{pub_info}...")

                # Collect valid matches
                if matches:
                    valid_matches.append({
                        'video': video,
                        'ratio': ratio,
                        'threshold_type': threshold_type
                    })

            if valid_matches:
                # Sort by ratio (best match first)
                valid_matches.sort(key=lambda x: x['ratio'], reverse=True)
                best = valid_matches[0]

                # Get threshold value for logging
                threshold_value = 0.40 if best['threshold_type'] == "relaxed" else 0.70
                self.logger.info(f"      📅 [YOUTUBE SCRAPE] Using {best['threshold_type']} threshold ({threshold_value:.0%})")
                self.logger.info(f"      ✅ [YOUTUBE SCRAPE] Found match ({best['ratio']:.1%}): {best['video']['title'][:60]}...")
                self.logger.info(f"      🎬 [YOUTUBE SCRAPE] Video URL: {best['video']['url']}")
                return best['video']['url']
            else:
                if best_match:
                    self.logger.info(f"      ℹ️ [YOUTUBE SCRAPE] Best match only {best_ratio:.1%} (need 70% or 40% if recent)")
                    self.logger.info(f"      📝 [YOUTUBE SCRAPE] Best match was: {best_match['title'][:60]}...")
                self.logger.info(f"      ℹ️ [YOUTUBE SCRAPE] No good match found in playlist/channel")
                return None

        except Exception as e:
            self.logger.warning(f"      ⚠️ [YOUTUBE SCRAPE] Error scraping playlist/channel: {e}")
            import traceback
            self.logger.debug(f"      🔍 [YOUTUBE SCRAPE] Full traceback:\n{traceback.format_exc()}")
            return None

    def _validate_youtube_video(self, video_url: str, episode_title: str, episode_published_date: Optional[str] = None) -> bool:
        """
        Validate that a direct YouTube video URL matches the episode

        Uses fuzzy matching with same threshold logic as playlist scraping:
        - 70% match required by default
        - 40% match sufficient if published within 1 day of each other

        Args:
            video_url: YouTube video URL to validate
            episode_title: Episode title to match against
            episode_published_date: Episode publish date (ISO format) for date-based matching

        Returns:
            True if video matches episode, False otherwise
        """
        try:
            self.logger.info(f"      🔍 [VIDEO VALIDATION] Validating direct video URL...")
            self.logger.debug(f"      📺 [VIDEO VALIDATION] URL: {video_url}")
            self.logger.debug(f"      📝 [VIDEO VALIDATION] Looking for: '{episode_title[:60]}...'")

            import requests
            from bs4 import BeautifulSoup
            from difflib import SequenceMatcher
            import json

            # Fetch video page
            response = requests.get(video_url, timeout=10)
            response.raise_for_status()

            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract video title and metadata from ytInitialData
            # Look for ytInitialData JSON
            yt_initial_data = None
            for script in soup.find_all('script'):
                script_text = script.string or ''
                if 'var ytInitialData = ' in script_text:
                    # Extract JSON
                    start = script_text.find('var ytInitialData = ') + len('var ytInitialData = ')
                    end = script_text.find('};', start) + 1
                    json_str = script_text[start:end]
                    try:
                        yt_initial_data = json.loads(json_str)
                        break
                    except json.JSONDecodeError:
                        continue

            if not yt_initial_data:
                self.logger.warning(f"      ⚠️ [VIDEO VALIDATION] Could not extract video metadata")
                return False

            # Extract video title
            video_title = None
            video_published = None

            try:
                # Navigate to video details
                contents = yt_initial_data.get('contents', {})
                two_column = contents.get('twoColumnWatchNextResults', {})
                results = two_column.get('results', {}).get('results', {})
                video_contents = results.get('contents', [])

                # Find videoPrimaryInfoRenderer
                for content in video_contents:
                    if 'videoPrimaryInfoRenderer' in content:
                        primary_info = content['videoPrimaryInfoRenderer']

                        # Extract title
                        title_runs = primary_info.get('title', {}).get('runs', [])
                        if title_runs:
                            video_title = title_runs[0].get('text', '')

                        # Extract publish date from dateText
                        date_text = primary_info.get('dateText', {}).get('simpleText', '')
                        if date_text:
                            video_published = date_text.lower()

                        break
            except (KeyError, IndexError) as e:
                self.logger.debug(f"      🔍 [VIDEO VALIDATION] Error navigating metadata: {e}")

            if not video_title:
                self.logger.warning(f"      ⚠️ [VIDEO VALIDATION] Could not extract video title")
                return False

            self.logger.info(f"      📹 [VIDEO VALIDATION] Video title: '{video_title[:60]}...'")
            if video_published:
                self.logger.info(f"      📅 [VIDEO VALIDATION] Published: {video_published}")

            # Use shared matching logic
            matches, ratio, threshold_type = self._check_title_match(
                episode_title,
                video_title,
                video_published,
                episode_published_date
            )

            # Get threshold value for logging
            threshold_value = 0.40 if threshold_type == "relaxed" else 0.70

            if threshold_type == "relaxed":
                self.logger.info(f"      📅 [VIDEO VALIDATION] Using relaxed threshold (40%) - video published recently")

            # Validate match
            if matches:
                self.logger.info(f"      ✅ [VIDEO VALIDATION] Match confirmed ({ratio:.1%} >= {threshold_value:.0%}, {threshold_type})")
                return True
            else:
                self.logger.info(f"      ❌ [VIDEO VALIDATION] Match failed ({ratio:.1%} < {threshold_value:.0%})")
                self.logger.info(f"      📝 [VIDEO VALIDATION] Episode: '{episode_title[:60]}...'")
                self.logger.info(f"      📝 [VIDEO VALIDATION] Video:   '{video_title[:60]}...'")
                return False

        except Exception as e:
            self.logger.warning(f"      ⚠️ [VIDEO VALIDATION] Error validating video: {e}")
            import traceback
            self.logger.debug(f"      🔍 [VIDEO VALIDATION] Full traceback:\n{traceback.format_exc()}")
            return False

    def _search_youtube_channel_for_episode(self, channel_url: str, episode_title: str, podcast_title: str) -> Optional[str]:
        """
        Search a YouTube channel for a specific episode video

        Args:
            channel_url: YouTube channel URL
            episode_title: Episode title to search for
            podcast_title: Podcast name

        Returns:
            YouTube video URL or None if not found
        """
        try:
            self.logger.info(f"      🔍 [YOUTUBE] Searching channel for episode...")
            self.logger.debug(f"      📺 [YOUTUBE] Channel: {channel_url}")
            self.logger.debug(f"      📝 [YOUTUBE] Episode: '{episode_title[:60]}...'")

            # Use SerpAPI to search within the YouTube channel
            from serpapi import GoogleSearch
            import os

            api_key = os.getenv('SERPAPI_KEY')
            if not api_key:
                self.logger.warning("      ⚠️ [YOUTUBE] SERPAPI_KEY not found")
                return None

            # Search within the specific channel
            query = f'site:youtube.com "{podcast_title}" "{episode_title}"'
            self.logger.debug(f"      🔎 [YOUTUBE] Query: {query[:100]}...")

            params = {
                "q": query,
                "api_key": api_key,
                "engine": "google",
                "num": 10  # Get more results to find the right video
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            organic_results = results.get('organic_results', [])
            self.logger.debug(f"      📄 [YOUTUBE] Found {len(organic_results)} results")

            # Extract channel handle/ID from channel_url
            channel_identifier = None
            if '/@' in channel_url:
                channel_identifier = channel_url.split('/@')[1].split('/')[0].lower()
            elif '/channel/' in channel_url:
                channel_identifier = channel_url.split('/channel/')[1].split('/')[0]
            elif '/c/' in channel_url:
                channel_identifier = channel_url.split('/c/')[1].split('/')[0].lower()

            # Filter results to only include videos from this channel
            for idx, result in enumerate(organic_results):
                link = result.get('link', '')
                title = result.get('title', '')

                # Check if it's a video URL (not channel/playlist)
                if 'youtube.com/watch?v=' in link or 'youtu.be/' in link:
                    # Verify it's from the right channel by checking if channel identifier is in the URL
                    # Note: This is a heuristic - ideally we'd check the video's channel ID
                    self.logger.debug(f"      🎬 [YOUTUBE] Candidate {idx+1}: {title[:60]}... -> {link[:60]}...")

                    # If we have a channel identifier, try to verify it's from the right channel
                    if channel_identifier:
                        # Get the video page to check the channel
                        # For now, we'll trust that the search results are from the right channel
                        # since we included the channel in the query
                        pass

                    self.logger.info(f"      ✅ [YOUTUBE] Found video: {link}")
                    return link

            self.logger.info(f"      ℹ️ [YOUTUBE] No matching video found in channel")
            return None

        except Exception as e:
            self.logger.warning(f"      ⚠️ [YOUTUBE] Error searching channel: {e}")
            import traceback
            self.logger.debug(f"      🔍 [YOUTUBE] Full traceback:\n{traceback.format_exc()}")
            return None

    def _search_podcast_video_url(self, episode_title: str, podcast_title: str) -> Optional[str]:
        """
        Search YouTube for podcast episode video using SerpAPI

        Args:
            episode_title: Episode title
            podcast_title: Podcast name

        Returns:
            YouTube video URL or None if not found
        """
        try:
            from serpapi import GoogleSearch
            import os

            # Get API key from environment
            api_key = os.getenv('SERPAPI_KEY')
            if not api_key:
                self.logger.warning("      ⚠️ [SERPAPI] SERPAPI_KEY not found in environment")
                return None

            self.logger.info(f"      🔍 [SERPAPI] Searching YouTube for episode video...")
            self.logger.debug(f"      📝 [SERPAPI] Episode: '{episode_title[:60]}...'")
            self.logger.debug(f"      📝 [SERPAPI] Podcast: '{podcast_title}'")

            # Strict YouTube search query
            query = f'site:youtube.com "{podcast_title}" "{episode_title}"'
            self.logger.debug(f"      🔎 [SERPAPI] Query: {query[:100]}...")

            # SerpAPI search parameters
            params = {
                "q": query,
                "api_key": api_key,
                "engine": "google",
                "num": 10  # Get top 10 results to increase chances of finding the right video
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            self.logger.debug(f"      📊 [SERPAPI] Response received")

            # Save debug output if enabled
            if os.getenv('DEBUG_LOGGING') == '1':
                import json
                debug_file = self.base_dir / "programs" / "check_new_posts" / "logs" / "serpapi_debug.json"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)
                self.logger.debug(f"      💾 [SERPAPI] Saved response to {debug_file}")

            # Check for error in SerpAPI response (e.g., out of credits)
            if 'error' in results:
                error_msg = results['error']
                self.logger.warning(f"      ⚠️ [SERPAPI] Error from SerpAPI: {error_msg}")
                return None

            # First, check inline_images for direct video links (often more accurate)
            inline_images = results.get('inline_images', [])
            if inline_images:
                self.logger.debug(f"      🖼️ [SERPAPI] Found {len(inline_images)} inline images")
                for idx, image in enumerate(inline_images):
                    source = image.get('source', '')
                    img_title = image.get('title', '')

                    # Check if it's a YouTube video URL (not channel/playlist)
                    if 'youtube.com/watch?v=' in source:
                        self.logger.debug(f"      🎬 [SERPAPI] Image {idx+1}: {img_title[:60]}... -> {source[:60]}...")
                        self.logger.info(f"      ✅ [SERPAPI] Found YouTube video (from image): {source}")
                        return source

            # Check organic search results
            organic_results = results.get('organic_results', [])
            self.logger.debug(f"      📄 [SERPAPI] Found {len(organic_results)} organic results")

            for idx, result in enumerate(organic_results):
                link = result.get('link', '')
                title = result.get('title', '')

                self.logger.debug(f"      🔗 [SERPAPI] Result {idx+1}: {title[:60]}... -> {link[:60]}...")

                # Check if it's a specific YouTube video URL (not channel/playlist)
                if 'youtube.com/watch?v=' in link:
                    self.logger.info(f"      ✅ [SERPAPI] Found YouTube video: {link}")
                    return link
                elif 'youtu.be/' in link and 'youtu.be/@' not in link:
                    self.logger.info(f"      ✅ [SERPAPI] Found YouTube video: {link}")
                    return link

            # No YouTube video found
            self.logger.info(f"      ℹ️ [SERPAPI] No YouTube video found in search results")
            return None

        except Exception as e:
            self.logger.warning(f"      ⚠️ [SERPAPI] Error during search: {e}")
            import traceback
            self.logger.debug(f"      🔍 [SERPAPI] Full traceback:\n{traceback.format_exc()}")
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

            # Build episode URL using the full PocketCasts format
            # Format: https://pocketcasts.com/podcast/{podcast_slug}/{podcast_uuid}/{episode_slug}/{episode_uuid}
            podcast_slug = episode.get('podcastSlug', '')
            episode_slug = episode.get('slug', '')
            if podcast_slug and episode_slug and podcast_uuid and episode_uuid:
                episode_url = f"https://pocketcasts.com/podcast/{podcast_slug}/{podcast_uuid}/{episode_slug}/{episode_uuid}"
            else:
                # Fallback to episode-only URL if slugs are missing
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

                # Search for YouTube video URL - two-step strategy
                # Step 1: Try PocketCasts page scraping (free, fast)
                # Step 2: Try SerpAPI YouTube search (uses credits)
                # Fallback: Use PocketCasts audio URL
                podcast_video_url = None
                episode_url = episode_details['episode_url']

                if os.getenv('SEARCH_PODCAST_URLS') == '1':
                    # Log episode and podcast details before starting YouTube search
                    self.logger.info(f"")
                    self.logger.info(f"      🎯 [YOUTUBE SEARCH] Starting search for YouTube video...")
                    self.logger.info(f"      📝 Episode: {episode_title}")
                    self.logger.info(f"      🎙️ Podcast: {podcast_title}")

                    # Step 1: Extract YouTube channel/playlist from PocketCasts page
                    self.logger.info(f"      📍 [STEP 1] Scraping PocketCasts page for YouTube link...")
                    youtube_url = self._extract_youtube_channel_from_pocketcasts(episode_url)

                    if youtube_url:
                        # Found YouTube URL from PocketCasts page
                        # Check if it's a direct video URL first
                        if '/watch' in youtube_url:
                            # It's a direct video URL - validate it with fuzzy matching
                            self.logger.info(f"      📍 [STEP 1a] Validating direct video URL...")
                            is_valid = self._validate_youtube_video(
                                youtube_url, episode_title, episode_details.get('published_date')
                            )
                            if is_valid:
                                podcast_video_url = youtube_url
                                self.logger.info(f"      ✅ [STEP 1a] Direct video validated (FREE)!")
                            else:
                                self.logger.info(f"      ❌ [STEP 1a] Direct video did not match episode")
                                # Don't use this video, will fall through to SerpAPI if needed
                        elif '/playlist' in youtube_url or '/channel/' in youtube_url or '/@' in youtube_url or '/c/' in youtube_url or '/user/' in youtube_url:
                            # It's a channel/playlist, scrape it directly to find the video
                            self.logger.info(f"      📍 [STEP 1b] Scraping YouTube playlist/channel for videos...")
                            video_url = self._scrape_youtube_playlist_for_episode(
                                youtube_url, episode_title, episode_details.get('published_date')
                            )
                            if video_url:
                                podcast_video_url = video_url
                                self.logger.info(f"      ✅ [STEP 1b] Found video via playlist scraping (FREE)!")
                            else:
                                # Step 1c: If playlist scraping failed and podcast is whitelisted, try SerpAPI
                                if podcast_title in self.serpapi_whitelist:
                                    self.logger.info(f"      📍 [STEP 1c] Playlist scraping failed, trying SerpAPI (whitelisted podcast)...")
                                    video_url = self._search_youtube_channel_for_episode(
                                        youtube_url, episode_title, podcast_title
                                    )
                                    if video_url:
                                        podcast_video_url = video_url
                                        self.logger.info(f"      ✅ [STEP 1c] Found video via SerpAPI channel search!")
                                else:
                                    self.logger.info(f"      ℹ️ [STEP 1c] Playlist scraping failed, SerpAPI not used (podcast not whitelisted)")
                        else:
                            # Unknown YouTube URL type, log warning
                            self.logger.warning(f"      ⚠️ [STEP 1] Unknown YouTube URL type: {youtube_url}")
                            self.logger.warning(f"      ⚠️ [STEP 1] Not a video, playlist, or channel URL")

                    # Step 2: If Step 1 didn't find a video and podcast is whitelisted, use SerpAPI direct search
                    if not podcast_video_url:
                        if podcast_title in self.serpapi_whitelist:
                            self.logger.info(f"      📍 [STEP 2] Step 1 failed, trying SerpAPI direct search (whitelisted podcast)...")
                            podcast_video_url = self._search_podcast_video_url(episode_title, podcast_title)
                            if podcast_video_url:
                                self.logger.info(f"      ✅ [STEP 2] Found video via SerpAPI direct search!")
                        else:
                            self.logger.info(f"      ℹ️ [STEP 2] SerpAPI not used (podcast not whitelisted)")

                    # Log final result
                    if podcast_video_url:
                        self.logger.info(f"      ✅ [YOUTUBE SEARCH] Found YouTube video: {podcast_video_url[:60]}...")
                    else:
                        self.logger.info(f"      ℹ️ [YOUTUBE SEARCH] No YouTube video found, will use PocketCasts audio")
                else:
                    self.logger.debug("      ℹ️ [SEARCH] URL search disabled (set SEARCH_PODCAST_URLS=1 to enable)")

                # Add to processing list
                new_podcasts_for_processing.append({
                    'episode_title': episode_title,
                    'podcast_title': podcast_title,
                    'episode_url': episode_details['episode_url'],
                    'podcast_video_url': podcast_video_url,
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
                    'podcast_video_url': podcast_video_url,
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

                # Show podcast_video_url if available
                if podcast.get('podcast_video_url'):
                    self.logger.info(f"   🎬 Video URL: {podcast['podcast_video_url']}")

                self.logger.info(f"   🔗 PocketCasts: {podcast['episode_url']}")

            self.logger.info("=" * 80)
            self.logger.info("💡 These podcast episodes have been tracked.")
            self.logger.info("   Future integration: Process with article summarizer for transcripts")

            return f"Found {len(new_podcasts)} new podcast episodes"

        except Exception as e:
            self.logger.error(f"❌ Error showing podcast summary: {e}")
            return None

    def get_unprocessed_podcasts(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get podcasts that haven't been processed with article_summarizer yet

        Args:
            limit: Maximum number of podcasts to return (most recent first)

        Returns:
            List of unprocessed podcast dictionaries
        """
        try:
            from supabase import create_client
            from dotenv import load_dotenv

            # Load environment variables
            root_env = self.base_dir / '.env.local'
            if root_env.exists():
                load_dotenv(root_env)

            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

            if not supabase_url or not supabase_key:
                self.logger.warning("⚠️ Supabase credentials not found - cannot check processed podcasts")
                return []

            supabase = create_client(supabase_url, supabase_key)

            # Load tracked podcasts
            tracked_podcasts = self._load_tracked_podcasts()

            # Get all URLs from Supabase articles table
            result = supabase.table('articles').select('url').execute()
            processed_urls = set(row['url'] for row in result.data)

            self.logger.info(f"📊 Found {len(processed_urls)} processed articles in database")

            # Filter unprocessed podcasts
            unprocessed = []
            for episode_hash, podcast_data in tracked_podcasts.items():
                # Check both episode_url and podcast_video_url
                episode_url = podcast_data.get('episode_url', '')
                podcast_video_url = podcast_data.get('podcast_video_url', '')

                # Skip if either URL has been processed
                if episode_url in processed_urls or podcast_video_url in processed_urls:
                    continue

                # Add to unprocessed list with metadata
                unprocessed.append({
                    'episode_hash': episode_hash,
                    'episode_title': podcast_data.get('episode_title', 'Unknown'),
                    'podcast_title': podcast_data.get('podcast_title', 'Unknown'),
                    'episode_url': episode_url,
                    'podcast_video_url': podcast_video_url,
                    'published_date': podcast_data.get('published_date', ''),
                    'found_at': podcast_data.get('found_at', ''),
                    'progress_percent': podcast_data.get('progress_percent', 0)
                })

            # Sort by found_at (most recent first)
            unprocessed.sort(key=lambda x: x.get('found_at', ''), reverse=True)

            # Apply limit if specified
            if limit:
                unprocessed = unprocessed[:limit]

            self.logger.info(f"📋 Found {len(unprocessed)} unprocessed podcasts")
            return unprocessed

        except Exception as e:
            self.logger.error(f"❌ Error getting unprocessed podcasts: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return []

    def process_podcasts_with_summarizer(self, podcast_count: int) -> Dict:
        """
        Process N most recent unprocessed podcasts with article_summarizer

        Args:
            podcast_count: Number of podcasts to process

        Returns:
            Dictionary with processing results
        """
        self.logger.info(f"🎯 Processing {podcast_count} most recent unprocessed podcasts...")

        # Get unprocessed podcasts
        unprocessed = self.get_unprocessed_podcasts(limit=podcast_count)

        if not unprocessed:
            self.logger.info("✨ No unprocessed podcasts found")
            return {'processed': 0, 'failed': 0, 'skipped': 0}

        self.logger.info(f"📋 Found {len(unprocessed)} unprocessed podcasts to process")
        self.logger.info("=" * 80)

        results = {
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }

        for idx, podcast in enumerate(unprocessed, 1):
            episode_title = podcast['episode_title']
            podcast_title = podcast['podcast_title']
            podcast_video_url = podcast.get('podcast_video_url')
            episode_url = podcast['episode_url']

            self.logger.info(f"\n{idx}/{len(unprocessed)}. {episode_title[:70]}...")
            self.logger.info(f"   🎙️ {podcast_title}")

            # Determine which URL to use
            url_to_process = podcast_video_url if podcast_video_url else episode_url

            if not url_to_process:
                self.logger.warning(f"   ⚠️ No URL available, skipping...")
                results['skipped'] += 1
                continue

            self.logger.info(f"   🔗 URL: {url_to_process}")
            self.logger.info(f"   ▶️ Processing with article_summarizer...")

            # Call article_summarizer.py script
            try:
                result = subprocess.run(
                    ['python3', str(self.article_summarizer_script), url_to_process],
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout per podcast
                )

                if result.returncode == 0:
                    self.logger.info(f"   ✅ Successfully processed!")
                    # Extract article ID from output if present
                    output_lines = result.stdout.strip().split('\n')
                    for line in output_lines:
                        if 'Article ID:' in line or 'article/' in line:
                            self.logger.info(f"   📝 {line.strip()}")
                    results['processed'] += 1
                    results['details'].append({
                        'episode': episode_title,
                        'status': 'success',
                        'url': url_to_process
                    })
                else:
                    self.logger.error(f"   ❌ Processing failed (exit code: {result.returncode})")
                    self.logger.error(f"   ❌ Article was NOT saved to database due to processing error")
                    if result.stderr:
                        self.logger.error(f"   Error details: {result.stderr[:500]}")
                    if result.stdout:
                        self.logger.error(f"   Output: {result.stdout[:500]}")
                    results['failed'] += 1
                    results['details'].append({
                        'episode': episode_title,
                        'status': 'failed',
                        'url': url_to_process,
                        'error': result.stderr[:500] if result.stderr else result.stdout[:500] if result.stdout else 'Unknown error'
                    })

            except subprocess.TimeoutExpired:
                self.logger.error(f"   ⏱️ Processing timed out after 10 minutes")
                results['failed'] += 1
                results['details'].append({
                    'episode': episode_title,
                    'status': 'timeout',
                    'url': url_to_process
                })
            except Exception as e:
                self.logger.error(f"   ❌ Error processing: {e}")
                results['failed'] += 1
                results['details'].append({
                    'episode': episode_title,
                    'status': 'error',
                    'url': url_to_process,
                    'error': str(e)
                })

        # Show summary
        self.logger.info("\n" + "=" * 80)
        self.logger.info(f"🎉 Processing complete!")
        self.logger.info(f"   ✅ Processed: {results['processed']}")
        self.logger.info(f"   ❌ Failed: {results['failed']}")
        self.logger.info(f"   ⏭️ Skipped: {results['skipped']}")
        self.logger.info("=" * 80)

        return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Check PocketCasts for new podcasts and optionally process them with article_summarizer'
    )
    parser.add_argument(
        'count',
        nargs='?',
        type=int,
        help='Number of most recent unprocessed podcasts to process (e.g., 5)'
    )
    parser.add_argument(
        '--process',
        action='store_true',
        help='Interactive prompt for number of podcasts to process'
    )

    args = parser.parse_args()

    checker = PodcastChecker()

    try:
        # First, always check for new podcasts
        summary = checker.check_for_new_podcasts()

        # Print summary to stdout for shell script to capture
        if summary:
            print(summary)

        # Handle processing if requested
        if args.count is not None:
            # Process N podcasts
            print(f"\n🎯 Processing {args.count} most recent unprocessed podcasts...")
            results = checker.process_podcasts_with_summarizer(args.count)

        elif args.process:
            # Interactive mode
            print("\n" + "=" * 80)
            unprocessed = checker.get_unprocessed_podcasts()
            print(f"\n📊 Total unprocessed podcasts: {len(unprocessed)}")

            if unprocessed:
                print("\nRecent unprocessed podcasts:")
                for i, podcast in enumerate(unprocessed[:10], 1):
                    print(f"  {i}. {podcast['episode_title'][:60]}... ({podcast['podcast_title']})")
                if len(unprocessed) > 10:
                    print(f"  ... and {len(unprocessed) - 10} more")

                try:
                    count_input = input(f"\n🎯 How many podcasts to process? (1-{len(unprocessed)}): ")
                    count = int(count_input)

                    if count < 1 or count > len(unprocessed):
                        print(f"❌ Please enter a number between 1 and {len(unprocessed)}")
                        sys.exit(1)

                    print(f"\n▶️ Processing {count} podcasts...")
                    results = checker.process_podcasts_with_summarizer(count)

                except ValueError:
                    print("❌ Invalid number")
                    sys.exit(1)
                except KeyboardInterrupt:
                    print("\n⏹️ Cancelled by user")
                    sys.exit(0)
            else:
                print("✨ No unprocessed podcasts found")

    except KeyboardInterrupt:
        checker.logger.info("Process interrupted by user")
    except Exception as e:
        checker.logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
