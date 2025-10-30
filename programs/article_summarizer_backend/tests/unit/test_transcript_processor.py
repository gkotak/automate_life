"""
Tests for processors/transcript_processor.py

Tests YouTube transcript extraction with mocked API responses.
All external dependencies (YouTube Transcript API) are mocked.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import requests

from processors.transcript_processor import TranscriptProcessor


@pytest.fixture
def mock_session():
    """Mock requests session"""
    session = Mock(spec=requests.Session)
    return session


@pytest.fixture
def processor(tmp_path, mock_session):
    """Create TranscriptProcessor instance with temp directory"""
    return TranscriptProcessor(base_dir=tmp_path, session=mock_session)


@pytest.fixture
def sample_transcript_entries():
    """Sample transcript entries returned by YouTube API"""
    # Mock transcript entry objects
    entries = []
    for i, text in enumerate([
        "Welcome to this video about Python testing",
        "Today we'll learn about pytest and mocking",
        "Let's start with a simple example"
    ]):
        entry = MagicMock()
        entry.start = float(i * 5)
        entry.text = text
        entry.duration = 5.0
        entries.append(entry)
    return entries


class TestTranscriptProcessorInitialization:
    """Tests for TranscriptProcessor initialization"""

    @pytest.mark.unit
    def test_initializes_with_base_dir(self, tmp_path, mock_session):
        """Should initialize with base directory and session"""
        processor = TranscriptProcessor(base_dir=tmp_path, session=mock_session)

        assert processor.base_dir == tmp_path
        assert processor.session == mock_session
        assert processor.logger is not None

    @pytest.mark.unit
    def test_creates_logger_with_class_name(self, processor):
        """Should create logger with proper naming"""
        assert "TranscriptProcessor" in processor.logger.name


class TestGetYoutubeTranscript:
    """Tests for get_youtube_transcript() method"""

    @pytest.mark.unit
    def test_extracts_manual_transcript(self, processor, sample_transcript_entries):
        """Should extract manually created transcript when available"""
        with patch('youtube_transcript_api.YouTubeTranscriptApi') as mock_ytt_api:
            # Setup mock API
            mock_api_instance = MagicMock()
            mock_ytt_api.return_value = mock_api_instance

            # Mock transcript list
            mock_transcript_list = MagicMock()
            mock_api_instance.list.return_value = mock_transcript_list

            # Mock manual transcript
            mock_manual_transcript = MagicMock()
            mock_manual_transcript.fetch.return_value = sample_transcript_entries
            mock_transcript_list.find_manually_created_transcript.return_value = mock_manual_transcript

            # Test
            result = processor.get_youtube_transcript('dQw4w9WgXcQ')

            # Verify
            assert result['success'] is True
            assert result['type'] == 'manual'
            assert result['video_id'] == 'dQw4w9WgXcQ'
            assert result['total_entries'] == 3
            assert len(result['transcript']) == 3
            assert result['transcript'][0]['text'] == "Welcome to this video about Python testing"
            assert result['transcript'][0]['start'] == 0.0
            assert result['transcript'][0]['duration'] == 5.0

    @pytest.mark.unit
    def test_falls_back_to_auto_generated(self, processor, sample_transcript_entries):
        """Should fall back to auto-generated transcript if manual not available"""
        with patch('youtube_transcript_api.YouTubeTranscriptApi') as mock_ytt_api:
            # Setup mock API
            mock_api_instance = MagicMock()
            mock_ytt_api.return_value = mock_api_instance

            # Mock transcript list
            mock_transcript_list = MagicMock()
            mock_api_instance.list.return_value = mock_transcript_list

            # Manual transcript not available
            mock_transcript_list.find_manually_created_transcript.side_effect = Exception("No manual transcript")

            # Mock auto-generated transcript
            mock_auto_transcript = MagicMock()
            mock_auto_transcript.fetch.return_value = sample_transcript_entries
            mock_transcript_list.find_generated_transcript.return_value = mock_auto_transcript

            # Test
            result = processor.get_youtube_transcript('test_video_id')

            # Verify
            assert result['success'] is True
            assert result['type'] == 'auto_generated'
            assert result['video_id'] == 'test_video_id'
            assert result['total_entries'] == 3

    @pytest.mark.unit
    def test_handles_no_transcript_available(self, processor):
        """Should return error when no transcript is available"""
        with patch('youtube_transcript_api.YouTubeTranscriptApi') as mock_ytt_api:
            # Setup mock API
            mock_api_instance = MagicMock()
            mock_ytt_api.return_value = mock_api_instance

            # Mock transcript list
            mock_transcript_list = MagicMock()
            mock_api_instance.list.return_value = mock_transcript_list

            # Both manual and auto-generated fail
            mock_transcript_list.find_manually_created_transcript.side_effect = Exception("No manual")
            mock_transcript_list.find_generated_transcript.side_effect = Exception("No auto")

            # Test
            result = processor.get_youtube_transcript('no_transcript_video')

            # Verify
            assert result['success'] is False
            assert result['error'] == 'No English transcript available'
            assert result['video_id'] == 'no_transcript_video'

    @pytest.mark.unit
    def test_handles_missing_library(self, processor):
        """Should return error when youtube-transcript-api is not installed"""
        # Patch the import at the point it's used (inside the try block)
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'youtube_transcript_api':
                raise ImportError("No module named 'youtube_transcript_api'")
            return real_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            result = processor.get_youtube_transcript('test_video')

            assert result['success'] is False
            assert 'not installed' in result['error']
            assert result['video_id'] == 'test_video'

    @pytest.mark.unit
    def test_handles_api_exception(self, processor):
        """Should handle exceptions from YouTube API gracefully"""
        with patch('youtube_transcript_api.YouTubeTranscriptApi') as mock_ytt_api:
            # Setup mock to raise exception
            mock_ytt_api.return_value.list.side_effect = Exception("API rate limit exceeded")

            # Test
            result = processor.get_youtube_transcript('test_video')

            # Verify
            assert result['success'] is False
            assert 'API rate limit exceeded' in result['error']
            assert result['video_id'] == 'test_video'

    @pytest.mark.unit
    def test_handles_entry_without_duration(self, processor):
        """Should handle transcript entries without duration field"""
        with patch('youtube_transcript_api.YouTubeTranscriptApi') as mock_ytt_api:
            # Setup mock API
            mock_api_instance = MagicMock()
            mock_ytt_api.return_value = mock_api_instance

            # Mock transcript list
            mock_transcript_list = MagicMock()
            mock_api_instance.list.return_value = mock_transcript_list

            # Mock transcript entry without duration
            entry = MagicMock()
            entry.start = 0.0
            entry.text = "Test text"
            # Simulate missing duration attribute
            del entry.duration

            mock_manual_transcript = MagicMock()
            mock_manual_transcript.fetch.return_value = [entry]
            mock_transcript_list.find_manually_created_transcript.return_value = mock_manual_transcript

            # Test
            result = processor.get_youtube_transcript('test_video')

            # Verify - should default to 0 duration
            assert result['success'] is True
            assert result['transcript'][0]['duration'] == 0

    @pytest.mark.unit
    def test_processes_long_transcript(self, processor):
        """Should handle transcripts with many entries"""
        with patch('youtube_transcript_api.YouTubeTranscriptApi') as mock_ytt_api:
            # Setup mock API
            mock_api_instance = MagicMock()
            mock_ytt_api.return_value = mock_api_instance

            # Create 100 transcript entries
            entries = []
            for i in range(100):
                entry = MagicMock()
                entry.start = float(i * 2)
                entry.text = f"Segment {i}"
                entry.duration = 2.0
                entries.append(entry)

            mock_transcript_list = MagicMock()
            mock_api_instance.list.return_value = mock_transcript_list

            mock_manual_transcript = MagicMock()
            mock_manual_transcript.fetch.return_value = entries
            mock_transcript_list.find_manually_created_transcript.return_value = mock_manual_transcript

            # Test
            result = processor.get_youtube_transcript('long_video')

            # Verify
            assert result['success'] is True
            assert result['total_entries'] == 100
            assert len(result['transcript']) == 100
            assert result['transcript'][50]['text'] == "Segment 50"
            assert result['transcript'][50]['start'] == 100.0

    @pytest.mark.unit
    def test_serializes_transcript_data_correctly(self, processor, sample_transcript_entries):
        """Should convert transcript entries to serializable dictionaries"""
        with patch('youtube_transcript_api.YouTubeTranscriptApi') as mock_ytt_api:
            # Setup mock API
            mock_api_instance = MagicMock()
            mock_ytt_api.return_value = mock_api_instance

            mock_transcript_list = MagicMock()
            mock_api_instance.list.return_value = mock_transcript_list

            mock_manual_transcript = MagicMock()
            mock_manual_transcript.fetch.return_value = sample_transcript_entries
            mock_transcript_list.find_manually_created_transcript.return_value = mock_manual_transcript

            # Test
            result = processor.get_youtube_transcript('test_video')

            # Verify all entries are plain dictionaries (not MagicMock objects)
            assert isinstance(result['transcript'], list)
            for entry in result['transcript']:
                assert isinstance(entry, dict)
                assert 'start' in entry
                assert 'text' in entry
                assert 'duration' in entry
                assert isinstance(entry['start'], float)
                assert isinstance(entry['text'], str)
                assert isinstance(entry['duration'], float)
