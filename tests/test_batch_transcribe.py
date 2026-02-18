"""Tests for batch_transcribe.py session metadata automation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.batch_transcribe import (
    extract_session_id,
    load_session_metadata,
    validate_date_format,
)


class TestDateValidation:
    """Test date format validation."""

    def test_valid_iso8601_dates(self):
        """Test that valid ISO 8601 dates are accepted."""
        assert validate_date_format("2026-01-28") is True
        assert validate_date_format("2026-02-04") is True
        assert validate_date_format("2024-12-31") is True
        assert validate_date_format("2020-01-01") is True

    def test_invalid_date_formats(self):
        """Test that invalid date formats are rejected."""
        assert validate_date_format("28-01-2026") is False  # Wrong order
        assert validate_date_format("2026/01/28") is False  # Wrong separator
        assert validate_date_format("28 Jan 2026") is False  # Not ISO
        assert validate_date_format("2026-13-01") is False  # Invalid month
        assert validate_date_format("2026-01-32") is False  # Invalid day
        assert validate_date_format("not-a-date") is False
        assert validate_date_format("") is False
        assert validate_date_format(None) is False


class TestSessionIDExtraction:
    """Test session ID extraction from filenames."""

    def test_extract_video_id_from_filename(self):
        """Test extracting video ID from various audio filename formats."""
        assert extract_session_id(Path("7cuPpo7ko78.opus")) == "7cuPpo7ko78"
        assert extract_session_id(Path("Y--YlPwcI8o.mp3")) == "Y--YlPwcI8o"
        assert extract_session_id(Path("dQw4w9WgXcQ.wav")) == "dQw4w9WgXcQ"

    def test_extract_with_path(self):
        """Test extraction works with full paths."""
        assert extract_session_id(Path("/archive/7cuPpo7ko78.opus")) == "7cuPpo7ko78"
        assert extract_session_id(Path("archive/Y--YlPwcI8o.mp3")) == "Y--YlPwcI8o"


class TestMetadataLoading:
    """Test session metadata loading from JSON files."""

    def test_load_valid_metadata(self):
        """Test loading valid metadata JSON."""
        metadata_json = {
            "7cuPpo7ko78": {
                "date": "2026-01-28",
                "title": "House of Assembly 28 Jan 2026 Morning",
            },
            "Y--YlPwcI8o": {
                "date": "2026-02-04",
                "title": "House of Assembly 4 Feb 2026 Morning",
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(metadata_json, f)
            temp_path = f.name

        try:
            metadata = load_session_metadata(temp_path)

            assert len(metadata) == 2
            assert "7cuPpo7ko78" in metadata
            assert metadata["7cuPpo7ko78"]["date"] == "2026-01-28"
            assert metadata["7cuPpo7ko78"]["title"] == "House of Assembly 28 Jan 2026 Morning"
            assert "Y--YlPwcI8o" in metadata
        finally:
            Path(temp_path).unlink()

    def test_load_metadata_with_missing_title(self):
        """Test that missing title gets default value."""
        metadata_json = {
            "7cuPpo7ko78": {
                "date": "2026-01-28",
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(metadata_json, f)
            temp_path = f.name

        try:
            metadata = load_session_metadata(temp_path)

            assert len(metadata) == 1
            assert metadata["7cuPpo7ko78"]["title"] == "Session 7cuPpo7ko78"
        finally:
            Path(temp_path).unlink()

    def test_load_metadata_invalid_date(self):
        """Test that entries with invalid dates are skipped."""
        metadata_json = {
            "7cuPpo7ko78": {
                "date": "2026-01-28",
                "title": "Valid Session",
            },
            "invalid1": {
                "date": "28-01-2026",  # Invalid format
                "title": "Invalid Date Format",
            },
            "invalid2": {
                "date": "2026-13-01",  # Invalid month
                "title": "Invalid Month",
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(metadata_json, f)
            temp_path = f.name

        try:
            metadata = load_session_metadata(temp_path)

            assert len(metadata) == 1
            assert "7cuPpo7ko78" in metadata
            assert "invalid1" not in metadata
            assert "invalid2" not in metadata
        finally:
            Path(temp_path).unlink()

    def test_load_metadata_missing_date(self):
        """Test that entries without date field are skipped."""
        metadata_json = {
            "7cuPpo7ko78": {
                "date": "2026-01-28",
                "title": "Valid Session",
            },
            "no_date": {
                "title": "No Date Field",
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(metadata_json, f)
            temp_path = f.name

        try:
            metadata = load_session_metadata(temp_path)

            assert len(metadata) == 1
            assert "7cuPpo7ko78" in metadata
            assert "no_date" not in metadata
        finally:
            Path(temp_path).unlink()

    def test_load_metadata_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError, match="Metadata file not found"):
            load_session_metadata("/nonexistent/path/metadata.json")

    def test_load_metadata_invalid_json(self):
        """Test that ValueError is raised for invalid JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{ invalid json }")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                load_session_metadata(temp_path)
        finally:
            Path(temp_path).unlink()


class TestBatchProcessing:
    """Test batch processing with metadata."""

    @patch("scripts.batch_transcribe.create_pipeline")
    @patch("scripts.batch_transcribe.discover_audio_files")
    def test_process_batch_with_metadata(
        self, mock_discover, mock_create_pipeline
    ):
        """Test batch processing with metadata provided."""
        from scripts.batch_transcribe import process_batch

        # Mock audio files discovery
        mock_audio_files = [
            Path("7cuPpo7ko78.opus"),
            Path("Y--YlPwcI8o.mp3"),
        ]
        mock_discover.return_value = mock_audio_files

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_transcript = MagicMock()
        mock_transcript.segments = [MagicMock(), MagicMock()]
        mock_transcript.model_dump.return_value = {
            "session_id": "test",
            "segments": [],
        }
        mock_pipeline.process.return_value = mock_transcript
        mock_create_pipeline.return_value = mock_pipeline

        # Test metadata
        metadata = {
            "7cuPpo7ko78": {
                "date": "2026-01-28",
                "title": "House of Assembly 28 Jan 2026 Morning",
            },
            "Y--YlPwcI8o": {
                "date": "2026-02-04",
                "title": "House of Assembly 4 Feb 2026 Morning",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            results = process_batch(
                audio_dir="/fake/audio/dir",
                output_dir=tmpdir,
                metadata=metadata,
                device="cpu",
            )

            assert results["status"] == "success"
            assert results["total_files"] == 2
            assert results["processed"] == 2
            assert results["failed"] == 0

            assert mock_pipeline.process.call_count == 2

            output_path = Path(tmpdir)
            assert (output_path / "7cuPpo7ko78_transcript.json").exists()
            assert (output_path / "Y--YlPwcI8o_transcript.json").exists()
            assert (output_path / "batch_summary.json").exists()

            with open(output_path / "7cuPpo7ko78_transcript.json") as f:
                output_data = json.load(f)
                assert "session_metadata" in output_data
                assert output_data["session_metadata"]["date"] == "2026-01-28"
                assert output_data["session_metadata"]["title"] == "House of Assembly 28 Jan 2026 Morning"

    @patch("scripts.batch_transcribe.create_pipeline")
    @patch("scripts.batch_transcribe.discover_audio_files")
    def test_process_batch_without_metadata(
        self, mock_discover, mock_create_pipeline
    ):
        """Test batch processing without metadata (fallback to video_id)."""
        from scripts.batch_transcribe import process_batch

        mock_audio_files = [Path("7cuPpo7ko78.opus")]
        mock_discover.return_value = mock_audio_files

        mock_pipeline = MagicMock()
        mock_transcript = MagicMock()
        mock_transcript.segments = [MagicMock()]
        mock_transcript.model_dump.return_value = {
            "session_id": "7cuPpo7ko78",
            "segments": [],
        }
        mock_pipeline.process.return_value = mock_transcript
        mock_create_pipeline.return_value = mock_pipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            results = process_batch(
                audio_dir="/fake/audio/dir",
                output_dir=tmpdir,
                metadata=None,
                device="cpu",
            )

            assert results["status"] == "success"
            assert results["processed"] == 1

            with open(Path(tmpdir) / "7cuPpo7ko78_transcript.json") as f:
                output_data = json.load(f)
                assert output_data["session_metadata"]["session_id"] == "7cuPpo7ko78"
                assert output_data["session_metadata"]["date"] is None
                assert output_data["session_metadata"]["title"] == "Session 7cuPpo7ko78"

    @patch("scripts.batch_transcribe.create_pipeline")
    @patch("scripts.batch_transcribe.discover_audio_files")
    def test_process_batch_no_audio_files(
        self, mock_discover, mock_create_pipeline
    ):
        """Test batch processing with no audio files."""
        from scripts.batch_transcribe import process_batch

        mock_discover.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            results = process_batch(
                audio_dir="/fake/audio/dir",
                output_dir=tmpdir,
                metadata=None,
                device="cpu",
            )

            assert results["status"] == "error"
            assert results["processed"] == 0
            assert "No audio files found" in results["message"]
