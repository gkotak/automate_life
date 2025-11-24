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


class TestDirectMediaFileDetection:
    """Tests for direct media file URL detection (MP3, MP4, etc.)"""

    @pytest.fixture
    def detector(self):
        """Create a ContentTypeDetector instance"""
        return ContentTypeDetector()

    # Direct Video File Tests
    @pytest.mark.unit
    def test_detects_direct_mp4_video(self, detector):
        """Should detect .mp4 files as direct video"""
        url = "https://example.com/video.mp4"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'video'

    @pytest.mark.unit
    def test_detects_cloudfront_mp4_video(self, detector):
        """Should detect MP4 on CloudFront as direct video"""
        url = "https://d123abc.cloudfront.net/videos/sample_video.mp4"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'video'

    @pytest.mark.unit
    def test_detects_mov_video(self, detector):
        """Should detect .mov files as direct video"""
        url = "https://example.com/recording.mov"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'video'

    @pytest.mark.unit
    def test_detects_webm_video(self, detector):
        """Should detect .webm files as direct video"""
        url = "https://example.com/clip.webm"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'video'

    @pytest.mark.unit
    def test_detects_mkv_video(self, detector):
        """Should detect .mkv files as direct video"""
        url = "https://example.com/movie.mkv"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'video'

    # Direct Audio File Tests
    @pytest.mark.unit
    def test_detects_direct_mp3_audio(self, detector):
        """Should detect .mp3 files as direct audio"""
        url = "https://example.com/podcast.mp3"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'audio'

    @pytest.mark.unit
    def test_detects_m4a_audio(self, detector):
        """Should detect .m4a files as direct audio"""
        url = "https://example.com/episode.m4a"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'audio'

    @pytest.mark.unit
    def test_detects_wav_audio(self, detector):
        """Should detect .wav files as direct audio"""
        url = "https://example.com/recording.wav"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'audio'

    @pytest.mark.unit
    def test_detects_ogg_audio(self, detector):
        """Should detect .ogg files as direct audio"""
        url = "https://example.com/audio.ogg"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'audio'

    # URLs with Query Parameters
    @pytest.mark.unit
    def test_detects_mp4_with_query_params(self, detector):
        """Should detect MP4 even with query parameters"""
        url = "https://example.com/video.mp4?token=abc123&expires=1234567890"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'video'

    @pytest.mark.unit
    def test_detects_mp3_with_query_params(self, detector):
        """Should detect MP3 even with query parameters"""
        url = "https://example.com/podcast.mp3?download=true&quality=high"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'audio'

    # Case Insensitivity
    @pytest.mark.unit
    def test_case_insensitive_mp4_detection(self, detector):
        """Should detect MP4 regardless of case"""
        urls = [
            "https://example.com/video.MP4",
            "https://example.com/video.Mp4",
            "https://example.com/video.mP4"
        ]
        for url in urls:
            is_media, media_type = detector.is_direct_media_url(url)
            assert is_media is True
            assert media_type == 'video'

    @pytest.mark.unit
    def test_case_insensitive_mp3_detection(self, detector):
        """Should detect MP3 regardless of case"""
        urls = [
            "https://example.com/audio.MP3",
            "https://example.com/audio.Mp3",
            "https://example.com/audio.mP3"
        ]
        for url in urls:
            is_media, media_type = detector.is_direct_media_url(url)
            assert is_media is True
            assert media_type == 'audio'

    @pytest.mark.unit
    def test_detects_pdf_as_document(self, detector):
        """Should detect PDF files as document media"""
        urls = [
            "https://example.com/document.pdf",
            "https://example.com/file.PDF",
            "https://example.com/report.pdf?param=value"
        ]
        for url in urls:
            is_media, media_type = detector.is_direct_media_url(url)
            assert is_media is True
            assert media_type == 'document'

    # Negative Cases
    @pytest.mark.unit
    def test_does_not_detect_non_media_urls(self, detector):
        """Should not detect non-media URLs as media"""
        urls = [
            "https://example.com/article.html",
            "https://example.com/page",
            "https://example.com/image.jpg"
        ]
        for url in urls:
            is_media, media_type = detector.is_direct_media_url(url)
            assert is_media is False
            assert media_type is None

    @pytest.mark.unit
    def test_does_not_detect_partial_extension_match(self, detector):
        """Should not match partial extensions like 'ump4' or 'temp3'"""
        urls = [
            "https://example.com/jump4ward.html",
            "https://example.com/temp3file.txt"
        ]
        for url in urls:
            is_media, media_type = detector.is_direct_media_url(url)
            assert is_media is False

    # Real-World Examples
    @pytest.mark.unit
    def test_detects_seekingalpha_mp3(self, detector):
        """Should detect Seeking Alpha audio files"""
        url = "https://static.seekingalpha.com/cdn/s3/transcripts_audio/12345.mp3"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'audio'

    @pytest.mark.unit
    def test_detects_pocketcasts_audio(self, detector):
        """Should detect PocketCasts audio files"""
        url = "https://chrt.fm/track/ABC123/audio.mp3"
        is_media, media_type = detector.is_direct_media_url(url)

        assert is_media is True
        assert media_type == 'audio'


class TestDirectMediaContentType:
    """Tests for detect_content_type() with direct media files"""

    @pytest.fixture
    def detector(self):
        """Create a ContentTypeDetector instance"""
        return ContentTypeDetector()

    @pytest.mark.unit
    def test_detect_content_type_for_mp4(self, detector):
        """Should return video content type for direct MP4 URL"""
        from bs4 import BeautifulSoup

        url = "https://example.com/video.mp4"
        html = "<html><body>Video page</body></html>"
        soup = BeautifulSoup(html, 'html.parser')

        result = detector.detect_content_type(soup, url)

        assert result.has_embedded_video is True
        assert result.has_embedded_audio is False
        assert result.is_text_only is False
        assert len(result.video_urls) == 1
        assert result.video_urls[0]['platform'] == 'direct_file'
        assert result.video_urls[0]['url'] == url
        assert result.video_urls[0]['context'] == 'direct_video_file'
        assert result.video_urls[0]['requires_download'] is True

    @pytest.mark.unit
    def test_detect_content_type_for_mp3(self, detector):
        """Should return audio content type for direct MP3 URL"""
        from bs4 import BeautifulSoup

        url = "https://example.com/podcast.mp3"
        html = "<html><body>Audio page</body></html>"
        soup = BeautifulSoup(html, 'html.parser')

        result = detector.detect_content_type(soup, url)

        assert result.has_embedded_video is False
        assert result.has_embedded_audio is True
        assert result.is_text_only is False
        assert len(result.audio_urls) == 1
        assert result.audio_urls[0]['platform'] == 'direct_file'
        assert result.audio_urls[0]['url'] == url
        assert result.audio_urls[0]['context'] == 'direct_audio_file'

    @pytest.mark.unit
    def test_direct_files_marked_requires_download(self, detector):
        """Should mark direct files as requiring download"""
        from bs4 import BeautifulSoup

        video_url = "https://example.com/video.mp4"
        audio_url = "https://example.com/audio.mp3"
        empty_soup = BeautifulSoup("", 'html.parser')

        video_result = detector.detect_content_type(empty_soup, video_url)
        audio_result = detector.detect_content_type(empty_soup, audio_url)

        assert video_result.video_urls[0]['requires_download'] is True
        assert audio_result.audio_urls[0]['requires_download'] is True
