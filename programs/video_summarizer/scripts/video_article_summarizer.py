#!/usr/bin/env python3
"""
Hybrid Video Article Summarizer
Combines deterministic Python operations with Claude Code AI capabilities
"""

import os
import sys
import json
import subprocess
import requests
import re
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

class VideoArticleSummarizer:
    def __init__(self, base_dir=None):
        if base_dir is None:
            # Find the project root by looking for characteristic files
            current_dir = Path(__file__).parent
            while current_dir != current_dir.parent:
                if (current_dir / '.git').exists() or (current_dir / 'CLAUDE.md').exists():
                    base_dir = current_dir
                    break
                current_dir = current_dir.parent
            else:
                # Fallback: assume script is in programs/video_summarizer/scripts/
                base_dir = Path(__file__).parent.parent.parent

        self.base_dir = Path(base_dir)
        self.html_dir = self.base_dir / "programs" / "video_summarizer" / "output" / "article_summaries"
        self.logs_dir = self.base_dir / "programs" / "video_summarizer" / "logs"
        self.claude_cmd = self._find_claude_cli()

        # Load environment variables for credentials (prioritize .env.local)
        env_local = self.base_dir / '.env.local'
        env_default = self.base_dir / '.env'

        if env_local.exists():
            load_dotenv(env_local)
        elif env_default.exists():
            load_dotenv(env_default)

        # Setup authenticated session
        self.session = self._setup_authenticated_session()

        # Ensure directories exist
        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging to both console and file"""
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = self.logs_dir / f"video_article_summarizer_{timestamp}.log"

        # Create logger
        self.logger = logging.getLogger('VideoArticleSummarizer')
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        simple_formatter = logging.Formatter('%(message)s')

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self.logger.addHandler(console_handler)

        # Log startup
        self.logger.info(f"VideoArticleSummarizer initialized. Log file: {log_file}")

    def _setup_authenticated_session(self):
        """Setup requests session with authentication credentials"""
        session = requests.Session()

        # Set default headers
        user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        # Add session cookies if provided
        session_cookies = os.getenv('NEWSLETTER_SESSION_COOKIES')
        if session_cookies:
            # Parse cookie string format: "name1=value1; name2=value2"
            for cookie in session_cookies.split(';'):
                if '=' in cookie:
                    name, value = cookie.strip().split('=', 1)
                    session.cookies.set(name, value)

        return session

    def _detect_platform(self, url):
        """Detect the platform/service from URL patterns"""
        domain = urlparse(url).netloc.lower()

        # Platform detection patterns
        platforms = {
            'substack': [
                lambda d: d.endswith('.substack.com'),
                lambda d: 'substack.com' in d,
                lambda d: any(pattern in d for pattern in ['newsletter', 'substack'])
            ],
            'medium': [
                lambda d: d.endswith('.medium.com'),
                lambda d: d == 'medium.com',
                lambda d: 'medium.com' in d
            ],
            'patreon': [
                lambda d: d == 'patreon.com',
                lambda d: d.endswith('.patreon.com')
            ],
            'youtube': [
                lambda d: d in ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']
            ],
            'ghost': [
                lambda d: 'ghost.io' in d,
                lambda d: any(ghost_indicator in url.lower() for ghost_indicator in ['/ghost/', 'ghost.org'])
            ],
            'convertkit': [
                lambda d: 'convertkit.com' in d,
                lambda d: 'ck.page' in d
            ],
            'beehiiv': [
                lambda d: 'beehiiv.com' in d
            ],
            'mailchimp': [
                lambda d: 'mailchimp.com' in d,
                lambda d: 'us' in d and 'campaign-archive.com' in d  # Mailchimp archives
            ],
            'linkedin': [
                lambda d: d in ['linkedin.com', 'www.linkedin.com']
            ],
            'twitter': [
                lambda d: d in ['twitter.com', 'www.twitter.com', 'x.com', 'www.x.com']
            ]
        }

        # Check each platform's patterns
        for platform, patterns in platforms.items():
            if any(pattern(domain) for pattern in patterns):
                return platform

        # Check for common newsletter/blog indicators in the URL
        url_lower = url.lower()
        if any(indicator in url_lower for indicator in ['/newsletter/', '/blog/', '/p/', '/post/']):
            return 'newsletter_generic'

        return 'generic'

    def _authenticate_for_platform(self, platform, url, session):
        """Perform platform-specific authentication based on detected platform"""
        try:
            self.logger.info(f"   Detected platform: {platform}")

            if platform == 'substack':
                return self._authenticate_substack(session)
            elif platform == 'medium':
                return self._authenticate_medium(session)
            elif platform == 'patreon':
                return self._authenticate_patreon(session)
            elif platform == 'youtube':
                return self._authenticate_youtube(session)
            elif platform == 'ghost':
                return self._authenticate_ghost(url, session)
            elif platform in ['convertkit', 'beehiiv', 'mailchimp', 'newsletter_generic']:
                return self._authenticate_newsletter_generic(platform, session)
            elif platform in ['linkedin', 'twitter']:
                return self._authenticate_social(platform, session)
            else:
                # Generic authentication using session cookies
                return self._authenticate_generic(platform, session)

        except Exception as e:
            self.logger.warning(f"   ⚠️ Authentication failed for {platform}: {str(e)}")
            return False

    def _authenticate_substack(self, session):
        """Authenticate with Substack"""
        email = os.getenv('SUBSTACK_EMAIL')
        password = os.getenv('SUBSTACK_PASSWORD')

        if email and password:
            self.logger.info("   Attempting Substack authentication...")
            login_url = "https://substack.com/api/v1/login"
            login_data = {
                'email': email,
                'password': password,
                'captcha_response': None
            }
            response = session.post(login_url, json=login_data)
            if response.status_code == 200:
                self.logger.info("   ✓ Substack authentication successful")
                return True
            else:
                self.logger.warning(f"   ⚠️ Substack authentication failed: {response.status_code}")
        else:
            self.logger.info("   No Substack credentials found, using session cookies if available")
        return False

    def _authenticate_medium(self, session):
        """Authenticate with Medium"""
        # Medium typically uses session cookies or OAuth
        session_cookie = os.getenv('MEDIUM_SESSION_COOKIE')
        if session_cookie:
            session.cookies.set('sid', session_cookie, domain='.medium.com')
            self.logger.info("   ✓ Medium session cookie applied")
            return True
        self.logger.info("   No Medium credentials found")
        return False

    def _authenticate_patreon(self, session):
        """Authenticate with Patreon"""
        session_cookie = os.getenv('PATREON_SESSION_COOKIE')
        if session_cookie:
            session.cookies.set('session_id', session_cookie, domain='.patreon.com')
            self.logger.info("   ✓ Patreon session cookie applied")
            return True
        self.logger.info("   No Patreon credentials found")
        return False

    def _authenticate_youtube(self, session):
        """Authenticate with YouTube (for premium content)"""
        api_key = os.getenv('YOUTUBE_API_KEY')
        if api_key:
            # YouTube API authentication would be handled differently
            self.logger.info("   ✓ YouTube API key available")
            return True
        self.logger.info("   No YouTube API key found")
        return False

    def _authenticate_ghost(self, url, session):
        """Authenticate with Ghost-based sites"""
        # Ghost sites often use member authentication
        site_name = urlparse(url).netloc.replace('.', '_').upper()
        email = os.getenv(f'{site_name}_EMAIL') or os.getenv('GHOST_EMAIL')
        password = os.getenv(f'{site_name}_PASSWORD') or os.getenv('GHOST_PASSWORD')

        if email and password:
            self.logger.info(f"   Attempting Ghost authentication for {site_name}")
            # Ghost authentication would need site-specific implementation
            return True
        self.logger.info("   No Ghost credentials found")
        return False

    def _authenticate_newsletter_generic(self, platform, session):
        """Authenticate with generic newsletter platforms"""
        platform_upper = platform.upper()
        session_cookie = os.getenv(f'{platform_upper}_SESSION_COOKIE')

        if session_cookie:
            session.cookies.set('session', session_cookie)
            self.logger.info(f"   ✓ {platform} session cookie applied")
            return True
        self.logger.info(f"   No {platform} credentials found")
        return False

    def _authenticate_social(self, platform, session):
        """Authenticate with social media platforms"""
        platform_upper = platform.upper()
        session_cookie = os.getenv(f'{platform_upper}_SESSION_COOKIE')

        if session_cookie:
            session.cookies.set('auth_token', session_cookie)
            self.logger.info(f"   ✓ {platform} session cookie applied")
            return True
        self.logger.info(f"   No {platform} credentials found")
        return False

    def _authenticate_generic(self, platform, session):
        """Generic authentication using session cookies"""
        # Check for platform-specific session cookies
        platform_upper = platform.upper()
        for cookie_name in ['SESSION_COOKIE', 'AUTH_TOKEN', 'ACCESS_TOKEN']:
            cookie_value = os.getenv(f'{platform_upper}_{cookie_name}')
            if cookie_value:
                session.cookies.set(cookie_name.lower(), cookie_value)
                self.logger.info(f"   ✓ {platform} {cookie_name.lower()} applied")
                return True

        self.logger.info(f"   No credentials found for {platform}")
        return False

    def _log_transcript_excerpts(self, formatted_text, video_id):
        """Log first and last 100 words of transcript if available"""
        if not formatted_text:
            return

        # Split into words to get first and last 100 words
        words = formatted_text.split()
        total_words = len(words)

        if total_words == 0:
            return

        self.logger.info(f"     📝 [HIGH PRIORITY] Transcript for {video_id}: {total_words} total words")

        # Log first 100 words
        if total_words > 0:
            first_100 = ' '.join(words[:100])
            self.logger.info(f"     📝 [HIGH PRIORITY] TRANSCRIPT START (first 100 words):")
            self.logger.info(f"     {first_100}")

        # Log last 100 words if transcript is longer than 100 words
        if total_words > 100:
            last_100 = ' '.join(words[-100:])
            self.logger.info(f"     📝 [HIGH PRIORITY] TRANSCRIPT END (last 100 words):")
            self.logger.info(f"     {last_100}")
        elif total_words <= 100:
            self.logger.info(f"     📝 [HIGH PRIORITY] Complete transcript logged above ({total_words} words)")

    def _find_claude_cli(self):
        """Find Claude CLI executable"""
        locations = [
            "/usr/local/bin/claude",
            "/opt/homebrew/bin/claude",
            "claude"  # Try PATH
        ]

        for location in locations:
            try:
                result = subprocess.run([location, "--version"],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return location
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        raise RuntimeError("Claude CLI not found. Please install Claude Code.")

    def _sanitize_filename(self, title):
        """Convert title to safe filename with underscores"""
        # Remove HTML tags if any
        title = re.sub(r'<[^>]+>', '', title)
        # Replace spaces and special chars with underscores
        filename = re.sub(r'[^\w\s-]', '', title)
        filename = re.sub(r'[\s-]+', '_', filename)
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        # Limit length
        return filename[:100] if filename else "untitled_article"

    def _extract_media_urls(self, soup, page_content):
        """Extract video and audio URLs from page content"""
        media_info = {
            'youtube_urls': [],
            'video_embeds': [],
            'iframe_sources': [],
            'audio_urls': [],
            'podcast_info': {}
        }

        # Extract YouTube URLs from various sources
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})'
        ]

        found_video_ids = set()
        for pattern in youtube_patterns:
            matches = re.findall(pattern, page_content)
            for match in matches:
                video_id = match
                if video_id not in found_video_ids:
                    found_video_ids.add(video_id)
                    media_info['youtube_urls'].append({
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'video_id': video_id,
                        'embed_url': f"https://www.youtube.com/embed/{video_id}"
                    })

        # Extract iframe sources
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src')
            if src:
                if 'youtube.com/embed' in src:
                    video_id_match = re.search(r'/embed/([a-zA-Z0-9_-]{11})', src)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        media_info['iframe_sources'].append({
                            'src': src,
                            'video_id': video_id,
                            'platform': 'youtube'
                        })
                else:
                    media_info['iframe_sources'].append({
                        'src': src,
                        'platform': 'other'
                    })

        # Extract audio URLs and podcast information
        # Look for Substack audio uploads
        substack_audio_pattern = r'api\.substack\.com/api/v1/audio/upload/([a-f0-9-]+)/src'
        substack_matches = re.findall(substack_audio_pattern, page_content)
        for audio_id in substack_matches:
            audio_url = f"https://api.substack.com/api/v1/audio/upload/{audio_id}/src"
            media_info['audio_urls'].append({
                'url': audio_url,
                'platform': 'substack',
                'type': 'podcast',
                'audio_id': audio_id
            })

        # Look for other audio file patterns
        audio_patterns = [
            r'(https?://[^\s<>"]+\.mp3[^\s<>"]*)',
            r'(https?://[^\s<>"]+\.wav[^\s<>"]*)',
            r'(https?://[^\s<>"]+\.m4a[^\s<>"]*)',
            r'(https?://[^\s<>"]+\.ogg[^\s<>"]*)'
        ]

        for pattern in audio_patterns:
            matches = re.findall(pattern, page_content)
            for audio_url in matches:
                media_info['audio_urls'].append({
                    'url': audio_url,
                    'platform': 'direct',
                    'type': 'audio_file'
                })

        # Extract podcast metadata from page
        podcast_title = soup.find('meta', property='og:title')
        podcast_description = soup.find('meta', property='og:description')

        if podcast_title or podcast_description:
            media_info['podcast_info'] = {
                'title': podcast_title.get('content') if podcast_title else '',
                'description': podcast_description.get('content') if podcast_description else '',
                'has_audio': len(media_info['audio_urls']) > 0
            }

        return media_info

    def _extract_youtube_transcript(self, video_id):
        """Extract transcript from YouTube video if available"""
        try:
            # Initialize the API instance
            ytt_api = YouTubeTranscriptApi()

            # Try to get transcript (both manual and auto-generated)
            transcript_list = ytt_api.list(video_id)

            # Try to get a manually created transcript first
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
                transcript_data = transcript.fetch()
                # Convert FetchedTranscript to list of dicts for JSON serialization
                transcript_list_data = []
                for entry in transcript_data:
                    transcript_list_data.append({
                        'start': entry.start,
                        'text': entry.text,
                        'duration': getattr(entry, 'duration', 0)
                    })
                return {
                    'success': True,
                    'type': 'manual',
                    'transcript': transcript_list_data,
                    'language': 'en'
                }
            except:
                # Fall back to auto-generated transcript
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    transcript_data = transcript.fetch()
                    # Convert FetchedTranscript to list of dicts for JSON serialization
                    transcript_list_data = []
                    for entry in transcript_data:
                        transcript_list_data.append({
                            'start': entry.start,
                            'text': entry.text,
                            'duration': getattr(entry, 'duration', 0)
                        })
                    return {
                        'success': True,
                        'type': 'auto_generated',
                        'transcript': transcript_list_data,
                        'language': 'en'
                    }
                except:
                    return {
                        'success': False,
                        'error': 'No English transcript available',
                        'transcript': []
                    }
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to fetch transcript: {str(e)}',
                'transcript': []
            }

    def _format_transcript_for_analysis(self, transcript_data):
        """Format transcript data into readable text for AI analysis"""
        if not transcript_data or not transcript_data.get('success'):
            return ""

        transcript = transcript_data.get('transcript', [])
        formatted_text = []

        for entry in transcript:
            # Handle dict objects (converted from FetchedTranscript)
            start_time = entry.get('start', 0)
            text = entry.get('text', '').strip()

            # Convert seconds to MM:SS format
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"{minutes}:{seconds:02d}"

            if text:
                formatted_text.append(f"[{timestamp}] {text}")

        return "\n".join(formatted_text)

    def _find_transcript_timestamp_for_content(self, transcript_data, search_keywords):
        """Find the timestamp in transcript where specific content/keywords appear"""
        if not transcript_data or not transcript_data.get('success'):
            return None, None

        transcript = transcript_data.get('transcript', [])
        search_keywords_lower = [kw.lower() for kw in search_keywords]

        best_matches = []

        for entry in transcript:
            start_time = entry.get('start', 0)
            text = entry.get('text', '').strip().lower()

            # Count how many keywords appear in this entry
            keyword_count = sum(1 for keyword in search_keywords_lower if keyword in text)

            if keyword_count > 0:
                minutes = int(start_time // 60)
                seconds = int(start_time % 60)
                timestamp = f"{minutes}:{seconds:02d}"

                best_matches.append({
                    'timestamp': timestamp,
                    'text': entry.get('text', '').strip(),
                    'keyword_count': keyword_count,
                    'start_time': start_time
                })

        # Sort by keyword count and then by time (prefer earlier occurrences)
        best_matches.sort(key=lambda x: (-x['keyword_count'], x['start_time']))

        if best_matches:
            best_match = best_matches[0]
            return best_match['timestamp'], best_match['text']

        return None, None

    def _extract_content_sections_from_transcript(self, transcript_data, num_sections=5):
        """Automatically divide transcript into logical sections based on content flow"""
        if not transcript_data or not transcript_data.get('success'):
            return []

        transcript = transcript_data.get('transcript', [])
        if len(transcript) < num_sections:
            return []

        total_duration = transcript[-1].get('start', 0) if transcript else 0
        section_duration = total_duration / num_sections

        sections = []
        for i in range(num_sections):
            section_start_time = i * section_duration

            # Find the closest transcript entry to this time
            closest_entry = min(transcript,
                              key=lambda x: abs(x.get('start', 0) - section_start_time))

            start_time = closest_entry.get('start', 0)
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"{minutes}:{seconds:02d}"

            # Get some context text for this section
            context_text = closest_entry.get('text', '').strip()

            sections.append({
                'timestamp': timestamp,
                'start_time': start_time,
                'context_text': context_text,
                'section_number': i + 1,
                'duration_minutes': int(section_duration / 60) if section_duration > 60 else 1
            })

        return sections

    def _select_main_podcast_episode(self, audio_urls):
        """Select the main podcast episode from multiple audio files, deduplicating and filtering segments"""
        if not audio_urls:
            return None

        # Group audio files by unique identifiers
        unique_audios = {}
        for audio in audio_urls:
            audio_id = audio.get('audio_id', audio.get('url', ''))
            if audio_id and audio_id not in unique_audios:
                unique_audios[audio_id] = audio

        # Convert back to list
        deduplicated_audios = list(unique_audios.values())

        if len(deduplicated_audios) == 1:
            return deduplicated_audios[0]

        # Scoring system to identify the main episode vs segments/formats
        def score_audio_file(audio):
            score = 0
            url = audio.get('url', '').lower()
            audio_id = audio.get('audio_id', '').lower()

            # Prefer files that seem like main episodes (not segments)
            if any(term in url or term in audio_id for term in ['episode', 'full', 'complete']):
                score += 10

            # Deprioritize files that seem like segments or clips
            if any(term in url or term in audio_id for term in ['segment', 'clip', 'part', 'chapter']):
                score -= 5

            # Deprioritize files that seem like different formats
            if any(term in url or term in audio_id for term in ['preview', 'sample', 'intro', 'outro']):
                score -= 3

            # Prefer substack podcast type
            if audio.get('platform') == 'substack' and audio.get('type') == 'podcast':
                score += 5

            # Use audio_id length as tiebreaker (longer IDs might be more specific)
            score += len(audio.get('audio_id', '')) * 0.01

            return score

        # Sort by score and return the highest scoring audio file
        scored_audios = [(score_audio_file(audio), audio) for audio in deduplicated_audios]
        scored_audios.sort(key=lambda x: x[0], reverse=True)

        return scored_audios[0][1] if scored_audios else deduplicated_audios[0]

    def _create_metadata_for_prompt(self, metadata):
        """Create a stripped-down version of metadata for Claude prompt (without full transcripts)"""
        stripped_metadata = {
            'title': metadata.get('title', ''),
            'url': metadata.get('url', ''),
            'domain': metadata.get('domain', ''),
            'has_video_indicators': metadata.get('has_video_indicators', False),
            'has_audio_indicators': metadata.get('has_audio_indicators', False),
            'extracted_at': metadata.get('extracted_at', ''),
            'media_info': {
                'youtube_urls': metadata.get('media_info', {}).get('youtube_urls', []),
                'audio_urls': [
                    {
                        'platform': audio.get('platform', ''),
                        'type': audio.get('type', '')
                    } for audio in metadata.get('media_info', {}).get('audio_urls', [])
                ],
                'podcast_info': metadata.get('media_info', {}).get('podcast_info', {})
            }
        }

        # Add transcript summary info without the actual transcript data
        if metadata.get('transcripts'):
            transcript_summary = {}
            for video_id, transcript_data in metadata['transcripts'].items():
                if transcript_data.get('success'):
                    transcript_list = transcript_data.get('transcript', [])
                    total_duration = transcript_list[-1].get('start', 0) if transcript_list else 0
                    transcript_summary[video_id] = {
                        'success': True,
                        'type': transcript_data.get('type', 'unknown'),
                        'language': transcript_data.get('language', 'en'),
                        'total_entries': len(transcript_list),
                        'duration_seconds': int(total_duration),
                        'duration_formatted': f"{int(total_duration // 60)}:{int(total_duration % 60):02d}"
                    }
                else:
                    transcript_summary[video_id] = {
                        'success': False,
                        'error': transcript_data.get('error', 'Unknown error')
                    }
            stripped_metadata['transcript_summary'] = transcript_summary

        return stripped_metadata

    def _extract_basic_metadata(self, url):
        """Extract basic metadata from URL (deterministic part)"""
        try:
            # Detect platform and authenticate accordingly
            platform = self._detect_platform(url)

            # Attempt platform-specific authentication if needed
            self._authenticate_for_platform(platform, url, self.session)

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract basic info
            title = soup.find('title')
            title = title.get_text().strip() if title else "Untitled Article"

            # Extract video and audio information
            media_info = self._extract_media_urls(soup, response.text)

            # Determine if media content exists
            has_video_indicators = (
                len(media_info['youtube_urls']) > 0 or
                len(media_info['iframe_sources']) > 0 or
                'youtube.com' in response.text or
                'youtu.be' in response.text or
                soup.find('video') is not None
            )

            has_audio_indicators = (
                len(media_info['audio_urls']) > 0 or
                'substack.com/api/v1/audio' in response.text or
                soup.find('audio') is not None or
                'podcast' in response.text.lower()
            )

            # Extract YouTube transcripts if videos found
            transcripts = {}
            has_video_transcript = False

            if media_info['youtube_urls']:
                self.logger.info("   Found YouTube videos, extracting transcript from main video...")
                # Only process the first/main video, ignore related content
                main_video = media_info['youtube_urls'][0]
                video_id = main_video['video_id']

                # HIGH PRIORITY: Log main video URLs and embed codes
                self.logger.info(f"     🎥 [HIGH PRIORITY] Main Video URL: {main_video['url']}")
                self.logger.info(f"     🎥 [HIGH PRIORITY] Embed URL: {main_video['embed_url']}")

                if len(media_info['youtube_urls']) > 1:
                    self.logger.info(f"     Found {len(media_info['youtube_urls'])} videos total, processing only the main video")

                self.logger.info(f"     Extracting transcript for: {video_id}")
                transcript_data = self._extract_youtube_transcript(video_id)
                transcripts[video_id] = transcript_data

                if transcript_data['success']:
                    self.logger.info(f"     ✓ Transcript extracted ({transcript_data['type']})")
                    has_video_transcript = True
                    # Log transcript excerpts if available
                    if transcript_data.get('transcript'):
                        formatted_text = self._format_transcript_for_analysis(transcript_data)
                        self._log_transcript_excerpts(formatted_text, video_id)
                else:
                    self.logger.info(f"     ✗ No transcript available: {transcript_data.get('error', 'Unknown error')}")

                # Update media_info to only include the main video
                media_info['youtube_urls'] = [main_video]

            # Only process audio if we don't have video content with transcripts
            if media_info['audio_urls'] and not has_video_transcript:
                # Deduplicate and select main podcast episode
                main_audio = self._select_main_podcast_episode(media_info['audio_urls'])
                if main_audio:
                    self.logger.info(f"   Found audio content, selected main podcast episode:")
                    self.logger.info(f"     🎧 [HIGH PRIORITY] Audio URL: {main_audio['url']}")
                    self.logger.info(f"     Audio: {main_audio['platform']} - {main_audio['type']}")
                    if main_audio['platform'] == 'substack':
                        self.logger.info(f"     Audio ID: {main_audio['audio_id']}")
                        self.logger.info("     Note: Substack audio transcription requires manual processing or external service")
                    # Update media_info to only include the main audio file
                    media_info['audio_urls'] = [main_audio]
                else:
                    self.logger.info("   Audio files found but no main episode could be identified")
                    media_info['audio_urls'] = []
            elif media_info['audio_urls'] and has_video_transcript:
                self.logger.info(f"   Found {len(media_info['audio_urls'])} audio files, but skipping since video transcript is available")
                # Clear audio URLs since we're prioritizing video
                media_info['audio_urls'] = []

            return {
                'title': title,
                'url': url,
                'domain': urlparse(url).netloc,
                'has_video_indicators': has_video_indicators,
                'has_audio_indicators': has_audio_indicators,
                'media_info': media_info,
                'transcripts': transcripts,
                'extracted_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'title': f"Article from {urlparse(url).netloc}",
                'url': url,
                'domain': urlparse(url).netloc,
                'has_video_indicators': False,
                'has_audio_indicators': False,
                'media_info': {
                    'youtube_urls': [],
                    'video_embeds': [],
                    'iframe_sources': [],
                    'audio_urls': [],
                    'podcast_info': {}
                },
                'transcripts': {},
                'extraction_error': str(e),
                'extracted_at': datetime.now().isoformat()
            }

    def _call_claude_api(self, prompt):
        """Call Claude Code API for AI-powered analysis"""
        try:
            # Call Claude CLI with --print flag for non-interactive mode
            result = subprocess.run([
                self.claude_cmd,
                "--print",
                "--output-format", "text",
                prompt
            ], capture_output=True, text=True, timeout=120, cwd=self.base_dir)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error calling Claude API: {result.stderr}"

        except subprocess.TimeoutExpired:
            return f"Claude API call timed out after 120 seconds"
        except Exception as e:
            return f"Error in Claude API call: {str(e)}"

    def _extract_json_from_response(self, response):
        """Extract and parse JSON from Claude's response, handling various formats"""
        # Try to find JSON block in response
        import re

        # Look for JSON between ```json and ``` or just plain JSON
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{.*?\})'
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        # If no JSON found, return None
        return None

    def _format_summary_as_html(self, summary_text):
        """Convert plain text summary to formatted HTML"""
        # Handle markdown-like formatting
        html = summary_text.replace('\n\n', '</p><p>')
        html = html.replace('\n• ', '<br>• ')
        html = html.replace('\n## ', '</p><h3>')
        html = html.replace('\n### ', '</p><h4>')

        # Wrap in paragraph tags
        if not html.startswith('<'):
            html = f'<p>{html}</p>'

        # Close any opened headers
        html = html.replace('<h3>', '<h3>').replace('\n', '</h3><p>')
        html = html.replace('<h4>', '<h4>').replace('\n', '</h4><p>')

        return html

    def _generate_summary_with_ai(self, url, metadata):
        """Use AI to generate content summary (non-deterministic part)"""
        media_context = ""
        transcript_context = ""

        # Handle video content
        if metadata.get('media_info') and metadata['media_info']['youtube_urls']:
            media_context += f"""
        IMPORTANT: This article contains video content. Video URLs found: {metadata['media_info']['youtube_urls']}

        Please focus on extracting video timestamps with the following format:
        - Use MM:SS format for timestamps (e.g., "5:23", "12:45", "1:02:30")
        - Provide detailed descriptions of what happens at each timestamp
        - Aim for 5-8 key timestamps that represent the most valuable content
        - Include timestamps for: key insights, important discussions, actionable advice, demonstrations
        """

        # Handle audio/podcast content
        if metadata.get('media_info') and metadata['media_info']['audio_urls']:
            media_context += f"""
        IMPORTANT: This article contains audio/podcast content. Audio URLs found: {metadata['media_info']['audio_urls']}

        This appears to be a podcast episode. Please:
        - Identify key discussion points and insights from the conversation
        - Extract actionable advice or key takeaways
        - Note the participants/speakers if mentioned in the content
        - Provide time-based highlights if duration information is available
        - Focus on the most valuable segments for listeners

        Audio Platform: {metadata['media_info']['audio_urls'][0]['platform'] if metadata['media_info']['audio_urls'] else 'unknown'}
        """

        # Include transcript data if available
        if metadata.get('transcripts'):
            available_transcripts = []
            full_transcript_text = ""
            for video_id, transcript_data in metadata['transcripts'].items():
                if transcript_data.get('success'):
                    formatted_transcript = self._format_transcript_for_analysis(transcript_data)
                    if formatted_transcript:
                        full_transcript_text += formatted_transcript + "\n\n"
                        # Include more of the transcript for better analysis
                        available_transcripts.append(f"""
        VIDEO TRANSCRIPT for {video_id} ({transcript_data.get('type', 'unknown')} transcript):
        {formatted_transcript[:8000]}{'...' if len(formatted_transcript) > 8000 else ''}
        """)

            if available_transcripts:
                # Generate automatic sections from transcript for reference
                sections_from_transcript = []
                for video_id, transcript_data in metadata['transcripts'].items():
                    if transcript_data.get('success'):
                        auto_sections = self._extract_content_sections_from_transcript(transcript_data, 6)
                        sections_from_transcript.extend(auto_sections)

                sections_context = ""
                if sections_from_transcript:
                    sections_context = f"""

        SUGGESTED SECTIONS (based on transcript timeline):
        {chr(10).join([f"Section {s['section_number']}: {s['timestamp']} - '{s['context_text'][:100]}...' (≈{s['duration_minutes']} min)" for s in sections_from_transcript])}
        """

                transcript_context = f"""
        TRANSCRIPT DATA AVAILABLE: The following are actual transcripts from the YouTube videos.
        Use these to create ACCURATE timestamps and content descriptions:

        {''.join(available_transcripts)}
        {sections_context}

        CRITICAL: Since you have the actual transcript with timestamps, you must:
        1. Find the EXACT timestamp where each key insight is mentioned by searching through the transcript
        2. Map summary sections to their corresponding timestamps in the transcript
        3. Use only timestamps that actually exist in the transcript data
        4. Quote specific phrases from the transcript when referencing insights (brief 5-10 word quotes)
        5. Ensure every insight has a corresponding timestamp from the actual transcript
        6. Use the suggested sections as a guide but feel free to adjust based on content flow
        7. When finding timestamps, look for keywords and phrases that match your insights
        """

        prompt = f"""
        Analyze this article: {url}

        Create a comprehensive summary with the following structure:
        1. Write a clear, structured summary (max 1000 words) in HTML format with embedded timestamps for each major subsection
        2. Extract 5-8 key insights as bullet points
        3. If video/audio content exists, identify specific timestamps with detailed descriptions

        {media_context}
        {transcript_context}

        ENHANCED TIMESTAMP MAPPING REQUIREMENTS:
        When transcript data is available, you MUST:

        1. For KEY INSIGHTS:
           - Search through the transcript to find the exact moment each insight is discussed
           - Include the specific timestamp (MM:SS) where that insight appears
           - Quote a brief phrase from the transcript to validate the timestamp
           - If an insight spans multiple parts, use the first significant mention

        2. For SUMMARY CONTENT:
           - Structure the summary with clear H3/H4 headings for major subsections
           - Add clickable timestamps to each subsection heading where that content is discussed
           - Format like: '<h3>🎯 Topic Name <span class="section-timestamp" onclick="jumpToTime(1800)" title="Jump to 30:00">⏰ 30:00</span></h3>'
           - Ensure the timestamps correspond to where that topic actually begins in the video
           - Cover the content chronologically and logically

        3. For MEDIA TIMESTAMPS:
           - Identify 6-10 key moments throughout the video
           - Focus on: key insights, important quotes, actionable advice, transitions, conclusions
           - Provide rich descriptions of what happens at each timestamp
           - Ensure timestamps are distributed throughout the video timeline

        VALIDATION RULES:
        - Only use timestamps that actually exist in the provided transcript
        - Verify each timestamp by checking the actual transcript text
        - If you cannot find a specific timestamp for an insight, mark it as "general" content
        - Prioritize accuracy over completeness

        Article metadata: {json.dumps(self._create_metadata_for_prompt(metadata), indent=2)}

        Return your response in this JSON format:
        {{
            "summary": "HTML formatted summary content with embedded section timestamps",
            "key_insights": [
                {{"insight": "insight text", "timestamp": "MM:SS", "transcript_quote": "brief quote from transcript at this time"}},
                {{"insight": "insight text", "timestamp": "MM:SS", "transcript_quote": "brief quote from transcript at this time"}},
                ...
            ],
            "media_timestamps": [
                {{"time": "MM:SS", "description": "detailed description of what happens at this time", "type": "video|audio", "transcript_quote": "relevant quote from transcript"}},
                ...
            ]
        }}

        Note: For audio content, if no specific timestamps are available, focus on key discussion topics and insights instead.
        """

        response = self._call_claude_api(prompt)

        # Try to extract JSON from response
        parsed_json = self._extract_json_from_response(response)

        if parsed_json:
            # Ensure summary is properly formatted as HTML
            if 'summary' in parsed_json:
                summary = parsed_json['summary']
                if not any(tag in summary for tag in ['<p>', '<div>', '<h1>', '<h2>', '<h3>']):
                    # Convert plain text to HTML
                    parsed_json['summary'] = self._format_summary_as_html(summary)

            return parsed_json
        else:
            # Fallback: format the entire response as HTML summary
            formatted_summary = self._format_summary_as_html(response)
            return {
                "summary": formatted_summary,
                "key_insights": [{"insight": "Content analyzed - see summary for details", "timestamp": ""}],
                "media_timestamps": [],
                "summary_sections": []
            }

    def _load_template(self, template_name="article_summary.html"):
        """Load HTML template from templates directory"""
        template_path = self.base_dir / "programs" / "video_summarizer" / "scripts" / "templates" / template_name
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Template not found: {template_path}")

    def _convert_timestamp_to_seconds(self, timestamp):
        """Convert MM:SS or H:MM:SS timestamp to seconds"""
        parts = timestamp.split(':')
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # H:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0

    def _generate_media_embed_html(self, metadata):
        """Generate video and audio embed HTML if media URLs are found"""
        media_info = metadata.get('media_info', {})

        # Prioritize YouTube embeds for video content
        if media_info.get('youtube_urls'):
            video_data = media_info['youtube_urls'][0]  # Use first video found
            video_id = video_data['video_id']

            embed_html = f'''
    <div class="video-container">
        <h2>🎥 Watch the Video</h2>
        <div class="speed-notice">
            ⚡ Video automatically plays at 2x speed for efficient viewing. You can adjust speed in player controls.
        </div>
        <div class="video-embed">
            <iframe
                src="https://www.youtube.com/embed/{video_id}?enablejsapi=1&playsinline=1"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen>
            </iframe>
        </div>
    </div>'''
            return embed_html

        elif media_info.get('iframe_sources'):
            # Use first iframe source
            iframe_data = media_info['iframe_sources'][0]
            if iframe_data.get('platform') == 'youtube':
                video_id = iframe_data.get('video_id')
                embed_html = f'''
    <div class="video-container">
        <h2>🎥 Watch the Video</h2>
        <div class="speed-notice">
            ⚡ Video automatically plays at 2x speed for efficient viewing. You can adjust speed in player controls.
        </div>
        <div class="video-embed">
            <iframe
                src="https://www.youtube.com/embed/{video_id}?enablejsapi=1&playsinline=1"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen>
            </iframe>
        </div>
    </div>'''
                return embed_html

        # Handle audio content (podcasts, etc.)
        elif media_info.get('audio_urls'):
            audio_data = media_info['audio_urls'][0]  # Use first audio found

            if audio_data['platform'] == 'substack':
                audio_id = audio_data['audio_id']
                embed_html = f'''
    <div class="audio-container">
        <h2>🎧 Listen to the Podcast</h2>
        <div class="audio-embed">
            <audio controls style="width: 100%; max-width: 600px;">
                <source src="{audio_data['url']}" type="audio/mpeg">
                <p>Your browser doesn't support HTML5 audio.
                <a href="{audio_data['url']}">Download the audio file</a>.</p>
            </audio>
        </div>
        <p class="audio-info">
            <strong>Platform:</strong> Substack Podcast<br>
            <strong>Audio ID:</strong> {audio_id}
        </p>
    </div>'''
                return embed_html
            else:
                # Generic audio player for other audio files
                embed_html = f'''
    <div class="audio-container">
        <h2>🎧 Listen to the Audio</h2>
        <div class="audio-embed">
            <audio controls style="width: 100%; max-width: 600px;">
                <source src="{audio_data['url']}" type="audio/mpeg">
                <p>Your browser doesn't support HTML5 audio.
                <a href="{audio_data['url']}">Download the audio file</a>.</p>
            </audio>
        </div>
        <p class="audio-info">
            <strong>Platform:</strong> {audio_data['platform'].title()}<br>
            <strong>Type:</strong> {audio_data['type'].replace('_', ' ').title()}
        </p>
    </div>'''
                return embed_html

        return ''

    def _generate_section_html(self, ai_summary, metadata):
        """Generate dynamic HTML sections based on AI summary content"""
        sections = {}

        # Generate media embed section (video/audio)
        media_embed = self._generate_media_embed_html(metadata)
        sections['MEDIA_EMBED_SECTION'] = media_embed

        # Generate insights section
        insights = ai_summary.get('key_insights', [])
        media_info = metadata.get('media_info', {})

        if insights and len(insights) > 0:
            # Check if insights are in new format with timestamps or old format
            first_insight = insights[0]

            # Skip if it's just the fallback content
            if (isinstance(first_insight, dict) and first_insight.get('insight') == "Content analyzed - see summary for details") or \
               (isinstance(first_insight, str) and first_insight in ["Analysis completed but formatting needs review", "Content analyzed - see summary for details"]):
                sections['INSIGHTS_SECTION'] = ''
            else:
                insights_html = '<div class="summary-section"><h3>💡 Key Insights</h3><ul>'

                for insight in insights:
                    if isinstance(insight, dict):
                        # New format with timestamp and optional transcript quote
                        insight_text = insight.get('insight', '')
                        timestamp = insight.get('timestamp', '')
                        transcript_quote = insight.get('transcript_quote', '')

                        if timestamp and media_info.get('youtube_urls'):
                            # Convert timestamp to seconds for video jump functionality
                            seconds = self._convert_timestamp_to_seconds(timestamp)
                            # Removed transcript quotes from Key Insights section for cleaner presentation
                            insights_html += f'''<li class="insight-with-timestamp">
                                {insight_text}
                                <span class="insight-timestamp" onclick="jumpToTime({seconds})" title="Jump to {timestamp}">🎬 {timestamp}</span>
                            </li>'''
                        else:
                            insights_html += f'<li>{insight_text}</li>'
                    else:
                        # Old format (plain string)
                        insights_html += f'<li>{insight}</li>'

                insights_html += '</ul></div>'
                sections['INSIGHTS_SECTION'] = insights_html
        else:
            sections['INSIGHTS_SECTION'] = ''

        # Generate interactive media timestamps section (video/audio)
        timestamps = ai_summary.get('media_timestamps', [])  # Updated to use media_timestamps

        if timestamps:
            # Check if we have video content with interactivity
            if media_info.get('youtube_urls'):
                video_id = media_info['youtube_urls'][0]['video_id']
                timestamps_html = '<div class="video-timestamps"><h3>🎬 Interactive Video Highlights</h3>'
                timestamps_html += '<p><em>Click timestamps to jump to that part of the video:</em></p><ul>'

                for ts in timestamps:
                    time_str = ts.get("time", "0:00")
                    description = ts.get("description", "No description")
                    media_type = ts.get("type", "video")
                    transcript_quote = ts.get("transcript_quote", "")
                    seconds = self._convert_timestamp_to_seconds(time_str)

                    quote_html = f'<div class="transcript-quote">"{transcript_quote}"</div>' if transcript_quote else ''

                    timestamps_html += f'''
                    <li class="timestamp-item">
                        <span class="timestamp-link" onclick="jumpToTime({seconds})">
                            <strong>{time_str}</strong>
                        </span>
                        <button class="play-button" onclick="jumpToTime({seconds})">▶ Play</button>
                        <br>
                        <span class="timestamp-description">{description}</span>
                        {quote_html}
                    </li>'''

                timestamps_html += '</ul></div>'
                sections['TIMESTAMPS_SECTION'] = timestamps_html
                sections['VIDEO_ID'] = video_id

            # Handle audio content (non-interactive timestamps)
            elif media_info.get('audio_urls'):
                timestamps_html = '<div class="audio-timestamps"><h3>🎧 Audio Highlights</h3>'
                timestamps_html += '<p><em>Key moments from the audio content:</em></p><ul>'

                for ts in timestamps:
                    time_str = ts.get("time", "")
                    description = ts.get("description", "No description")
                    media_type = ts.get("type", "audio")

                    if time_str:
                        timestamps_html += f'''
                        <li class="timestamp-item">
                            <strong>{time_str}</strong> - {description}
                        </li>'''
                    else:
                        # If no time available, just show as discussion point
                        timestamps_html += f'''
                        <li class="timestamp-item">
                            • {description}
                        </li>'''

                timestamps_html += '</ul></div>'
                sections['TIMESTAMPS_SECTION'] = timestamps_html
                sections['VIDEO_ID'] = ''  # No video ID for audio

            else:
                # Generic timestamps (neither video nor audio detected)
                timestamps_html = '<div class="media-timestamps"><h3>📋 Key Points</h3><ul>'
                for ts in timestamps:
                    time_str = ts.get("time", "")
                    description = ts.get("description", "No description")
                    if time_str:
                        timestamps_html += f'<li><strong>{time_str}</strong> - {description}</li>'
                    else:
                        timestamps_html += f'<li>• {description}</li>'
                timestamps_html += '</ul></div>'
                sections['TIMESTAMPS_SECTION'] = timestamps_html
                sections['VIDEO_ID'] = ''
        else:
            sections['TIMESTAMPS_SECTION'] = ''
            sections['VIDEO_ID'] = ''

        # Summary sections are now integrated into the main summary content
        sections['SUMMARY_SECTIONS'] = ''

        return sections

    def _generate_html_content(self, metadata, ai_summary):
        """Generate HTML content using external template (deterministic template loading)"""
        # Load the HTML template
        template = self._load_template()

        # Generate dynamic sections
        sections = self._generate_section_html(ai_summary, metadata)

        # Prepare template variables
        template_vars = {
            'TITLE': metadata['title'],
            'DOMAIN': metadata['domain'],
            'URL': metadata['url'],
            'EXTRACTED_AT': datetime.fromisoformat(metadata['extracted_at'].replace('Z', '+00:00')).strftime('%B %d, %Y at %I:%M %p'),
            'HAS_VIDEO': 'Yes' if metadata.get('has_video_indicators') else 'No',
            'HAS_AUDIO': 'Yes' if metadata.get('has_audio_indicators') else 'No',
            'SUMMARY_CONTENT': ai_summary.get('summary', 'Summary not available'),
            'GENERATION_DATE': datetime.now().strftime('%B %d, %Y'),
            **sections
        }

        # Replace template variables
        html_content = template
        for var, value in template_vars.items():
            html_content = html_content.replace(f'{{{{{var}}}}}', value)

        return html_content

    def _collect_index_statistics(self, articles_data):
        """Collect statistics about the article collection"""
        stats = {
            'total_articles': len(articles_data),
            'video_articles': 0,
            'audio_articles': 0,
            'domains': set(),
            'last_updated': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }

        for article in articles_data:
            # Check if article has video or audio indicators
            article_path = self.html_dir / article['filename']
            if article_path.exists():
                try:
                    with open(article_path, 'r') as f:
                        content = f.read()
                        if 'video-container' in content or 'Video Content:</strong> Yes' in content:
                            stats['video_articles'] += 1
                        if 'audio-container' in content or 'Audio Content:</strong> Yes' in content:
                            stats['audio_articles'] += 1
                except:
                    pass

            # Extract domain from URL if available
            if 'url' in article:
                domain = urlparse(article['url']).netloc
                if domain:
                    stats['domains'].add(domain)

        stats['domains_count'] = len(stats['domains'])
        return stats

    def _generate_articles_list_html(self, articles_data):
        """Generate HTML for articles list"""
        articles_html = ""

        for article in articles_data:
            filename = article['filename']
            title = article['title']
            description = article['description']
            is_updated = 'Updated on' in description

            # Check if article has video or audio
            has_video = False
            has_audio = False
            article_path = self.html_dir / filename
            if article_path.exists():
                try:
                    with open(article_path, 'r') as f:
                        content = f.read()
                        has_video = 'video-container' in content or 'Video Content:</strong> Yes' in content
                        has_audio = 'audio-container' in content or 'Audio Content:</strong> Yes' in content
                except:
                    pass

            # Generate indicators
            indicators = ""
            if has_video:
                indicators += '<span class="video-indicator">📹 VIDEO</span>'
            if has_audio:
                indicators += '<span class="audio-indicator">🎧 AUDIO</span>'
            if is_updated:
                indicators += '<span class="updated-indicator">🔄 UPDATED</span>'

            articles_html += f'''
        <li class="article-item">
            <a href="{filename}" class="article-title">{title}{indicators}</a>
            <p class="article-description">{description}</p>
        </li>'''

        return articles_html

    def _update_index_html(self, new_filename, title, metadata=None):
        """Update index.html with new article using external template"""
        index_path = self.html_dir / "index.html"

        # Collect existing articles data
        articles_data = []

        if index_path.exists():
            # Parse existing index to extract articles
            with open(index_path, 'r') as f:
                content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            article_list = soup.find('ul', class_='article-list')

            if article_list:
                for item in article_list.find_all('li', class_='article-item'):
                    link = item.find('a', class_='article-title')
                    desc = item.find('p', class_='article-description')
                    if link and desc:
                        articles_data.append({
                            'filename': link.get('href'),
                            'title': link.get_text().replace('📹 VIDEO', '').replace('🔄 UPDATED', '').strip(),
                            'description': desc.get_text(),
                            'url': metadata.get('url', '') if metadata else ''
                        })

        # Check if article already exists and update or add
        existing_article = None
        for i, article in enumerate(articles_data):
            if article['filename'] == new_filename:
                existing_article = i
                break

        if existing_article is not None:
            # Update existing article
            articles_data[existing_article].update({
                'title': title,
                'description': f"Updated on {datetime.now().strftime('%B %d, %Y')}",
                'url': metadata.get('url', '') if metadata else articles_data[existing_article].get('url', '')
            })
            # Move to front (most recent)
            article = articles_data.pop(existing_article)
            articles_data.insert(0, article)
        else:
            # Add new article at the beginning
            articles_data.insert(0, {
                'filename': new_filename,
                'title': title,
                'description': f"Generated on {datetime.now().strftime('%B %d, %Y')}",
                'url': metadata.get('url', '') if metadata else ''
            })

        # Generate statistics
        stats = self._collect_index_statistics(articles_data)

        # Generate articles list HTML
        articles_list_html = self._generate_articles_list_html(articles_data)

        # Load index template
        index_template = self._load_template("index.html")

        # Prepare template variables
        template_vars = {
            'TOTAL_ARTICLES': str(stats['total_articles']),
            'VIDEO_ARTICLES': str(stats['video_articles']),
            'AUDIO_ARTICLES': str(stats['audio_articles']),
            'DOMAINS_COUNT': str(stats['domains_count']),
            'ARTICLES_LIST': articles_list_html,
            'LAST_UPDATED': stats['last_updated']
        }

        # Replace template variables
        index_content = index_template
        for var, value in template_vars.items():
            index_content = index_content.replace(f'{{{{{var}}}}}', value)

        # Write updated index
        with open(index_path, 'w') as f:
            f.write(index_content)

    def _git_commit_and_push(self, filename):
        """Handle git operations (deterministic)"""
        try:
            os.chdir(self.base_dir)

            # Add files
            subprocess.run(['git', 'add', f'programs/video_summarizer/output/article_summaries/{filename}'], check=True)
            subprocess.run(['git', 'add', 'programs/video_summarizer/output/article_summaries/index.html'], check=True)

            # Commit
            commit_msg = f"""Add article summary: {filename}

Generated via hybrid Python + Claude Code approach

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)

            # Push
            subprocess.run(['git', 'push'], check=True)

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git operation failed: {e}")
            return False

    def process_article(self, url):
        """Main processing pipeline"""
        self.logger.info(f"Processing article: {url}")

        # Step 1: Extract basic metadata (deterministic)
        self.logger.info("1. Extracting metadata...")
        metadata = self._extract_basic_metadata(url)
        self.logger.info(f"   Title: {metadata['title']}")

        # Step 2: Generate filename (deterministic)
        filename = self._sanitize_filename(metadata['title']) + '.html'
        self.logger.info(f"   Filename: {filename}")

        # Step 3: AI-powered content analysis (non-deterministic)
        self.logger.info("2. Analyzing content with AI...")
        ai_summary = self._generate_summary_with_ai(url, metadata)

        # Step 4: Generate HTML (deterministic template)
        self.logger.info("3. Generating HTML...")
        html_content = self._generate_html_content(metadata, ai_summary)

        # Step 5: Write file (deterministic)
        html_path = self.html_dir / filename
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        self.logger.info(f"   Created: {html_path}")

        # Step 6: Update index (deterministic)
        self.logger.info("4. Updating index...")
        self._update_index_html(filename, metadata['title'], metadata)

        # Step 7: Git operations (deterministic)
        self.logger.info("5. Committing to git...")
        if self._git_commit_and_push(filename):
            self.logger.info("✅ Successfully committed and pushed to GitHub")
        else:
            self.logger.error("❌ Git operations failed")

        self.logger.info(f"✅ Processing complete: {filename}")
        return filename

def main():
    if len(sys.argv) != 2:
        print("Usage: python video_article_summarizer.py <article_url>")
        sys.exit(1)

    url = sys.argv[1]
    summarizer = VideoArticleSummarizer()

    try:
        result = summarizer.process_article(url)
        summarizer.logger.info(f"Success! Generated: {result}")
        print(f"Success! Generated: {result}")  # Also print to stdout for slash command
    except Exception as e:
        error_msg = f"Error: {e}"
        if hasattr(summarizer, 'logger'):
            summarizer.logger.error(error_msg)
        print(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()