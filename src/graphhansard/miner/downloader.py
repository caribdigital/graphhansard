"""YouTube audio downloader using yt-dlp.

Handles session discovery, audio-only download, cookie authentication,
rate limiting, and resumable downloads per SRD §7.2 (MN-1 through MN-5).
"""

from __future__ import annotations


class SessionDownloader:
    """Downloads House of Assembly audio from YouTube.

    See SRD §7.2 and §7.3 for specification.
    """

    def __init__(
        self,
        archive_dir: str = "archive",
        cookies_path: str | None = None,
        sleep_interval: int = 5,
        max_downloads: int = 50,
    ):
        raise NotImplementedError("SessionDownloader not yet implemented — see Issue #6")

    def discover_sessions(self, channel_url: str) -> list[dict]:
        """Discover all House of Assembly videos from a YouTube channel."""
        raise NotImplementedError

    def download_session(self, video_url: str) -> dict:
        """Download audio-only stream for a single session."""
        raise NotImplementedError

    def run_full_scrape(self, channel_url: str) -> None:
        """Discover and download all available sessions."""
        raise NotImplementedError

    def run_incremental_scrape(self, channel_url: str) -> None:
        """Download only sessions not already in the archive."""
        raise NotImplementedError
