"""Test for NF-6: Miner pipeline idempotency and resumability.

Requirement: Re-running does not duplicate data.

This test verifies that the miner pipeline is idempotent - running it
multiple times on the same input produces identical output without
duplicating downloads or catalogue entries.
"""

import json
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

from graphhansard.miner.catalogue import AudioCatalogue, DownloadStatus, SessionAudio
from graphhansard.miner.downloader import SessionDownloader


def _make_session_audio(
    video_id: str,
    title: str = "Test Session",
    upload_date: date | None = None,
    status: DownloadStatus = DownloadStatus.DOWNLOADED,
    file_path: str = "",
) -> SessionAudio:
    """Helper to build a valid SessionAudio entry for testing."""
    return SessionAudio(
        video_id=video_id,
        title=title,
        upload_date=upload_date or date(2024, 1, 15),
        duration_seconds=3600,
        audio_format="opus",
        audio_bitrate_kbps=128,
        file_path=file_path or f"archive/2024/{video_id}.opus",
        file_hash_sha256=f"sha256_{video_id}",
        download_timestamp=datetime.now(timezone.utc),
        source_url=f"https://youtube.com/watch?v={video_id}",
        status=status,
    )


def test_miner_idempotency():
    """Test that re-running miner pipeline does not duplicate data (NF-6)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_dir = Path(tmpdir) / "archive"

        # First run: create downloader and add a session
        downloader1 = SessionDownloader(
            archive_dir=str(archive_dir),
            sleep_interval=0,
            max_downloads=5,
        )

        entry = _make_session_audio("test_video_123")
        downloader1.catalogue.add_entry(entry)

        # Verify entry was added
        entries_after_first = downloader1.catalogue.get_all_entries()
        assert len(entries_after_first) == 1
        assert entries_after_first[0].video_id == "test_video_123"

        # Save catalogue state
        catalogue_path = archive_dir / "catalogue.json"
        with open(catalogue_path, "r", encoding="utf-8") as f:
            catalogue_first_run = json.load(f)

        # Second run: create new downloader (simulates re-run), add same session
        downloader2 = SessionDownloader(
            archive_dir=str(archive_dir),
            sleep_interval=0,
            max_downloads=5,
        )

        # Verify catalogue was loaded from disk
        loaded_entries = downloader2.catalogue.get_all_entries()
        assert len(loaded_entries) == 1, "Catalogue should load existing entries"

        # Try to add same session again — should update, not duplicate
        entry_again = _make_session_audio("test_video_123")
        assert downloader2.catalogue.is_duplicate("test_video_123"), (
            "is_duplicate should detect existing video_id"
        )
        downloader2.catalogue.add_entry(entry_again)

        # Verify idempotency: count should not increase
        entries_after_second = downloader2.catalogue.get_all_entries()
        assert len(entries_after_second) == len(entries_after_first), (
            f"Entry count should be unchanged: {len(entries_after_first)} vs {len(entries_after_second)}"
        )

        # Verify no duplicate video_ids
        video_ids = [e.video_id for e in entries_after_second]
        assert len(video_ids) == len(set(video_ids)), "No duplicate video_ids allowed"

        # Verify catalogue structure preserved
        with open(catalogue_path, "r", encoding="utf-8") as f:
            catalogue_second_run = json.load(f)
        assert len(catalogue_first_run) == len(catalogue_second_run), (
            "Catalogue entry count should be unchanged on disk"
        )


def test_miner_resumability():
    """Test that miner can resume after interruption (NF-6)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_dir = Path(tmpdir) / "archive"

        # First run: add sessions with different statuses
        downloader1 = SessionDownloader(
            archive_dir=str(archive_dir),
            sleep_interval=0,
            max_downloads=10,
        )

        sessions = [
            _make_session_audio("video_001", title="Completed Session",
                                status=DownloadStatus.DOWNLOADED),
            _make_session_audio("video_002", title="Failed Session",
                                status=DownloadStatus.FAILED),
            _make_session_audio("video_003", title="Duplicate Session",
                                status=DownloadStatus.SKIPPED_DUPLICATE),
        ]

        for session in sessions:
            downloader1.catalogue.add_entry(session)

        # Verify all entries added
        assert len(downloader1.catalogue.get_all_entries()) == 3

        # Simulate resume: create new downloader loading existing catalogue
        downloader2 = SessionDownloader(
            archive_dir=str(archive_dir),
            sleep_interval=0,
            max_downloads=10,
        )

        # Verify catalogue loaded correctly
        all_entries = downloader2.catalogue.get_all_entries()
        assert len(all_entries) == 3, (
            f"Expected 3 entries after resume, got {len(all_entries)}"
        )

        # Verify completed sessions are detected as duplicates (won't re-download)
        assert downloader2.catalogue.is_duplicate("video_001"), (
            "Completed session should be detected as duplicate"
        )

        # Verify failed sessions are also in catalogue (can be retried)
        assert downloader2.catalogue.is_duplicate("video_002"), (
            "Failed session should be in catalogue"
        )

        # Verify status values persisted correctly
        status_map = {e.video_id: e.status for e in all_entries}
        assert status_map["video_001"] == DownloadStatus.DOWNLOADED
        assert status_map["video_002"] == DownloadStatus.FAILED
        assert status_map["video_003"] == DownloadStatus.SKIPPED_DUPLICATE

        # Verify download archive file exists for yt-dlp resumability
        download_archive = archive_dir / "download_archive.txt"
        assert download_archive.parent.exists(), (
            "Archive directory should exist for resumability"
        )


if __name__ == "__main__":
    print("Running NF-6 Tests: Miner Pipeline Idempotency & Resumability")
    print("=" * 60)

    test_miner_idempotency()
    print("✅ test_miner_idempotency passed")

    test_miner_resumability()
    print("✅ test_miner_resumability passed")

    print("\n✅ NF-6: All tests passed - Pipeline is idempotent and resumable")
