"""Tests for fetch_session_metadata.py YouTube metadata extraction."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Import the functions we need to test
import sys

scripts_path = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_path))

try:
    from fetch_session_metadata import (
        convert_upload_date,
        extract_video_id,
        parse_date_from_title,
    )
except ImportError:
    pytest.skip("fetch_session_metadata.py not available", allow_module_level=True)


class TestVideoIDExtraction:
    """Test YouTube video ID extraction from URLs."""
    
    def test_extract_from_watch_url(self):
        """Test extraction from standard watch URLs."""
        url = "https://www.youtube.com/watch?v=7cuPpo7ko78"
        assert extract_video_id(url) == "7cuPpo7ko78"
        
        url = "https://youtube.com/watch?v=Y--YlPwcI8o"
        assert extract_video_id(url) == "Y--YlPwcI8o"
    
    def test_extract_from_short_url(self):
        """Test extraction from youtu.be short URLs."""
        url = "https://youtu.be/7cuPpo7ko78"
        assert extract_video_id(url) == "7cuPpo7ko78"
        
        url = "http://youtu.be/Y--YlPwcI8o"
        assert extract_video_id(url) == "Y--YlPwcI8o"
    
    def test_extract_from_embed_url(self):
        """Test extraction from embed URLs."""
        url = "https://www.youtube.com/embed/7cuPpo7ko78"
        assert extract_video_id(url) == "7cuPpo7ko78"
    
    def test_extract_from_bare_id(self):
        """Test that bare video IDs are accepted."""
        assert extract_video_id("7cuPpo7ko78") == "7cuPpo7ko78"
        assert extract_video_id("Y--YlPwcI8o") == "Y--YlPwcI8o"
    
    def test_extract_from_invalid_url(self):
        """Test that invalid URLs return None."""
        assert extract_video_id("https://www.google.com") is None
        assert extract_video_id("not-a-url") is None
        assert extract_video_id("") is None


class TestUploadDateConversion:
    """Test conversion of yt-dlp upload dates to ISO 8601."""
    
    def test_convert_valid_upload_date(self):
        """Test converting valid YYYYMMDD format."""
        assert convert_upload_date("20260128") == "2026-01-28"
        assert convert_upload_date("20260204") == "2026-02-04"
        assert convert_upload_date("20241231") == "2024-12-31"
    
    def test_convert_invalid_format(self):
        """Test that invalid formats raise ValueError."""
        with pytest.raises(ValueError):
            convert_upload_date("2026-01-28")  # Wrong separator
        
        with pytest.raises(ValueError):
            convert_upload_date("260128")  # Too short
        
        with pytest.raises(ValueError):
            convert_upload_date("202601281")  # Too long
    
    def test_convert_invalid_date(self):
        """Test that invalid dates raise ValueError."""
        with pytest.raises(ValueError):
            convert_upload_date("20261301")  # Invalid month
        
        with pytest.raises(ValueError):
            convert_upload_date("20260132")  # Invalid day


class TestTitleDateParsing:
    """Test parsing dates from video titles."""
    
    def test_parse_short_month_format(self):
        """Test parsing 'DD Mon YYYY' format."""
        title = "House of Assembly 28 Jan 2026 Morning"
        assert parse_date_from_title(title) == "2026-01-28"
        
        title = "House of Assembly 4 Feb 2026 Morning"
        assert parse_date_from_title(title) == "2026-02-04"
        
        title = "Session - 15 Dec 2024"
        assert parse_date_from_title(title) == "2024-12-15"
    
    def test_parse_iso_format(self):
        """Test parsing ISO 8601 dates in titles."""
        title = "Parliamentary Session 2026-01-28"
        assert parse_date_from_title(title) == "2026-01-28"
        
        title = "Debate 2026-02-04 Part 1"
        assert parse_date_from_title(title) == "2026-02-04"
    
    def test_parse_long_month_format(self):
        """Test parsing 'Month DD, YYYY' format."""
        title = "House of Assembly January 28, 2026"
        assert parse_date_from_title(title) == "2026-01-28"
        
        title = "February 4, 2026 - Morning Session"
        assert parse_date_from_title(title) == "2026-02-04"
        
        title = "December 31, 2024 Special Session"
        assert parse_date_from_title(title) == "2024-12-31"
    
    def test_parse_no_date_in_title(self):
        """Test that titles without dates return None."""
        assert parse_date_from_title("House of Assembly Session") is None
        assert parse_date_from_title("Morning Debate") is None
        assert parse_date_from_title("") is None
    
    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        title = "house of assembly 28 JAN 2026"
        assert parse_date_from_title(title) == "2026-01-28"
        
        title = "FEBRUARY 4, 2026"
        assert parse_date_from_title(title) == "2026-02-04"
    
    def test_parse_all_months(self):
        """Test parsing all month names."""
        month_tests = [
            ("1 Jan 2026", "2026-01-01"),
            ("2 Feb 2026", "2026-02-02"),
            ("3 Mar 2026", "2026-03-03"),
            ("4 Apr 2026", "2026-04-04"),
            ("5 May 2026", "2026-05-05"),
            ("6 Jun 2026", "2026-06-06"),
            ("7 Jul 2026", "2026-07-07"),
            ("8 Aug 2026", "2026-08-08"),
            ("9 Sep 2026", "2026-09-09"),
            ("10 Oct 2026", "2026-10-10"),
            ("11 Nov 2026", "2026-11-11"),
            ("12 Dec 2026", "2026-12-12"),
        ]
        
        for title, expected in month_tests:
            assert parse_date_from_title(title) == expected


class TestProcessVideo:
    """Test processing individual videos to extract metadata."""
    
    @patch("fetch_session_metadata.fetch_youtube_metadata")
    def test_process_video_with_valid_metadata(self, mock_fetch):
        """Test processing video with valid YouTube metadata."""
        from fetch_session_metadata import process_video
        
        # Mock yt-dlp response
        mock_fetch.return_value = {
            "title": "House of Assembly 28 Jan 2026 Morning",
            "upload_date": "20260128",
        }
        
        result = process_video("7cuPpo7ko78", parse_title_date=False)
        
        assert result is not None
        assert result["date"] == "2026-01-28"
        assert result["title"] == "House of Assembly 28 Jan 2026 Morning"
    
    @patch("fetch_session_metadata.fetch_youtube_metadata")
    def test_process_video_parse_title_date(self, mock_fetch):
        """Test that title date parsing takes precedence when enabled."""
        from fetch_session_metadata import process_video
        
        # Mock yt-dlp response with different upload_date
        mock_fetch.return_value = {
            "title": "House of Assembly 28 Jan 2026 Morning",
            "upload_date": "20260201",  # Different from title date
        }
        
        result = process_video("7cuPpo7ko78", parse_title_date=True)
        
        assert result is not None
        # Should use title date, not upload date
        assert result["date"] == "2026-01-28"
    
    @patch("fetch_session_metadata.fetch_youtube_metadata")
    def test_process_video_fallback_to_upload_date(self, mock_fetch):
        """Test fallback to upload_date when title has no date."""
        from fetch_session_metadata import process_video
        
        # Mock yt-dlp response with no date in title
        mock_fetch.return_value = {
            "title": "House of Assembly Morning Session",
            "upload_date": "20260128",
        }
        
        result = process_video("7cuPpo7ko78", parse_title_date=True)
        
        assert result is not None
        # Should fall back to upload date
        assert result["date"] == "2026-01-28"
    
    @patch("fetch_session_metadata.fetch_youtube_metadata")
    def test_process_video_no_date_available(self, mock_fetch):
        """Test that None is returned when no date is available."""
        from fetch_session_metadata import process_video
        
        # Mock yt-dlp response with no upload_date
        mock_fetch.return_value = {
            "title": "House of Assembly Session",
            # No upload_date field
        }
        
        result = process_video("7cuPpo7ko78", parse_title_date=False)
        
        # Should return None when no date is available
        assert result is None
    
    @patch("fetch_session_metadata.fetch_youtube_metadata")
    def test_process_video_fetch_failed(self, mock_fetch):
        """Test that None is returned when fetch fails."""
        from fetch_session_metadata import process_video
        
        # Mock fetch failure
        mock_fetch.return_value = None
        
        result = process_video("7cuPpo7ko78")
        
        assert result is None


class TestLoadURLsFromFile:
    """Test loading YouTube URLs from text files."""
    
    def test_load_urls_basic(self):
        """Test loading basic URL list."""
        from fetch_session_metadata import load_urls_from_file
        
        url_content = """https://www.youtube.com/watch?v=7cuPpo7ko78
https://www.youtube.com/watch?v=Y--YlPwcI8o
https://youtu.be/dQw4w9WgXcQ
"""
        
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write(url_content)
            temp_path = f.name
        
        try:
            urls = load_urls_from_file(Path(temp_path))
            
            assert len(urls) == 3
            assert "7cuPpo7ko78" in urls[0]
            assert "Y--YlPwcI8o" in urls[1]
            assert "dQw4w9WgXcQ" in urls[2]
        finally:
            Path(temp_path).unlink()
    
    def test_load_urls_with_comments(self):
        """Test that comments are ignored."""
        from fetch_session_metadata import load_urls_from_file
        
        url_content = """# This is a comment
https://www.youtube.com/watch?v=7cuPpo7ko78
# Another comment
https://www.youtube.com/watch?v=Y--YlPwcI8o
"""
        
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write(url_content)
            temp_path = f.name
        
        try:
            urls = load_urls_from_file(Path(temp_path))
            
            # Should only have 2 URLs (comments ignored)
            assert len(urls) == 2
        finally:
            Path(temp_path).unlink()
    
    def test_load_urls_with_blank_lines(self):
        """Test that blank lines are ignored."""
        from fetch_session_metadata import load_urls_from_file
        
        url_content = """
https://www.youtube.com/watch?v=7cuPpo7ko78

https://www.youtube.com/watch?v=Y--YlPwcI8o

"""
        
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write(url_content)
            temp_path = f.name
        
        try:
            urls = load_urls_from_file(Path(temp_path))
            
            # Should only have 2 URLs (blank lines ignored)
            assert len(urls) == 2
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
