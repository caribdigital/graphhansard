"""Structured logging for download attempts.

Logs all download attempts to archive/download_log.jsonl per SRD §7.2 (MN-10).
Each log entry contains: timestamp, video_id, action, reason, duration.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DownloadLogger:
    """Structured logger for download attempts."""

    def __init__(self, log_path: str = "archive/download_log.jsonl"):
        """Initialize the download logger.

        Args:
            log_path: Path to the JSONL log file
        """
        self.log_path = Path(log_path)

        # Create parent directory if it doesn't exist
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create file if it doesn't exist
        if not self.log_path.exists():
            self.log_path.touch()

    def log_attempt(
        self,
        video_id: str,
        action: str,
        reason: str | None = None,
        duration: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a download attempt.

        Args:
            video_id: YouTube video ID or manual file identifier
            action: Action taken (e.g., 'download', 'skip', 'fail', 'manual_add')
            reason: Reason for the action (e.g., 'success', 'duplicate', 'error')
            duration: Duration of the action in seconds
            metadata: Additional metadata to include in the log entry
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "video_id": video_id,
            "action": action,
            "reason": reason,
            "duration": duration,
        }

        # Add metadata if provided
        if metadata:
            entry.update(metadata)

        # Append to log file
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to download log: {e}")

    def log_download_success(
        self,
        video_id: str,
        duration: float,
        file_path: str | None = None,
    ) -> None:
        """Log a successful download.

        Args:
            video_id: YouTube video ID
            duration: Download duration in seconds
            file_path: Path to the downloaded file
        """
        metadata = {"file_path": file_path} if file_path else None
        self.log_attempt(
            video_id=video_id,
            action="download",
            reason="success",
            duration=duration,
            metadata=metadata,
        )

    def log_download_failed(
        self,
        video_id: str,
        duration: float,
        error: str,
    ) -> None:
        """Log a failed download.

        Args:
            video_id: YouTube video ID
            duration: Time spent attempting the download in seconds
            error: Error message
        """
        self.log_attempt(
            video_id=video_id,
            action="download",
            reason="failed",
            duration=duration,
            metadata={"error": error},
        )

    def log_download_skipped(
        self,
        video_id: str,
        reason: str,
    ) -> None:
        """Log a skipped download.

        Args:
            video_id: YouTube video ID
            reason: Reason for skipping (e.g., 'duplicate', 'max_reached')
        """
        self.log_attempt(
            video_id=video_id,
            action="skip",
            reason=reason,
            duration=None,
        )

    def log_manual_addition(
        self,
        video_id: str,
        file_path: str,
        title: str,
    ) -> None:
        """Log a manual file addition.

        Args:
            video_id: Generated manual video ID
            file_path: Path to the manually added file
            title: Title of the manually added session
        """
        self.log_attempt(
            video_id=video_id,
            action="manual_add",
            reason="success",
            duration=None,
            metadata={"file_path": file_path, "title": title},
        )
