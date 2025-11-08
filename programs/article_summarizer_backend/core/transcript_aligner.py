"""
Transcript Alignment Module

Aligns text transcripts with audio files to add precise timestamps.
Uses Deepgram for audio transcription with word-level timestamps,
then matches the provided text transcript to those timestamps.

This module is shared by:
- article_summarizer_backend (Substack audio posts, YouTube videos)
- earnings_insights (Seeking Alpha earnings calls)
"""

import logging
import os
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AlignedSegment:
    """A segment of transcript with timing information"""
    speaker: str
    text: str
    start: float  # seconds
    end: float    # seconds
    confidence: float = 0.9


class TranscriptAligner:
    """
    Aligns text transcripts with audio files using Deepgram

    Usage:
        aligner = TranscriptAligner()
        aligned = await aligner.align_transcript(audio_url, transcript_text)
        formatted = format_aligned_transcript_for_claude(aligned)
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.deepgram_api_key = os.getenv('DEEPGRAM_API_KEY')

        if not self.deepgram_api_key:
            self.logger.warning("⚠️ DEEPGRAM_API_KEY not set - alignment will fail")

    async def align_transcript(
        self,
        audio_url: str,
        transcript_text: str
    ) -> Dict:
        """
        Align a text transcript with audio timestamps

        Args:
            audio_url: URL to audio file (MP3, etc.)
            transcript_text: Clean text transcript with speaker labels

        Returns:
            {
                "aligned_transcript": [AlignedSegment, ...],
                "deepgram_transcript": {...},  # Full Deepgram response
                "source": "aligned_with_deepgram"
            }
        """
        self.logger.info(f"🔄 [ALIGNMENT] Starting transcript alignment")
        self.logger.info(f"   Audio URL: {audio_url[:100]}...")
        self.logger.info(f"   Transcript length: {len(transcript_text)} chars")

        # Step 1: Transcribe audio with Deepgram (get word-level timestamps)
        self.logger.info("🎤 [DEEPGRAM] Transcribing audio with word-level timestamps...")
        deepgram_result = await self._transcribe_with_deepgram(audio_url)

        if not deepgram_result:
            self.logger.error("❌ [ALIGNMENT] Deepgram transcription failed")
            return {
                "aligned_transcript": [],
                "deepgram_transcript": None,
                "source": "alignment_failed",
                "error": "Deepgram transcription failed"
            }

        dg_words = deepgram_result['results']['channels'][0]['alternatives'][0]['words']
        self.logger.info(f"✅ [DEEPGRAM] Transcribed {len(dg_words)} words")

        # Step 2: Parse text transcript into speaker segments
        self.logger.info("📝 [PARSING] Parsing text transcript into segments...")
        text_segments = self._parse_transcript_into_segments(transcript_text)
        self.logger.info(f"✅ [PARSING] Found {len(text_segments)} speaker segments")

        # Step 3: Align each text segment to Deepgram timestamps
        self.logger.info("🔗 [MATCHING] Aligning segments to timestamps...")
        aligned_segments = []

        for i, segment in enumerate(text_segments):
            self.logger.debug(f"   Segment {i+1}/{len(text_segments)}: {segment['speaker']} - {segment['text'][:50]}...")

            # Find best match in Deepgram transcript
            match_start, match_end = self._find_text_in_transcript(
                segment['text'],
                dg_words
            )

            if match_start is not None and match_end is not None:
                aligned_segments.append(AlignedSegment(
                    speaker=segment['speaker'],
                    text=segment['text'],
                    start=dg_words[match_start]['start'],
                    end=dg_words[match_end]['end'],
                    confidence=0.9
                ))
                self.logger.debug(f"      ✓ Matched at {dg_words[match_start]['start']:.1f}s - {dg_words[match_end]['end']:.1f}s")
            else:
                self.logger.warning(f"      ⚠️ Could not align segment {i+1}: {segment['speaker']}")

        self.logger.info(f"✅ [ALIGNMENT] Successfully aligned {len(aligned_segments)}/{len(text_segments)} segments")

        return {
            "aligned_transcript": [
                {
                    "speaker": seg.speaker,
                    "text": seg.text,
                    "start": seg.start,
                    "end": seg.end,
                    "confidence": seg.confidence
                }
                for seg in aligned_segments
            ],
            "deepgram_transcript": deepgram_result,
            "source": "aligned_with_deepgram"
        }

    async def _transcribe_with_deepgram(self, audio_url: str) -> Optional[Dict]:
        """
        Transcribe audio using Deepgram with word-level timestamps

        Args:
            audio_url: URL to audio file

        Returns:
            Deepgram API response with word-level timestamps
        """
        try:
            from deepgram import Deepgram
        except ImportError:
            self.logger.error("❌ [DEEPGRAM] deepgram-sdk not installed. Install: pip install deepgram-sdk")
            return None

        if not self.deepgram_api_key:
            self.logger.error("❌ [DEEPGRAM] DEEPGRAM_API_KEY not set")
            return None

        try:
            # Initialize Deepgram client (v2 API)
            deepgram = Deepgram(self.deepgram_api_key)

            # Configure options for best alignment
            options = {
                "model": "nova-2",        # Best accuracy
                "smart_format": True,     # Better formatting
                "punctuate": True,        # Add punctuation
                "diarize": True,          # Speaker diarization
                "utterances": True,       # Group into sentences
                "language": "en"
            }

            # Transcribe URL (v2 API uses async directly)
            self.logger.info(f"   Sending request to Deepgram...")
            response = await deepgram.transcription.prerecorded(
                {"url": audio_url},
                options
            )

            # Response is already a dict in v2
            result = response

            # Log some stats
            if result and 'results' in result:
                channels = result['results'].get('channels', [])
                if channels:
                    words = channels[0]['alternatives'][0].get('words', [])
                    self.logger.info(f"   ✅ Transcription complete: {len(words)} words")

                    # Calculate duration
                    if words:
                        duration = words[-1]['end']
                        self.logger.info(f"   Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")

            return result

        except Exception as e:
            self.logger.error(f"❌ [DEEPGRAM] Transcription error: {e}")
            return None

    def _parse_transcript_into_segments(self, transcript_text: str) -> List[Dict]:
        """
        Parse transcript text into speaker segments

        Handles common formats:
        - Seeking Alpha: "Speaker Name - Title\nText content"
        - Generic: "Speaker:\nText content"
        - Mixed formats

        Args:
            transcript_text: Raw transcript text

        Returns:
            List of {"speaker": str, "text": str} dicts
        """
        segments = []
        current_speaker = None
        current_text = []

        lines = transcript_text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a speaker line
            if self._is_speaker_line(line):
                # Save previous segment
                if current_speaker and current_text:
                    segments.append({
                        "speaker": current_speaker,
                        "text": ' '.join(current_text).strip()
                    })

                # Start new segment
                current_speaker = self._clean_speaker_name(line)
                current_text = []
            else:
                # Accumulate text for current speaker
                current_text.append(line)

        # Add final segment
        if current_speaker and current_text:
            segments.append({
                "speaker": current_speaker,
                "text": ' '.join(current_text).strip()
            })

        return segments

    def _is_speaker_line(self, line: str) -> bool:
        """
        Detect if a line is a speaker name/label

        Patterns:
        - "John Doe - CEO" (Seeking Alpha format)
        - "CEO:" or "CFO:"
        - "OPERATOR" (all caps)
        - "Analyst - Goldman Sachs"
        """
        # Pattern 1: All caps (OPERATOR, EXECUTIVE, etc.)
        if line.isupper() and len(line.split()) <= 3:
            return True

        # Pattern 2: Contains " - " with short text (name - title)
        if ' - ' in line and len(line.split()) <= 8:
            return True

        # Pattern 3: Ends with colon (Speaker:)
        if line.endswith(':') and len(line.split()) <= 5:
            return True

        # Pattern 4: Common speaker labels
        common_speakers = ['operator', 'analyst', 'executive', 'ceo', 'cfo', 'coo']
        if any(speaker in line.lower() for speaker in common_speakers) and len(line.split()) <= 6:
            return True

        return False

    def _clean_speaker_name(self, speaker_line: str) -> str:
        """Clean up speaker name by removing trailing colons, etc."""
        # Remove trailing colon
        cleaned = speaker_line.rstrip(':').strip()

        # If format is "Name - Title", keep it as is (informative)
        # If all caps, convert to title case
        if cleaned.isupper():
            cleaned = cleaned.title()

        return cleaned

    def _find_text_in_transcript(
        self,
        target_text: str,
        dg_words: List[Dict]
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Find target text in Deepgram word list using fuzzy matching

        Args:
            target_text: Text to find (from parsed transcript)
            dg_words: List of word dicts from Deepgram (each has 'word', 'start', 'end')

        Returns:
            (start_word_index, end_word_index) or (None, None) if not found
        """
        # Normalize target text to words
        target_words = self._normalize_text_to_words(target_text)

        if not target_words or not dg_words:
            return None, None

        # Build list of normalized Deepgram words
        dg_normalized = [self._normalize_word(w['word']) for w in dg_words]

        # Use sliding window to find best match
        best_match_score = 0
        best_match_start = None
        best_match_end = None

        window_size = len(target_words)

        # Don't search if target is too long
        if window_size > len(dg_normalized):
            # Try to find partial match with first N words
            window_size = min(50, len(dg_normalized))
            target_words = target_words[:window_size]

        for i in range(len(dg_normalized) - window_size + 1):
            window = dg_normalized[i:i + window_size]

            # Calculate similarity using SequenceMatcher
            similarity = SequenceMatcher(None, target_words, window).ratio()

            if similarity > best_match_score:
                best_match_score = similarity
                best_match_start = i
                best_match_end = i + window_size - 1

        # Only return if match is good enough (>75% similarity)
        if best_match_score > 0.75:
            return best_match_start, best_match_end

        return None, None

    def _normalize_text_to_words(self, text: str) -> List[str]:
        """Normalize text to list of lowercase words (remove punctuation)"""
        # Remove punctuation, lowercase, split into words
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    def _normalize_word(self, word: str) -> str:
        """Normalize a single word (lowercase, remove punctuation)"""
        return re.sub(r'[^\w]', '', word.lower())


# =============================================================================
# Formatting Utilities
# =============================================================================

def format_aligned_transcript_for_claude(aligned_data: Dict) -> str:
    """
    Format aligned transcript for Claude analysis

    Output format:
    [00:45] CEO: We delivered record revenue of $52.3 billion...
    [02:30] CFO: Our operating margins expanded to 28%...

    Args:
        aligned_data: Result from TranscriptAligner.align_transcript()

    Returns:
        Formatted string with timestamps
    """
    if not aligned_data or 'aligned_transcript' not in aligned_data:
        return ""

    formatted_lines = []

    for segment in aligned_data['aligned_transcript']:
        timestamp = format_timestamp(segment['start'])
        speaker = segment['speaker']
        text = segment['text']

        formatted_lines.append(f"[{timestamp}] {speaker}: {text}")

    return '\n\n'.join(formatted_lines)


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to MM:SS or HH:MM:SS format

    Args:
        seconds: Time in seconds (e.g., 125.5)

    Returns:
        Formatted timestamp (e.g., "02:05" or "1:23:45")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def extract_text_from_aligned(aligned_data: Dict) -> str:
    """
    Extract plain text from aligned transcript (no timestamps)

    Useful as fallback when you need just the text content.

    Args:
        aligned_data: Result from TranscriptAligner.align_transcript()

    Returns:
        Plain text with speaker labels
    """
    if not aligned_data or 'aligned_transcript' not in aligned_data:
        return ""

    lines = []

    for segment in aligned_data['aligned_transcript']:
        lines.append(f"{segment['speaker']}")
        lines.append(segment['text'])
        lines.append("")  # Blank line between segments

    return '\n'.join(lines)
