"""
Unit tests for core/url_utils.py

Tests URL normalization, ID generation, and URL comparison utilities.
"""

import pytest
from core.url_utils import normalize_url, generate_post_id, is_same_base_url


class TestNormalizeUrl:
    """Tests for normalize_url() function"""

    @pytest.mark.unit
    def test_removes_query_parameters(self):
        """Should remove query parameters from URL"""
        url = "https://example.com/article?token=abc123&utm_source=email"
        result = normalize_url(url)
        assert result == "https://example.com/article"

    @pytest.mark.unit
    def test_removes_fragment(self):
        """Should remove fragment identifier from URL"""
        url = "https://example.com/article#section-2"
        result = normalize_url(url)
        assert result == "https://example.com/article"

    @pytest.mark.unit
    def test_removes_both_query_and_fragment(self):
        """Should remove both query parameters and fragment"""
        url = "https://example.com/article?token=abc#section-1"
        result = normalize_url(url)
        assert result == "https://example.com/article"

    @pytest.mark.unit
    def test_preserves_trailing_slash(self):
        """Should preserve trailing slash in path"""
        url = "https://stratechery.com/2025/article/?access_token=xyz"
        result = normalize_url(url)
        assert result == "https://stratechery.com/2025/article/"

    @pytest.mark.unit
    def test_handles_url_without_parameters(self):
        """Should return unchanged URL when no parameters present"""
        url = "https://example.com/article"
        result = normalize_url(url)
        assert result == url

    @pytest.mark.unit
    def test_handles_multiple_query_parameters(self):
        """Should remove all query parameters"""
        url = "https://example.com/article?a=1&b=2&c=3&d=4"
        result = normalize_url(url)
        assert result == "https://example.com/article"

    @pytest.mark.unit
    def test_handles_substack_urls(self, sample_urls):
        """Should normalize Substack URLs correctly"""
        url = f"{sample_urls['substack']}?utm_source=email"
        result = normalize_url(url)
        assert result == sample_urls['substack']

    @pytest.mark.unit
    def test_handles_youtube_urls(self, sample_urls):
        """Should normalize YouTube URLs correctly"""
        # YouTube URLs have query params, normalize removes them
        url = f"{sample_urls['youtube']}&t=30s"
        result = normalize_url(url)
        # Should remove all query params including v=
        assert result == "https://www.youtube.com/watch"

    @pytest.mark.unit
    def test_handles_malformed_url(self):
        """Should return original URL if parsing fails"""
        malformed_url = "not a valid url at all"
        result = normalize_url(malformed_url)
        # Should return original since parsing fails
        assert result == malformed_url

    @pytest.mark.unit
    def test_handles_empty_string(self):
        """Should handle empty string gracefully"""
        result = normalize_url("")
        assert result == ""

    @pytest.mark.unit
    def test_handles_url_with_port(self):
        """Should preserve port number"""
        url = "https://example.com:8080/article?param=value"
        result = normalize_url(url)
        assert result == "https://example.com:8080/article"

    @pytest.mark.unit
    def test_handles_http_protocol(self):
        """Should work with HTTP (not HTTPS)"""
        url = "http://example.com/article?token=123"
        result = normalize_url(url)
        assert result == "http://example.com/article"


class TestGeneratePostId:
    """Tests for generate_post_id() function"""

    @pytest.mark.unit
    def test_generates_consistent_id(self):
        """Should generate same ID for same title and URL"""
        title = "Test Article"
        url = "https://example.com/article"

        id1 = generate_post_id(title, url)
        id2 = generate_post_id(title, url)

        assert id1 == id2

    @pytest.mark.unit
    def test_generates_different_ids_for_different_titles(self):
        """Should generate different IDs for different titles"""
        url = "https://example.com/article"

        id1 = generate_post_id("Title 1", url)
        id2 = generate_post_id("Title 2", url)

        assert id1 != id2

    @pytest.mark.unit
    def test_generates_different_ids_for_different_urls(self):
        """Should generate different IDs for different URLs"""
        title = "Test Article"

        id1 = generate_post_id(title, "https://example.com/article1")
        id2 = generate_post_id(title, "https://example.com/article2")

        assert id1 != id2

    @pytest.mark.unit
    def test_normalizes_url_before_generating_id(self):
        """Should generate same ID regardless of query parameters"""
        title = "Test Article"
        url1 = "https://example.com/article?token=123"
        url2 = "https://example.com/article?token=456"

        id1 = generate_post_id(title, url1)
        id2 = generate_post_id(title, url2)

        assert id1 == id2

    @pytest.mark.unit
    def test_generates_md5_hash(self):
        """Should generate valid MD5 hash (32 hex characters)"""
        title = "Test Article"
        url = "https://example.com/article"

        result = generate_post_id(title, url)

        assert len(result) == 32
        assert all(c in '0123456789abcdef' for c in result)

    @pytest.mark.unit
    def test_handles_unicode_in_title(self):
        """Should handle Unicode characters in title"""
        title = "Test Article with émojis 🚀"
        url = "https://example.com/article"

        result = generate_post_id(title, url)

        assert len(result) == 32  # Valid MD5 hash

    @pytest.mark.unit
    def test_handles_special_characters(self):
        """Should handle special characters in title"""
        title = "Test: Article — Part [1] (2024)"
        url = "https://example.com/article"

        result = generate_post_id(title, url)

        assert len(result) == 32

    @pytest.mark.unit
    def test_case_sensitive_titles(self):
        """Should treat uppercase and lowercase titles differently"""
        url = "https://example.com/article"

        id1 = generate_post_id("TEST ARTICLE", url)
        id2 = generate_post_id("test article", url)

        assert id1 != id2


class TestIsSameBaseUrl:
    """Tests for is_same_base_url() function"""

    @pytest.mark.unit
    def test_returns_true_for_same_url(self):
        """Should return True for identical URLs"""
        url = "https://example.com/article"
        assert is_same_base_url(url, url) is True

    @pytest.mark.unit
    def test_returns_true_for_urls_with_different_params(self):
        """Should return True when only query params differ"""
        url1 = "https://example.com/article?token=123"
        url2 = "https://example.com/article?token=456"
        assert is_same_base_url(url1, url2) is True

    @pytest.mark.unit
    def test_returns_true_for_urls_with_different_fragments(self):
        """Should return True when only fragments differ"""
        url1 = "https://example.com/article#section-1"
        url2 = "https://example.com/article#section-2"
        assert is_same_base_url(url1, url2) is True

    @pytest.mark.unit
    def test_returns_false_for_different_domains(self):
        """Should return False for different domains"""
        url1 = "https://example.com/article"
        url2 = "https://different.com/article"
        assert is_same_base_url(url1, url2) is False

    @pytest.mark.unit
    def test_returns_false_for_different_paths(self):
        """Should return False for different paths"""
        url1 = "https://example.com/article1"
        url2 = "https://example.com/article2"
        assert is_same_base_url(url1, url2) is False

    @pytest.mark.unit
    def test_returns_false_for_different_protocols(self):
        """Should return False for different protocols"""
        url1 = "http://example.com/article"
        url2 = "https://example.com/article"
        assert is_same_base_url(url1, url2) is False

    @pytest.mark.unit
    def test_handles_trailing_slash_difference(self):
        """Should treat URLs with/without trailing slash as different"""
        url1 = "https://example.com/article"
        url2 = "https://example.com/article/"
        # URLs are technically different
        assert is_same_base_url(url1, url2) is False

    @pytest.mark.unit
    def test_handles_youtube_urls(self, sample_urls):
        """Should correctly compare YouTube URLs"""
        url1 = f"{sample_urls['youtube']}&t=30s"
        url2 = f"{sample_urls['youtube']}&feature=share"
        assert is_same_base_url(url1, url2) is True

    @pytest.mark.unit
    def test_handles_substack_urls(self, sample_urls):
        """Should correctly compare Substack URLs"""
        url1 = f"{sample_urls['substack']}?utm_source=email"
        url2 = f"{sample_urls['substack']}?utm_source=twitter"
        assert is_same_base_url(url1, url2) is True

    @pytest.mark.unit
    def test_handles_malformed_urls(self):
        """Should handle comparison of malformed URLs"""
        url1 = "not a url"
        url2 = "also not a url"
        # Different malformed URLs should not be considered the same
        assert is_same_base_url(url1, url2) is False
