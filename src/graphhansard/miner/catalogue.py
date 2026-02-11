"""Metadata catalogue for downloaded session audio.

Manages the archive/catalogue.json file per SRD §7.4 (MN-6, MN-7, MN-8).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import Enum


class DownloadStatus(str, Enum):
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    SKIPPED_DUPLICATE = "skipped_duplicate"


class SessionAudio(BaseModel):
    """Metadata for a single downloaded session audio file."""

    video_id: str
    title: str
    parsed_date: date | None = None
    upload_date: date
    duration_seconds: int
    audio_format: str
    audio_bitrate_kbps: int
    file_path: str
    file_hash_sha256: str
    download_timestamp: datetime
    source_url: str
    status: DownloadStatus
    notes: str | None = None


class AudioCatalogue:
    """Manages the session audio metadata catalogue.

    See SRD §7.4 for specification.
    """

    def __init__(self, catalogue_path: str = "archive/catalogue.json"):
        raise NotImplementedError("AudioCatalogue not yet implemented — see Issue #7")

    def add_entry(self, entry: SessionAudio) -> None:
        """Add a new entry to the catalogue."""
        raise NotImplementedError

    def is_duplicate(self, video_id: str) -> bool:
        """Check if a video ID already exists in the catalogue."""
        raise NotImplementedError

    def get_all_entries(self) -> list[SessionAudio]:
        """Return all catalogue entries."""
        raise NotImplementedError
