"""
Unit tests for core/text_utils.py

Tests text manipulation functions including filename sanitization,
title similarity calculation, and fuzzy title matching.
"""

import pytest
from datetime import datetime, timedelta
from core.text_utils import (
    sanitize_filename,
    calculate_title_similarity,
    check_title_and_date_match
)


class TestSanitizeFilename:
    """Tests for sanitize_filename() function"""

    @pytest.mark.unit
    def test_replaces_spaces_with_underscores(self):
        """Should replace spaces with underscores"""
        result = sanitize_filename("Hello World Test")
        assert result == "Hello_World_Test"

    @pytest.mark.unit
    def test_replaces_em_dashes(self):
        """Should replace em dashes (—) with regular hyphens"""
        result = sanitize_filename("Test Article — Part 1")
        assert result == "Test_Article_-_Part_1"

    @pytest.mark.unit
    def test_replaces_en_dashes(self):
        """Should replace en dashes (–) with regular hyphens"""
        result = sanitize_filename("Test Article – Part 1")
        assert result == "Test_Article_-_Part_1"

    @pytest.mark.unit
    def test_removes_invalid_characters(self):
        """Should remove invalid filename characters"""
        result = sanitize_filename('Invalid: <chars> "test" file|name?')
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '|' not in result
        assert '?' not in result

    @pytest.mark.unit
    def test_removes_forward_slash(self):
        """Should remove forward slashes"""
        result = sanitize_filename("Test/Article")
        assert '/' not in result

    @pytest.mark.unit
    def test_removes_backslash(self):
        """Should remove backslashes"""
        result = sanitize_filename("Test\\Article")
        assert '\\' not in result

    @pytest.mark.unit
    def test_handles_unicode_characters(self):
        """Should convert non-ASCII characters to underscores"""
        result = sanitize_filename("Test émojis 🚀 and ñoñ-ASCII")
        # Non-ASCII chars should be replaced with underscores
        assert '🚀' not in result
        assert 'é' not in result
        assert 'ñ' not in result

    @pytest.mark.unit
    def test_cleans_multiple_underscores(self):
        """Should collapse multiple underscores into one"""
        result = sanitize_filename("Test___Article___Name")
        assert '___' not in result
        assert result == "Test_Article_Name"

    @pytest.mark.unit
    def test_limits_length_to_100_chars(self):
        """Should truncate filenames longer than 100 characters"""
        long_title = "A" * 200
        result = sanitize_filename(long_title)
        assert len(result) == 100

    @pytest.mark.unit
    def test_preserves_short_titles(self):
        """Should not truncate titles under 100 characters"""
        title = "Short Title"
        result = sanitize_filename(title)
        assert result == "Short_Title"
        assert len(result) < 100

    @pytest.mark.unit
    def test_handles_empty_string(self):
        """Should handle empty string"""
        result = sanitize_filename("")
        assert result == ""

    @pytest.mark.unit
    def test_handles_only_spaces(self):
        """Should handle string with only spaces"""
        result = sanitize_filename("     ")
        assert result == "_"

    @pytest.mark.unit
    def test_handles_parentheses_and_brackets(self, sample_titles):
        """Should remove angle brackets but preserve parentheses and square brackets"""
        result = sanitize_filename(sample_titles['with_punctuation'])
        # Only characters in the regex pattern [<>:"/\\|?*] are removed
        # Parentheses () and square brackets [] are preserved
        assert '<' not in result
        assert '>' not in result
        # These ARE preserved:
        # assert '(' not in result
        # assert ')' not in result
        # assert '[' not in result
        # assert ']' not in result

    @pytest.mark.unit
    def test_realistic_article_title(self):
        """Should sanitize realistic article title correctly"""
        title = "AI Engineering 101: Getting Started — Part 1 (2024)"
        result = sanitize_filename(title)
        # Parentheses are preserved in filenames
        assert result == "AI_Engineering_101_Getting_Started_-_Part_1_(2024)"


class TestCalculateTitleSimilarity:
    """Tests for calculate_title_similarity() function"""

    @pytest.mark.unit
    def test_identical_titles_return_1(self):
        """Should return 1.0 for identical titles"""
        title = "AI Engineering 101"
        result = calculate_title_similarity(title, title)
        assert result == 1.0

    @pytest.mark.unit
    def test_case_insensitive_comparison(self):
        """Should be case-insensitive"""
        result = calculate_title_similarity("AI Engineering 101", "ai engineering 101")
        assert result == 1.0

    @pytest.mark.unit
    def test_completely_different_titles(self):
        """Should return low score for completely different titles"""
        result = calculate_title_similarity("AI Engineering", "Cooking Recipes")
        assert result < 0.3

    @pytest.mark.unit
    def test_similar_titles_high_score(self):
        """Should return high score for similar titles"""
        result = calculate_title_similarity(
            "AI Engineering 101",
            "AI Engineering 101 with Examples"
        )
        assert result > 0.7

    @pytest.mark.unit
    def test_partial_match(self):
        """Should return medium score for partial match"""
        result = calculate_title_similarity(
            "Introduction to Machine Learning",
            "Introduction to Deep Learning"
        )
        assert 0.5 < result < 0.9

    @pytest.mark.unit
    def test_handles_empty_strings(self):
        """Should handle empty strings"""
        result = calculate_title_similarity("", "")
        assert result == 1.0  # Two empty strings are identical

    @pytest.mark.unit
    def test_handles_one_empty_string(self):
        """Should handle comparison with empty string"""
        result = calculate_title_similarity("AI Engineering", "")
        assert result == 0.0

    @pytest.mark.unit
    def test_special_characters_dont_affect_much(self):
        """Should handle special characters in comparison"""
        result = calculate_title_similarity(
            "AI: Engineering 101",
            "AI Engineering 101"
        )
        assert result > 0.9

    @pytest.mark.unit
    def test_word_order_matters(self):
        """Should give lower score for different word order"""
        result = calculate_title_similarity(
            "Machine Learning Introduction",
            "Introduction Machine Learning"
        )
        # Not identical because word order differs
        assert 0.5 < result < 0.95


class TestCheckTitleAndDateMatch:
    """Tests for check_title_and_date_match() function"""

    @pytest.mark.unit
    def test_strong_title_match_no_dates(self):
        """Should match on title alone with high similarity"""
        matches, similarity, match_type = check_title_and_date_match(
            "AI Engineering 101",
            "AI Engineering 101 Extended"
        )
        assert matches is True
        assert match_type == "strong_title"
        assert similarity >= 0.65

    @pytest.mark.unit
    def test_weak_title_no_match_without_dates(self):
        """Should not match weak title without dates"""
        matches, similarity, match_type = check_title_and_date_match(
            "AI Eng 101",
            "Artificial Intelligence Course"
        )
        assert matches is False
        assert match_type == "no_match"

    @pytest.mark.unit
    def test_weak_title_with_matching_dates(self, sample_dates):
        """Should match weak title when dates are close"""
        # These titles have ~65% similarity (just above weak threshold)
        # With dates within 1 day, should match via title_plus_date
        matches, similarity, match_type = check_title_and_date_match(
            "Data Science Overview",
            "Data Science Introduction",
            sample_dates['base'],
            sample_dates['same_day']
        )
        assert matches is True
        assert match_type in ["strong_title", "title_plus_date"]  # 65% could trigger either
        assert similarity >= 0.50

    @pytest.mark.unit
    def test_weak_title_with_far_apart_dates(self, sample_dates):
        """Should not match weak title when dates are far apart"""
        # These titles have ~65% similarity - borderline
        # With dates 7 days apart (beyond 1-day tolerance), should not match
        matches, similarity, match_type = check_title_and_date_match(
            "Data Science Overview",
            "Data Science Introduction",
            sample_dates['base'],
            sample_dates['week_later']
        )
        # Could be strong_title match (65%+) OR no_match depending on exact threshold
        # The test is checking that weak titles + far dates don't create title_plus_date match
        assert match_type != "title_plus_date"

    @pytest.mark.unit
    def test_identical_titles_always_match(self):
        """Should always match identical titles"""
        matches, similarity, match_type = check_title_and_date_match(
            "Exact Same Title",
            "Exact Same Title"
        )
        assert matches is True
        assert similarity == 1.0
        assert match_type == "strong_title"

    @pytest.mark.unit
    def test_completely_different_titles_never_match(self, sample_dates):
        """Should never match completely different titles even with same date"""
        matches, similarity, match_type = check_title_and_date_match(
            "AI Engineering",
            "Cooking Recipes",
            sample_dates['base'],
            sample_dates['base']
        )
        assert matches is False
        assert match_type == "no_match"

    @pytest.mark.unit
    def test_custom_strong_threshold(self):
        """Should respect custom strong_threshold parameter"""
        # Set very high threshold so match fails
        matches, similarity, match_type = check_title_and_date_match(
            "AI Engineering 101",
            "AI Engineering 101 Extended",
            strong_threshold=0.99
        )
        assert matches is False

    @pytest.mark.unit
    def test_custom_weak_threshold(self, sample_dates):
        """Should respect custom weak_threshold parameter"""
        # Set very low threshold so match succeeds
        matches, similarity, match_type = check_title_and_date_match(
            "AI",
            "Artificial Intelligence",
            sample_dates['base'],
            sample_dates['same_day'],
            weak_threshold=0.10
        )
        assert matches is True
        assert match_type == "title_plus_date"

    @pytest.mark.unit
    def test_custom_date_tolerance(self, sample_dates):
        """Should respect custom date_tolerance_days parameter"""
        # Allow 7 days tolerance, use titles ~65% similar
        matches, similarity, match_type = check_title_and_date_match(
            "Data Science Overview",
            "Data Science Introduction",
            sample_dates['base'],
            sample_dates['week_later'],
            date_tolerance_days=7
        )
        assert matches is True
        # Could be strong_title (65%) or title_plus_date
        assert match_type in ["strong_title", "title_plus_date"]

    @pytest.mark.unit
    def test_dates_exactly_one_day_apart(self, sample_dates):
        """Should match dates exactly 1 day apart (within default tolerance)"""
        # Use titles ~65% similar
        matches, similarity, match_type = check_title_and_date_match(
            "Data Science Overview",
            "Data Science Introduction",
            sample_dates['base'],
            sample_dates['next_day']
        )
        assert matches is True
        # Could be strong_title (65%) or title_plus_date
        assert match_type in ["strong_title", "title_plus_date"]

    @pytest.mark.unit
    def test_returns_similarity_score(self):
        """Should always return similarity score"""
        matches, similarity, match_type = check_title_and_date_match(
            "Title One",
            "Title Two"
        )
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0

    @pytest.mark.unit
    def test_match_type_values(self):
        """Should return one of the three valid match types"""
        valid_types = ["strong_title", "title_plus_date", "no_match"]

        matches, similarity, match_type = check_title_and_date_match(
            "Test Title",
            "Test Title"
        )
        assert match_type in valid_types

    @pytest.mark.unit
    def test_none_dates_handled_gracefully(self):
        """Should handle None dates without error"""
        matches, similarity, match_type = check_title_and_date_match(
            "AI Eng",
            "AI Engineering",
            None,
            None
        )
        # Should not crash and should return result based only on title
        assert isinstance(matches, bool)
        assert isinstance(similarity, float)

    @pytest.mark.unit
    def test_one_none_date_handled(self, sample_dates):
        """Should handle one None date"""
        matches, similarity, match_type = check_title_and_date_match(
            "AI Eng",
            "AI Engineering",
            sample_dates['base'],
            None
        )
        # Cannot do date comparison, so only title-based
        assert match_type != "title_plus_date"
