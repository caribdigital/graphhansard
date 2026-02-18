#!/usr/bin/env python3
"""Fetch session metadata from YouTube videos using yt-dlp.

This helper script extracts metadata (upload date, title) from YouTube videos
and generates a JSON file compatible with batch_transcribe.py.

Usage:
    # From list of URLs in a text file
    python scripts/fetch_session_metadata.py urls.txt --output sessions.json

    # From command-line URLs
    python scripts/fetch_session_metadata.py --urls https://youtube.com/watch?v=7cuPpo7ko78 \
                                                  https://youtube.com/watch?v=Y--YlPwcI8o \
                                              --output sessions.json

    # With custom date parsing
    python scripts/fetch_session_metadata.py urls.txt --output sessions.json --parse-title-date

Input URL file format (urls.txt):
    https://www.youtube.com/watch?v=7cuPpo7ko78
    https://www.youtube.com/watch?v=Y--YlPwcI8o
    # Comments are ignored

Output JSON format:
    {
      "7cuPpo7ko78": {
        "date": "2026-01-28",
        "title": "House of Assembly 28 Jan 2026 Morning"
      },
      "Y--YlPwcI8o": {
        "date": "2026-02-04",
        "title": "House of Assembly 4 Feb 2026 Morning"
      }
    }

Requirements:
    - pip install yt-dlp
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL.

    Args:
        url: YouTube URL

    Returns:
        Video ID or None if not found
    """
    # Handle different YouTube URL formats
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If no pattern matches, check if it's already a video ID
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url):
        return url

    return None


def fetch_youtube_metadata(video_id: str) -> dict[str, Any] | None:
    """Fetch metadata for a YouTube video using yt-dlp.

    Args:
        video_id: YouTube video ID

    Returns:
        Dictionary with video metadata or None if failed
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        # Run yt-dlp to get metadata
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--skip-download", url],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )

        metadata = json.loads(result.stdout)
        return metadata

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout fetching metadata for {video_id}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp failed for {video_id}: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from yt-dlp for {video_id}: {e}")
        return None
    except FileNotFoundError:
        logger.error("yt-dlp not found. Install with: pip install yt-dlp")
        sys.exit(1)


def parse_date_from_title(title: str) -> str | None:
    """Attempt to parse a date from the video title.

    Args:
        title: Video title

    Returns:
        ISO 8601 date string (YYYY-MM-DD) or None if not found
    """
    # Common date patterns in parliamentary session titles
    patterns = [
        # "28 Jan 2026", "4 Feb 2026"
        r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})",
        # "2026-01-28", "2026-02-04"
        r"(\d{4})-(\d{2})-(\d{2})",
        # "January 28, 2026"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})",
    ]

    month_map = {
        "jan": "01", "january": "01",
        "feb": "02", "february": "02",
        "mar": "03", "march": "03",
        "apr": "04", "april": "04",
        "may": "05",
        "jun": "06", "june": "06",
        "jul": "07", "july": "07",
        "aug": "08", "august": "08",
        "sep": "09", "september": "09",
        "oct": "10", "october": "10",
        "nov": "11", "november": "11",
        "dec": "12", "december": "12",
    }

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            groups = match.groups()

            # Pattern 1: "28 Jan 2026"
            if len(groups) == 3 and groups[1].lower() in month_map:
                day, month, year = groups
                month_num = month_map[month.lower()]
                try:
                    return f"{year}-{month_num}-{int(day):02d}"
                except ValueError:
                    continue

            # Pattern 2: "2026-01-28"
            elif len(groups) == 3 and groups[0].isdigit() and len(groups[0]) == 4:
                year, month, day = groups
                try:
                    datetime(int(year), int(month), int(day))
                    return f"{year}-{month}-{day}"
                except ValueError:
                    continue

            # Pattern 3: "January 28, 2026"
            elif len(groups) == 3 and groups[0].lower() in month_map:
                month, day, year = groups
                month_num = month_map[month.lower()]
                try:
                    return f"{year}-{month_num}-{int(day):02d}"
                except ValueError:
                    continue

    return None


def convert_upload_date(upload_date: str) -> str:
    """Convert yt-dlp upload_date (YYYYMMDD) to ISO 8601 (YYYY-MM-DD).

    Args:
        upload_date: Upload date in YYYYMMDD format

    Returns:
        ISO 8601 date string (YYYY-MM-DD)
    """
    if len(upload_date) != 8:
        raise ValueError(f"Invalid upload_date format: {upload_date}")

    year = upload_date[:4]
    month = upload_date[4:6]
    day = upload_date[6:8]

    # Validate date
    datetime(int(year), int(month), int(day))

    return f"{year}-{month}-{day}"


def process_video(
    video_id: str,
    parse_title_date: bool = False,
) -> dict[str, str] | None:
    """Process a single video and extract session metadata.

    Args:
        video_id: YouTube video ID
        parse_title_date: Whether to attempt parsing date from title

    Returns:
        Dictionary with 'date' and 'title' keys, or None if failed
    """
    logger.info(f"Fetching metadata for: {video_id}")

    metadata = fetch_youtube_metadata(video_id)
    if not metadata:
        return None

    title = metadata.get("title", f"Session {video_id}")
    upload_date_raw = metadata.get("upload_date")

    # Determine session date
    session_date = None

    # Try parsing from title first if requested
    if parse_title_date:
        session_date = parse_date_from_title(title)
        if session_date:
            logger.info(f"  Parsed date from title: {session_date}")

    # Fall back to upload date
    if not session_date and upload_date_raw:
        try:
            session_date = convert_upload_date(upload_date_raw)
            logger.info(f"  Using upload date: {session_date}")
        except ValueError as e:
            logger.warning(f"  Invalid upload_date: {e}")

    if not session_date:
        logger.warning(f"  Could not determine date for {video_id}")
        return None

    logger.info(f"  Title: {title}")

    return {
        "date": session_date,
        "title": title,
    }


def load_urls_from_file(file_path: Path) -> list[str]:
    """Load YouTube URLs from a text file.

    Args:
        file_path: Path to text file containing URLs (one per line)

    Returns:
        List of YouTube URLs
    """
    urls = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            urls.append(line)

    logger.info(f"Loaded {len(urls)} URLs from {file_path}")
    return urls


def main():
    """Main entry point for metadata fetcher."""
    parser = argparse.ArgumentParser(
        description="Fetch session metadata from YouTube videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input sources (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "url_file",
        nargs="?",
        help="Text file containing YouTube URLs (one per line)",
    )
    input_group.add_argument(
        "--urls",
        nargs="+",
        help="One or more YouTube URLs or video IDs",
    )

    # Optional arguments
    parser.add_argument(
        "--output",
        "-o",
        default="sessions.json",
        help="Output JSON file (default: sessions.json)",
    )
    parser.add_argument(
        "--parse-title-date",
        action="store_true",
        help="Attempt to parse date from video title (in addition to upload date)",
    )

    args = parser.parse_args()

    # Collect URLs
    urls = []
    if args.url_file:
        url_file = Path(args.url_file)
        if not url_file.exists():
            logger.error(f"URL file not found: {url_file}")
            sys.exit(1)
        urls = load_urls_from_file(url_file)
    elif args.urls:
        urls = args.urls

    if not urls:
        logger.error("No URLs provided")
        sys.exit(1)

    # Extract video IDs
    video_ids = []
    for url in urls:
        video_id = extract_video_id(url)
        if video_id:
            video_ids.append(video_id)
        else:
            logger.warning(f"Could not extract video ID from: {url}")

    if not video_ids:
        logger.error("No valid video IDs found")
        sys.exit(1)

    logger.info(f"Processing {len(video_ids)} videos...")

    # Process videos
    session_metadata = {}
    for video_id in video_ids:
        meta = process_video(video_id, parse_title_date=args.parse_title_date)
        if meta:
            session_metadata[video_id] = meta
        else:
            logger.warning(f"Skipping {video_id} due to errors")

    # Save metadata
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(session_metadata, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*70}")
    logger.info("Metadata Extraction Complete")
    logger.info(f"{'='*70}")
    logger.info(f"Total videos: {len(video_ids)}")
    logger.info(f"Successful: {len(session_metadata)}")
    logger.info(f"Failed: {len(video_ids) - len(session_metadata)}")
    logger.info(f"Output saved to: {output_path}")

    # Exit with error if no metadata was extracted
    if not session_metadata:
        sys.exit(1)


if __name__ == "__main__":
    main()
