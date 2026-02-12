"""Tests for Layer 1 — The Miner.

Covers: download pipeline, metadata catalogue, CLI.
See Issues #6 through #8.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from graphhansard.miner.catalogue import AudioCatalogue, DownloadStatus, SessionAudio
from graphhansard.miner.cli import main
from graphhansard.miner.download_logger import DownloadLogger
from graphhansard.miner.downloader import SessionDownloader


class TestSessionAudio:
    """Test SessionAudio schema validation."""

    def test_session_audio_creation(self):
        """Test creating a valid SessionAudio object."""
        entry = SessionAudio(
            video_id="test123",
            title="Test Session",
            upload_date=datetime(2024, 1, 1).date(),
            duration_seconds=3600,
            audio_format="opus",
            audio_bitrate_kbps=128,
            file_path="archive/2024/20240101/test123.opus",
            file_hash_sha256="abc123",
            download_timestamp=datetime.now(timezone.utc),
            source_url="https://youtube.com/watch?v=test123",
            status=DownloadStatus.DOWNLOADED,
        )

        assert entry.video_id == "test123"
        assert entry.title == "Test Session"
        assert entry.audio_format == "opus"
        assert entry.status == DownloadStatus.DOWNLOADED

    def test_session_audio_with_optional_fields(self):
        """Test SessionAudio with optional fields."""
        entry = SessionAudio(
            video_id="test456",
            title="Test Session 2",
            parsed_date=datetime(2024, 1, 15).date(),
            upload_date=datetime(2024, 1, 1).date(),
            duration_seconds=7200,
            audio_format="m4a",
            audio_bitrate_kbps=256,
            file_path="archive/2024/20240101/test456.m4a",
            file_hash_sha256="def456",
            download_timestamp=datetime.now(timezone.utc),
            source_url="https://youtube.com/watch?v=test456",
            status=DownloadStatus.DOWNLOADED,
            notes="Test note",
        )

        assert entry.parsed_date == datetime(2024, 1, 15).date()
        assert entry.notes == "Test note"


class TestAudioCatalogue:
    """Test AudioCatalogue metadata management."""

    def test_catalogue_initialization_creates_file(self):
        """Test that initializing a catalogue creates the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalogue_path = Path(tmpdir) / "catalogue.json"
            catalogue = AudioCatalogue(str(catalogue_path))

            assert catalogue_path.exists()
            assert catalogue.get_all_entries() == []

    def test_catalogue_add_entry(self):
        """Test adding an entry to the catalogue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalogue_path = Path(tmpdir) / "catalogue.json"
            catalogue = AudioCatalogue(str(catalogue_path))

            entry = SessionAudio(
                video_id="test789",
                title="Test Session 3",
                upload_date=datetime(2024, 1, 1).date(),
                duration_seconds=1800,
                audio_format="opus",
                audio_bitrate_kbps=128,
                file_path="test.opus",
                file_hash_sha256="ghi789",
                download_timestamp=datetime.now(timezone.utc),
                source_url="https://youtube.com/watch?v=test789",
                status=DownloadStatus.DOWNLOADED,
            )

            catalogue.add_entry(entry)
            entries = catalogue.get_all_entries()

            assert len(entries) == 1
            assert entries[0].video_id == "test789"

    def test_catalogue_is_duplicate(self):
        """Test duplicate detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalogue_path = Path(tmpdir) / "catalogue.json"
            catalogue = AudioCatalogue(str(catalogue_path))

            entry = SessionAudio(
                video_id="test999",
                title="Test Session 4",
                upload_date=datetime(2024, 1, 1).date(),
                duration_seconds=1800,
                audio_format="opus",
                audio_bitrate_kbps=128,
                file_path="test.opus",
                file_hash_sha256="xyz999",
                download_timestamp=datetime.now(timezone.utc),
                source_url="https://youtube.com/watch?v=test999",
                status=DownloadStatus.DOWNLOADED,
            )

            assert not catalogue.is_duplicate("test999")
            catalogue.add_entry(entry)
            assert catalogue.is_duplicate("test999")
            assert not catalogue.is_duplicate("other_id")

    def test_catalogue_persistence(self):
        """Test that catalogue persists across reloads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalogue_path = Path(tmpdir) / "catalogue.json"

            # Create and add entry
            catalogue1 = AudioCatalogue(str(catalogue_path))
            entry = SessionAudio(
                video_id="persist123",
                title="Persistent Entry",
                upload_date=datetime(2024, 1, 1).date(),
                duration_seconds=1800,
                audio_format="opus",
                audio_bitrate_kbps=128,
                file_path="test.opus",
                file_hash_sha256="persist123",
                download_timestamp=datetime.now(timezone.utc),
                source_url="https://youtube.com/watch?v=persist123",
                status=DownloadStatus.DOWNLOADED,
            )
            catalogue1.add_entry(entry)

            # Reload catalogue
            catalogue2 = AudioCatalogue(str(catalogue_path))
            entries = catalogue2.get_all_entries()

            assert len(entries) == 1
            assert entries[0].video_id == "persist123"

    def test_catalogue_update_existing_entry(self):
        """Test updating an existing entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalogue_path = Path(tmpdir) / "catalogue.json"
            catalogue = AudioCatalogue(str(catalogue_path))

            # Add initial entry
            entry1 = SessionAudio(
                video_id="update123",
                title="Original Title",
                upload_date=datetime(2024, 1, 1).date(),
                duration_seconds=1800,
                audio_format="opus",
                audio_bitrate_kbps=128,
                file_path="test.opus",
                file_hash_sha256="update123",
                download_timestamp=datetime.now(timezone.utc),
                source_url="https://youtube.com/watch?v=update123",
                status=DownloadStatus.DOWNLOADED,
            )
            catalogue.add_entry(entry1)

            # Update with new entry
            entry2 = SessionAudio(
                video_id="update123",
                title="Updated Title",
                upload_date=datetime(2024, 1, 1).date(),
                duration_seconds=1800,
                audio_format="opus",
                audio_bitrate_kbps=128,
                file_path="test.opus",
                file_hash_sha256="update123",
                download_timestamp=datetime.now(timezone.utc),
                source_url="https://youtube.com/watch?v=update123",
                status=DownloadStatus.DOWNLOADED,
            )
            catalogue.add_entry(entry2)

            entries = catalogue.get_all_entries()
            assert len(entries) == 1
            assert entries[0].title == "Updated Title"

    def test_catalogue_is_duplicate_by_hash(self):
        """Test hash-based duplicate detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalogue_path = Path(tmpdir) / "catalogue.json"
            catalogue = AudioCatalogue(str(catalogue_path))

            fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            entry = SessionAudio(
                video_id="hash_test_123",
                title="Hash Test Session",
                upload_date=datetime(2024, 1, 1).date(),
                duration_seconds=1800,
                audio_format="opus",
                audio_bitrate_kbps=128,
                file_path="test.opus",
                file_hash_sha256="abc123def456",
                download_timestamp=fixed_time,
                source_url="https://youtube.com/watch?v=hash_test_123",
                status=DownloadStatus.DOWNLOADED,
            )

            assert not catalogue.is_duplicate_by_hash("abc123def456")
            catalogue.add_entry(entry)
            assert catalogue.is_duplicate_by_hash("abc123def456")
            assert not catalogue.is_duplicate_by_hash("different_hash")

    def test_catalogue_is_duplicate_by_hash_ignores_failed(self):
        """Test that hash duplicate detection ignores failed downloads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalogue_path = Path(tmpdir) / "catalogue.json"
            catalogue = AudioCatalogue(str(catalogue_path))

            fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            # Add a failed entry with a hash
            failed_entry = SessionAudio(
                video_id="failed_123",
                title="Failed Session",
                upload_date=datetime(2024, 1, 1).date(),
                duration_seconds=0,
                audio_format="",
                audio_bitrate_kbps=0,
                file_path="",
                file_hash_sha256="failed_hash_123",
                download_timestamp=fixed_time,
                source_url="https://youtube.com/watch?v=failed_123",
                status=DownloadStatus.FAILED,
            )
            catalogue.add_entry(failed_entry)

            # Hash should not be considered a duplicate because status is FAILED
            assert not catalogue.is_duplicate_by_hash("failed_hash_123")

            # Add a successful entry with same hash
            success_entry = SessionAudio(
                video_id="success_123",
                title="Success Session",
                upload_date=datetime(2024, 1, 1).date(),
                duration_seconds=1800,
                audio_format="opus",
                audio_bitrate_kbps=128,
                file_path="test.opus",
                file_hash_sha256="failed_hash_123",
                download_timestamp=fixed_time,
                source_url="https://youtube.com/watch?v=success_123",
                status=DownloadStatus.DOWNLOADED,
            )
            catalogue.add_entry(success_entry)

            # Now it should be a duplicate
            assert catalogue.is_duplicate_by_hash("failed_hash_123")

    def test_catalogue_is_duplicate_by_hash_empty_string(self):
        """Empty hash string never matches as duplicate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalogue_path = Path(tmpdir) / "catalogue.json"
            catalogue = AudioCatalogue(str(catalogue_path))

            # Add a valid entry
            entry = SessionAudio(
                video_id="hash_empty_test",
                title="Hash Empty Test",
                upload_date=datetime(2024, 1, 1).date(),
                duration_seconds=1800,
                audio_format="opus",
                audio_bitrate_kbps=128,
                file_path="test.opus",
                file_hash_sha256="real_hash_value",
                download_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                source_url="https://youtube.com/watch?v=hash_empty_test",
                status=DownloadStatus.DOWNLOADED,
            )
            catalogue.add_entry(entry)

            assert not catalogue.is_duplicate_by_hash("")


class TestSessionDownloader:
    """Test SessionDownloader functionality."""

    def test_downloader_initialization(self):
        """Test SessionDownloader initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = SessionDownloader(
                archive_dir=tmpdir,
                cookies_path=None,
                sleep_interval=1,
                max_downloads=10,
            )

            assert downloader.archive_dir == Path(tmpdir)
            assert downloader.sleep_interval == 1
            assert downloader.max_downloads == 10
            assert downloader.download_count == 0

    @patch("yt_dlp.YoutubeDL")
    def test_discover_sessions(self, mock_ytdl_class):
        """Test discovering sessions from a channel."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock yt-dlp response
            mock_ytdl = MagicMock()
            mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
            mock_ytdl.extract_info.return_value = {
                "entries": [
                    {
                        "id": "video1",
                        "title": "Session 1",
                        "url": "https://youtube.com/watch?v=video1",
                        "duration": 3600,
                        "upload_date": "20240101",
                    },
                    {
                        "id": "video2",
                        "title": "Session 2",
                        "url": "https://youtube.com/watch?v=video2",
                        "duration": 7200,
                        "upload_date": "20240102",
                    },
                ]
            }

            downloader = SessionDownloader(archive_dir=tmpdir)
            videos = downloader.discover_sessions("https://youtube.com/@TestChannel")

            assert len(videos) == 2
            assert videos[0]["id"] == "video1"
            assert videos[1]["id"] == "video2"

    @patch("time.sleep")
    @patch("yt_dlp.YoutubeDL")
    def test_download_session(self, mock_ytdl_class, mock_sleep):
        """Test downloading a single session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake audio file
            year_dir = Path(tmpdir) / "2024"
            date_dir = year_dir / "20240101"
            date_dir.mkdir(parents=True)
            test_file = date_dir / "testvideo.opus"
            test_file.write_bytes(b"fake audio data")

            # Mock yt-dlp response
            mock_ytdl = MagicMock()
            mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
            mock_ytdl.extract_info.return_value = {
                "id": "testvideo",
                "title": "Test Session",
                "webpage_url": "https://youtube.com/watch?v=testvideo",
                "upload_date": "20240101",
                "duration": 1800,
                "requested_downloads": [{
                    "filepath": str(test_file),
                    "ext": "opus",
                    "abr": 128,
                }],
            }

            downloader = SessionDownloader(
                archive_dir=tmpdir,
                sleep_interval=1,
                max_downloads=10,
            )
            result = downloader.download_session("https://youtube.com/watch?v=testvideo")

            assert result["status"] == "success"
            assert result["video_id"] == "testvideo"
            assert downloader.download_count == 1

    @patch("time.sleep")
    @patch("yt_dlp.YoutubeDL")
    def test_download_session_detects_hash_duplicate(self, mock_ytdl_class, mock_sleep):
        """Test that downloader detects hash-based duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create first audio file
            year_dir = Path(tmpdir) / "2024"
            date_dir = year_dir / "20240101"
            date_dir.mkdir(parents=True)
            test_file1 = date_dir / "video1.opus"
            test_file1.write_bytes(b"fake audio data")

            # Create second location with identical content
            date_dir2 = year_dir / "20240102"
            date_dir2.mkdir(parents=True)
            test_file2 = date_dir2 / "video2.opus"
            test_file2.write_bytes(b"fake audio data")  # Same content = same hash

            # Mock yt-dlp for first download
            mock_ytdl = MagicMock()
            mock_ytdl_class.return_value.__enter__.return_value = mock_ytdl
            mock_ytdl.extract_info.return_value = {
                "id": "video1",
                "title": "Test Session 1",
                "webpage_url": "https://youtube.com/watch?v=video1",
                "upload_date": "20240101",
                "duration": 1800,
                "requested_downloads": [{
                    "filepath": str(test_file1),
                    "ext": "opus",
                    "abr": 128,
                }],
            }

            downloader = SessionDownloader(
                archive_dir=tmpdir,
                sleep_interval=1,
                max_downloads=10,
            )

            # Download first video
            result1 = downloader.download_session("https://youtube.com/watch?v=video1")
            assert result1["status"] == "success"

            # Mock yt-dlp for second download (same content, different video)
            mock_ytdl.extract_info.return_value = {
                "id": "video2",
                "title": "Test Session 2",
                "webpage_url": "https://youtube.com/watch?v=video2",
                "upload_date": "20240102",
                "duration": 1800,
                "requested_downloads": [{
                    "filepath": str(test_file2),
                    "ext": "opus",
                    "abr": 128,
                }],
            }

            # Download second video - should detect duplicate by hash
            result2 = downloader.download_session("https://youtube.com/watch?v=video2")
            assert result2["status"] == "skipped_duplicate"
            assert result2["reason"] == "hash_match"

            # Verify catalogue has both entries
            entries = downloader.catalogue.get_all_entries()
            assert len(entries) == 2
            assert entries[0].status == DownloadStatus.DOWNLOADED
            assert entries[1].status == DownloadStatus.SKIPPED_DUPLICATE


class TestCLI:
    """Test CLI argument parsing and command dispatch."""

    def test_cli_no_command(self, capsys):
        """Test CLI with no command shows help."""
        exit_code = main([])

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "GraphHansard Audio Ingestion Pipeline" in captured.out

    def test_cli_scrape_help(self, capsys):
        """Test scrape command help."""
        with pytest.raises(SystemExit):
            main(["scrape", "--help"])

        captured = capsys.readouterr()
        assert "Full scrape" in captured.out

    def test_cli_status_no_catalogue(self, capsys, monkeypatch, tmp_path):
        """Test status command with no catalogue."""
        monkeypatch.chdir(tmp_path)
        exit_code = main(["status"])
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "No catalogue found" in captured.out

    def test_cli_add_manual(self, monkeypatch, tmp_path):
        """Test add-manual command."""
        # Create a fake audio file
        test_file = tmp_path / "test.opus"
        test_file.write_bytes(b"fake audio")

        # Create archive directory
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()

        monkeypatch.chdir(tmp_path)
        exit_code = main([
            "add-manual",
            str(test_file),
            "--date", "2024-01-01",
            "--title", "Manual Session"
        ])

        assert exit_code == 0

        # Check catalogue was created
        catalogue_path = archive_dir / "catalogue.json"
        assert catalogue_path.exists()

        # Verify entry
        catalogue = AudioCatalogue(str(catalogue_path))
        entries = catalogue.get_all_entries()
        assert len(entries) == 1
        assert entries[0].title == "Manual Session"


class TestDownloadLogger:
    """Test DownloadLogger structured logging."""

    def test_download_logger_initialization(self):
        """Test initializing the download logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "download_log.jsonl"
            DownloadLogger(str(log_path))

            assert log_path.exists()

    def test_log_download_success(self):
        """Test logging a successful download."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "download_log.jsonl"
            logger = DownloadLogger(str(log_path))

            logger.log_download_success(
                video_id="test123",
                duration=45.5,
                file_path="archive/2024/20240101/test123.opus",
            )

            # Verify log entry
            with open(log_path, "r") as f:
                entries = [json.loads(line) for line in f]

            assert len(entries) == 1
            entry = entries[0]
            assert entry["video_id"] == "test123"
            assert entry["action"] == "download"
            assert entry["reason"] == "success"
            assert entry["duration"] == 45.5
            assert entry["file_path"] == "archive/2024/20240101/test123.opus"
            assert "timestamp" in entry

    def test_log_download_failed(self):
        """Test logging a failed download."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "download_log.jsonl"
            logger = DownloadLogger(str(log_path))

            logger.log_download_failed(
                video_id="test456",
                duration=10.2,
                error="Connection timeout",
            )

            # Verify log entry
            with open(log_path, "r") as f:
                entries = [json.loads(line) for line in f]

            assert len(entries) == 1
            entry = entries[0]
            assert entry["video_id"] == "test456"
            assert entry["action"] == "download"
            assert entry["reason"] == "failed"
            assert entry["duration"] == 10.2
            assert entry["error"] == "Connection timeout"

    def test_log_download_skipped(self):
        """Test logging a skipped download."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "download_log.jsonl"
            logger = DownloadLogger(str(log_path))

            logger.log_download_skipped(
                video_id="test789",
                reason="duplicate",
            )

            # Verify log entry
            with open(log_path, "r") as f:
                entries = [json.loads(line) for line in f]

            assert len(entries) == 1
            entry = entries[0]
            assert entry["video_id"] == "test789"
            assert entry["action"] == "skip"
            assert entry["reason"] == "duplicate"
            assert entry["duration"] is None

    def test_log_manual_addition(self):
        """Test logging a manual file addition."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "download_log.jsonl"
            logger = DownloadLogger(str(log_path))

            logger.log_manual_addition(
                video_id="manual_abc123",
                file_path="/path/to/manual.opus",
                title="Manual Session",
            )

            # Verify log entry
            with open(log_path, "r") as f:
                entries = [json.loads(line) for line in f]

            assert len(entries) == 1
            entry = entries[0]
            assert entry["video_id"] == "manual_abc123"
            assert entry["action"] == "manual_add"
            assert entry["reason"] == "success"
            assert entry["file_path"] == "/path/to/manual.opus"
            assert entry["title"] == "Manual Session"

    def test_multiple_log_entries(self):
        """Test logging multiple entries to the same file."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "download_log.jsonl"
            logger = DownloadLogger(str(log_path))

            # Log multiple entries
            logger.log_download_success("video1", 30.0, "file1.opus")
            logger.log_download_failed("video2", 5.0, "Error")
            logger.log_download_skipped("video3", "duplicate")

            # Verify all entries
            with open(log_path, "r") as f:
                entries = [json.loads(line) for line in f]

            assert len(entries) == 3
            assert entries[0]["video_id"] == "video1"
            assert entries[1]["video_id"] == "video2"
            assert entries[2]["video_id"] == "video3"


class TestProxyRotation:
    """Test proxy rotation functionality."""

    def test_proxy_list_loading(self):
        """Test loading proxy list from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a proxy list file
            proxy_list_path = Path(tmpdir) / "proxies.txt"
            proxy_list_path.write_text("http://proxy1:8080\nhttp://proxy2:8080\n# Comment\n\nhttp://proxy3:8080\n")

            downloader = SessionDownloader(
                archive_dir=tmpdir,
                proxy_list_path=str(proxy_list_path),
            )

            assert len(downloader.proxies) == 3
            assert "http://proxy1:8080" in downloader.proxies
            assert "http://proxy2:8080" in downloader.proxies
            assert "http://proxy3:8080" in downloader.proxies

    def test_proxy_rotation(self):
        """Test that proxies rotate correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a proxy list file
            proxy_list_path = Path(tmpdir) / "proxies.txt"
            proxy_list_path.write_text("http://proxy1:8080\nhttp://proxy2:8080\n")

            downloader = SessionDownloader(
                archive_dir=tmpdir,
                proxy_list_path=str(proxy_list_path),
            )

            # Get proxies in sequence
            proxy1 = downloader._get_next_proxy()
            proxy2 = downloader._get_next_proxy()
            proxy3 = downloader._get_next_proxy()

            assert proxy1 == "http://proxy1:8080"
            assert proxy2 == "http://proxy2:8080"
            assert proxy3 == "http://proxy1:8080"  # Should wrap around

    def test_downloader_without_proxy(self):
        """Test that downloader works without proxy list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = SessionDownloader(archive_dir=tmpdir)

            assert downloader.proxies == []
            assert downloader._get_next_proxy() is None
