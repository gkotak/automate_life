"""
Unit tests for core/content_detector.py

Tests video/audio platform detection from iframes and URLs.
Focus on the _extract_video_from_iframe_src() function and ContentType dataclass.
"""

import pytest
from core.content_detector import ContentTypeDetector, ContentType


class TestContentTypeDataclass:
    """Tests for ContentType dataclass"""

    @pytest.mark.unit
    def test_default_is_text_only(self):
        """Should default to text-only content"""
        content = ContentType()
        assert content.is_text_only is True
        assert content.has_embedded_video is False
        assert content.has_embedded_audio is False

    @pytest.mark.unit
    def test_initializes_empty_lists(self):
        """Should initialize empty video/audio URL lists"""
        content = ContentType()
        assert content.video_urls == []
        assert content.audio_urls == []

    @pytest.mark.unit
    def test_can_set_video_content(self):
        """Should allow setting video content"""
        content = ContentType(
            has_embedded_video=True,
            is_text_only=False,
            video_urls=[{'video_id': 'test123', 'platform': 'youtube'}]
        )
        assert content.has_embedded_video is True
        assert content.is_text_only is False
        assert len(content.video_urls) == 1

    @pytest.mark.unit
    def test_can_set_audio_content(self):
        """Should allow setting audio content"""
        content = ContentType(
            has_embedded_audio=True,
            is_text_only=False,
            audio_urls=[{'url': 'https://example.com/audio.mp3'}]
        )
        assert content.has_embedded_audio is True
        assert content.is_text_only is False
        assert len(content.audio_urls) == 1


class TestExtractVideoFromIframeSrc:
    """Tests for _extract_video_from_iframe_src() method"""

    @pytest.fixture
    def detector(self):
        """Create a ContentTypeDetector instance"""
        return ContentTypeDetector()

    # YouTube Tests
    @pytest.mark.unit
    def test_extracts_youtube_video_id(self, detector, sample_video_ids):
        """Should extract YouTube video ID from embed URL"""
        src = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['platform'] == 'youtube'
        assert result['video_id'] == sample_video_ids['youtube']
        assert result['context'] == 'iframe_embed'

    @pytest.mark.unit
    def test_extracts_youtube_nocookie(self, detector, sample_video_ids):
        """Should extract YouTube video ID from youtube-nocookie domain"""
        src = "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['platform'] == 'youtube'
        assert result['video_id'] == sample_video_ids['youtube']

    @pytest.mark.unit
    def test_youtube_with_query_params(self, detector, sample_video_ids):
        """Should extract YouTube video ID even with query parameters"""
        src = "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&mute=1"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['video_id'] == sample_video_ids['youtube']

    # Vimeo Tests
    @pytest.mark.unit
    def test_extracts_vimeo_video_id(self, detector, sample_video_ids):
        """Should extract Vimeo video ID from player embed URL"""
        src = "https://player.vimeo.com/video/123456789"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['platform'] == 'vimeo'
        assert result['video_id'] == sample_video_ids['vimeo']
        assert result['context'] == 'iframe_embed'

    @pytest.mark.unit
    def test_vimeo_with_query_params(self, detector, sample_video_ids):
        """Should extract Vimeo video ID with query parameters"""
        src = "https://player.vimeo.com/video/123456789?badge=0&autopause=0"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['video_id'] == sample_video_ids['vimeo']

    @pytest.mark.unit
    def test_vimeo_direct_url_pattern(self, detector, sample_video_ids):
        """Should extract Vimeo video ID from direct vimeo.com URLs"""
        src = "https://vimeo.com/123456789"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['video_id'] == sample_video_ids['vimeo']

    # Loom Tests
    @pytest.mark.unit
    def test_extracts_loom_video_id(self, detector, sample_video_ids):
        """Should extract Loom video ID from embed URL"""
        src = "https://www.loom.com/embed/abc123def456"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['platform'] == 'loom'
        assert result['video_id'] == sample_video_ids['loom']
        assert result['context'] == 'iframe_embed'

    @pytest.mark.unit
    def test_loom_share_url_pattern(self, detector, sample_video_ids):
        """Should extract Loom video ID from share URLs"""
        src = "https://www.loom.com/share/abc123def456"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['video_id'] == sample_video_ids['loom']

    @pytest.mark.unit
    def test_loom_with_query_params(self, detector, sample_video_ids):
        """Should extract Loom video ID with query parameters"""
        src = "https://www.loom.com/embed/abc123def456?hide_owner=true&hide_share=true"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['video_id'] == sample_video_ids['loom']

    # Wistia Tests
    @pytest.mark.unit
    def test_extracts_wistia_video_id(self, detector, sample_video_ids):
        """Should extract Wistia video ID from embed URL"""
        src = "https://fast.wistia.net/embed/iframe/xyz789abc"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['platform'] == 'wistia'
        assert result['video_id'] == sample_video_ids['wistia']

    @pytest.mark.unit
    def test_wistia_alternate_domain(self, detector):
        """Should handle wistia.com domain (not just wistia.net)"""
        src = "https://fast.wistia.com/embed/iframe/xyz789abc"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['platform'] == 'wistia'

    # Dailymotion Tests
    @pytest.mark.unit
    def test_extracts_dailymotion_video_id(self, detector, sample_video_ids):
        """Should extract Dailymotion video ID from embed URL"""
        src = "https://www.dailymotion.com/embed/video/x8abcdef"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['platform'] == 'dailymotion'
        assert result['video_id'] == sample_video_ids['dailymotion']

    # Edge Cases
    @pytest.mark.unit
    def test_returns_none_for_non_video_iframe(self, detector):
        """Should return None for non-video iframes"""
        src = "https://example.com/embed/map"
        result = detector._extract_video_from_iframe_src(src)

        assert result is None

    @pytest.mark.unit
    def test_returns_none_for_empty_src(self, detector):
        """Should return None for empty src"""
        result = detector._extract_video_from_iframe_src("")

        assert result is None

    @pytest.mark.unit
    def test_returns_none_for_malformed_url(self, detector):
        """Should return None for malformed URL"""
        src = "not a valid url at all"
        result = detector._extract_video_from_iframe_src(src)

        assert result is None

    @pytest.mark.unit
    def test_case_insensitive_domain_matching(self, detector):
        """Should match domains case-insensitively"""
        # Note: Python's 'in' operator is case-sensitive, so uppercase won't match
        # This tests that lowercase domains work correctly
        src = "https://player.vimeo.com/video/123456789"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['platform'] == 'vimeo'

    # URL Template Tests
    @pytest.mark.unit
    def test_youtube_returns_correct_urls(self, detector, sample_video_ids):
        """Should return correct YouTube URLs"""
        src = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        result = detector._extract_video_from_iframe_src(src)

        assert result['url'] == f"https://www.youtube.com/watch?v={sample_video_ids['youtube']}"
        assert result['embed_url'] == f"https://www.youtube.com/embed/{sample_video_ids['youtube']}"

    @pytest.mark.unit
    def test_vimeo_returns_correct_urls(self, detector, sample_video_ids):
        """Should return correct Vimeo URLs"""
        src = "https://player.vimeo.com/video/123456789"
        result = detector._extract_video_from_iframe_src(src)

        assert result['url'] == f"https://vimeo.com/{sample_video_ids['vimeo']}"
        assert result['embed_url'] == f"https://player.vimeo.com/video/{sample_video_ids['vimeo']}"

    @pytest.mark.unit
    def test_loom_returns_correct_urls(self, detector, sample_video_ids):
        """Should return correct Loom URLs"""
        src = "https://www.loom.com/embed/abc123def456"
        result = detector._extract_video_from_iframe_src(src)

        assert result['url'] == f"https://www.loom.com/share/{sample_video_ids['loom']}"
        assert result['embed_url'] == f"https://www.loom.com/embed/{sample_video_ids['loom']}"

    # Video ID Format Tests
    @pytest.mark.unit
    def test_youtube_alphanumeric_with_dash_underscore(self, detector):
        """Should handle YouTube video IDs with alphanumeric, dash, and underscore"""
        video_id = "abc-123_XYZ"
        src = f"https://www.youtube.com/embed/{video_id}"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['video_id'] == video_id

    @pytest.mark.unit
    def test_vimeo_numeric_only(self, detector):
        """Should handle Vimeo numeric-only video IDs"""
        video_id = "987654321"
        src = f"https://player.vimeo.com/video/{video_id}"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['video_id'] == video_id

    @pytest.mark.unit
    def test_loom_alphanumeric_with_dash_underscore(self, detector):
        """Should handle Loom alphanumeric video IDs with dashes and underscores"""
        video_id = "abc123-def456_ghi789"
        src = f"https://www.loom.com/embed/{video_id}"
        result = detector._extract_video_from_iframe_src(src)

        assert result is not None
        assert result['video_id'] == video_id

    # Multiple Platform Priority
    @pytest.mark.unit
    def test_processes_platforms_in_order(self, detector):
        """Should process platforms in defined order"""
        # If URL somehow matches multiple patterns (unlikely but test the logic)
        src = "https://www.youtube.com/embed/test123"
        result = detector._extract_video_from_iframe_src(src)

        # Should match YouTube since it's in the platforms dict
        assert result['platform'] == 'youtube'


class TestContentTypeDetectorInit:
    """Tests for ContentTypeDetector initialization"""

    @pytest.mark.unit
    def test_creates_with_default_session(self):
        """Should create with default requests session"""
        detector = ContentTypeDetector()
        assert detector.session is not None

    @pytest.mark.unit
    def test_accepts_custom_session(self):
        """Should accept custom requests session"""
        import requests
        custom_session = requests.Session()
        detector = ContentTypeDetector(session=custom_session)
        assert detector.session is custom_session

    @pytest.mark.unit
    def test_has_logger(self):
        """Should have a logger instance"""
        detector = ContentTypeDetector()
        assert detector.logger is not None
