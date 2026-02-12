"""YouTube audio downloader using yt-dlp.

Handles session discovery, audio-only download, cookie authentication,
rate limiting, and resumable downloads per SRD §7.2 (MN-1 through MN-5).
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yt_dlp

from graphhansard.miner.catalogue import AudioCatalogue, DownloadStatus, SessionAudio

logger = logging.getLogger(__name__)


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
        """Initialize the SessionDownloader.

        Args:
            archive_dir: Directory to store downloaded audio files
            cookies_path: Optional path to Netscape-format cookies file
            sleep_interval: Seconds to wait between downloads (rate limiting)
            max_downloads: Maximum number of downloads per session
        """
        self.archive_dir = Path(archive_dir)
        self.cookies_path = cookies_path
        self.sleep_interval = sleep_interval
        self.max_downloads = max_downloads
        self.download_count = 0

        # Create archive directory if it doesn't exist
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Initialize catalogue
        catalogue_path = self.archive_dir / "catalogue.json"
        self.catalogue = AudioCatalogue(str(catalogue_path))

        # Download archive file for yt-dlp resumability
        self.download_archive_path = self.archive_dir / "download_archive.txt"

    def _get_ydl_opts(self, output_template: str | None = None) -> dict[str, Any]:
        """Get yt-dlp options.

        Args:
            output_template: Custom output template (optional)

        Returns:
            Dictionary of yt-dlp options
        """
        if output_template is None:
            output_template = str(
                self.archive_dir
                / "%(upload_date>%Y)s"
                / "%(upload_date)s"
                / "%(id)s.%(ext)s"
            )

        opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "opus",
                "preferredquality": "128",
            }],
            "outtmpl": output_template,
            "download_archive": str(self.download_archive_path),
            "quiet": False,
            "no_warnings": False,
            "extract_flat": False,
            "writeinfojson": True,
            "writethumbnail": False,
        }

        # Add cookies if provided
        if self.cookies_path:
            opts["cookiefile"] = self.cookies_path

        return opts

    def discover_sessions(self, channel_url: str) -> list[dict]:
        """Discover all House of Assembly videos from a YouTube channel.

        Args:
            channel_url: YouTube channel URL or playlist URL

        Returns:
            List of video metadata dictionaries
        """
        logger.info(f"Discovering videos from {channel_url}")

        opts = {
            "quiet": True,
            "extract_flat": True,
            "skip_download": True,
        }

        if self.cookies_path:
            opts["cookiefile"] = self.cookies_path

        videos = []
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(channel_url, download=False)

                # Handle both channel and playlist URLs
                if "entries" in info:
                    for entry in info["entries"]:
                        if entry:
                            videos.append({
                                "id": entry.get("id"),
                                "title": entry.get("title"),
                                "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                                "duration": entry.get("duration"),
                                "upload_date": entry.get("upload_date"),
                            })
                else:
                    # Single video
                    videos.append({
                        "id": info.get("id"),
                        "title": info.get("title"),
                        "url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={info.get('id')}",
                        "duration": info.get("duration"),
                        "upload_date": info.get("upload_date"),
                    })

            except Exception as e:
                logger.error(f"Error discovering sessions: {e}")
                raise

        logger.info(f"Discovered {len(videos)} videos")
        return videos

    def download_session(self, video_url: str) -> dict:
        """Download audio-only stream for a single session.

        Args:
            video_url: YouTube video URL

        Returns:
            Dictionary with download status and metadata
        """
        if self.download_count >= self.max_downloads:
            logger.warning(
                f"Max downloads ({self.max_downloads}) reached, "
                f"skipping {video_url}"
            )
            return {
                "status": "skipped_max_reached",
                "url": video_url,
            }

        logger.info(f"Downloading {video_url}")

        opts = self._get_ydl_opts()

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(video_url, download=True)

                # Get the actual downloaded file path
                if "requested_downloads" in info and info["requested_downloads"]:
                    filepath = info["requested_downloads"][0].get("filepath")
                else:
                    # Construct expected path from template
                    upload_date = info.get("upload_date", "unknown")
                    year = upload_date[:4] if len(upload_date) >= 4 else "unknown"
                    video_id = info.get("id", "unknown")
                    ext = "opus"  # Our preferred format
                    filepath = (
                        self.archive_dir / year / upload_date / f"{video_id}.{ext}"
                    )

                filepath = Path(filepath)

                # Calculate file hash if file exists
                file_hash = ""
                if filepath.exists():
                    with open(filepath, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()

                # Create catalogue entry
                upload_date_str = info.get("upload_date", "")
                upload_date_obj = None
                if upload_date_str:
                    try:
                        upload_date_obj = datetime.strptime(
                            upload_date_str, "%Y%m%d"
                        ).date()
                    except ValueError:
                        pass

                # Extract audio format info
                audio_format = "opus"
                audio_bitrate = 128

                if "requested_downloads" in info and info["requested_downloads"]:
                    req_dl = info["requested_downloads"][0]
                    audio_format = req_dl.get("ext", "opus")
                    audio_bitrate = req_dl.get("abr", 128) or 128

                entry = SessionAudio(
                    video_id=info.get("id", ""),
                    title=info.get("title", ""),
                    parsed_date=None,  # To be parsed later
                    upload_date=upload_date_obj or datetime.now(timezone.utc).date(),
                    duration_seconds=info.get("duration", 0) or 0,
                    audio_format=audio_format,
                    audio_bitrate_kbps=int(audio_bitrate),
                    file_path=(
                        str(filepath.relative_to(self.archive_dir))
                        if filepath.exists()
                        else str(filepath)
                    ),
                    file_hash_sha256=file_hash,
                    download_timestamp=datetime.now(timezone.utc),
                    source_url=info.get("webpage_url", video_url),
                    status=DownloadStatus.DOWNLOADED,
                    notes=None,
                )

                # Add to catalogue
                self.catalogue.add_entry(entry)

                self.download_count += 1

                # Rate limiting
                if self.download_count < self.max_downloads:
                    logger.info(
                        f"Sleeping for {self.sleep_interval} seconds "
                        f"(rate limiting)"
                    )
                    time.sleep(self.sleep_interval)

                return {
                    "status": "success",
                    "url": video_url,
                    "video_id": info.get("id"),
                    "filepath": str(filepath),
                }

        except Exception as e:
            logger.error(f"Error downloading {video_url}: {e}")

            # Extract video ID from URL without network call
            match = re.search(r'[?&]v=([^&]+)', video_url)
            video_id = match.group(1) if match else None

            # Record failure in catalogue
            if video_id:
                entry = SessionAudio(
                    video_id=video_id,
                    title="",
                    upload_date=datetime.now(timezone.utc).date(),
                    duration_seconds=0,
                    audio_format="",
                    audio_bitrate_kbps=0,
                    file_path="",
                    file_hash_sha256="",
                    download_timestamp=datetime.now(timezone.utc),
                    source_url=video_url,
                    status=DownloadStatus.FAILED,
                    notes=str(e),
                )
                self.catalogue.add_entry(entry)

            return {
                "status": "failed",
                "url": video_url,
                "error": str(e),
            }

    def run_full_scrape(self, channel_url: str) -> None:
        """Discover and download all available sessions.

        Args:
            channel_url: YouTube channel URL or playlist URL
        """
        logger.info(f"Starting full scrape of {channel_url}")

        videos = self.discover_sessions(channel_url)

        logger.info(f"Found {len(videos)} videos to process")

        for i, video in enumerate(videos, 1):
            if self.download_count >= self.max_downloads:
                logger.warning(
                    f"Reached max downloads limit ({self.max_downloads}), "
                    f"stopping"
                )
                break

            video_url = video.get("url")
            video_id = video.get("id")

            # Check if already downloaded
            if self.catalogue.is_duplicate(video_id):
                logger.info(
                    f"[{i}/{len(videos)}] Skipping {video_id} "
                    f"(already in catalogue)"
                )
                continue

            logger.info(f"[{i}/{len(videos)}] Processing {video_url}")
            result = self.download_session(video_url)
            logger.info(f"[{i}/{len(videos)}] Result: {result['status']}")

        logger.info(f"Full scrape complete. Downloaded {self.download_count} sessions")

    def run_incremental_scrape(self, channel_url: str) -> None:
        """Download only sessions not already in the archive.

        This uses yt-dlp's --download-archive feature for efficient resumability.

        Args:
            channel_url: YouTube channel URL or playlist URL
        """
        logger.info(f"Starting incremental scrape of {channel_url}")

        # For incremental scrape, yt-dlp will automatically skip videos
        # listed in the download archive file
        self.run_full_scrape(channel_url)
