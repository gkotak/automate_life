"""
Transcript Processing Module

Handles extraction and processing of transcripts from various sources.
"""

import logging
from pathlib import Path
from typing import Dict, Optional
import requests

logger = logging.getLogger(__name__)


class TranscriptProcessor:
    """Handles transcript extraction and processing"""

    def __init__(self, base_dir: Path, session: requests.Session):
        self.base_dir = base_dir
        self.session = session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_youtube_transcript(self, video_id: str) -> Optional[Dict]:
        """
        Extract transcript from YouTube video

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with transcript data or None if not available
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            # Initialize the API instance
            ytt_api = YouTubeTranscriptApi()

            # Try to get transcript (both manual and auto-generated)
            transcript_list = ytt_api.list(video_id)

            # Try to get a manually created transcript first
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
                transcript_data = transcript.fetch()
                transcript_type = 'manual'
            except Exception:
                # Fall back to auto-generated transcript
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    transcript_data = transcript.fetch()
                    transcript_type = 'auto_generated'
                except Exception:
                    return {
                        'success': False,
                        'error': 'No English transcript available',
                        'video_id': video_id
                    }

            # Convert to serializable format
            transcript_list_data = []
            for entry in transcript_data:
                transcript_list_data.append({
                    'start': entry.start,
                    'text': entry.text,
                    'duration': getattr(entry, 'duration', 0)
                })

            return {
                'success': True,
                'transcript': transcript_list_data,
                'type': transcript_type,
                'video_id': video_id,
                'total_entries': len(transcript_list_data)
            }

        except ImportError:
            self.logger.error("youtube-transcript-api not installed")
            return {
                'success': False,
                'error': 'youtube-transcript-api not installed',
                'video_id': video_id
            }
        except Exception as e:
            self.logger.warning(f"Could not extract transcript for {video_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'video_id': video_id
            }