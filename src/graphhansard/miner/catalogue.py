"""Metadata catalogue for downloaded session audio.

Manages the archive/catalogue.json file per SRD §7.4 (MN-6, MN-7, MN-8).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel


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
        """Initialize the AudioCatalogue.

        Args:
            catalogue_path: Path to the catalogue JSON file
        """
        self.catalogue_path = Path(catalogue_path)
        self.entries: list[SessionAudio] = []

        # Load existing catalogue if it exists
        if self.catalogue_path.exists():
            self._load()
        else:
            # Create parent directory if it doesn't exist
            self.catalogue_path.parent.mkdir(parents=True, exist_ok=True)
            self._save()

    def _load(self) -> None:
        """Load catalogue from JSON file."""
        with open(self.catalogue_path, "r") as f:
            data = json.load(f)
            self.entries = [SessionAudio(**entry) for entry in data]

    def _save(self) -> None:
        """Save catalogue to JSON file."""
        with open(self.catalogue_path, "w") as f:
            data = [entry.model_dump(mode="json") for entry in self.entries]
            json.dump(data, f, indent=2, default=str)

    def add_entry(self, entry: SessionAudio) -> None:
        """Add a new entry to the catalogue.

        Args:
            entry: SessionAudio metadata entry to add
        """
        # Check if this is a duplicate by video_id
        if self.is_duplicate(entry.video_id):
            # Update existing entry instead of adding duplicate
            for i, existing in enumerate(self.entries):
                if existing.video_id == entry.video_id:
                    self.entries[i] = entry
                    break
        else:
            self.entries.append(entry)

        self._save()

    def is_duplicate(self, video_id: str) -> bool:
        """Check if a video ID already exists in the catalogue.

        Args:
            video_id: YouTube video ID to check

        Returns:
            True if the video ID exists in the catalogue, False otherwise
        """
        return any(entry.video_id == video_id for entry in self.entries)

    def get_all_entries(self) -> list[SessionAudio]:
        """Return all catalogue entries.

        Returns:
            List of all SessionAudio entries
        """
        return self.entries
