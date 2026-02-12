"""CLI interface for the Miner pipeline.

Entry point: python -m graphhansard.miner.cli
See SRD §7.2 (MN-12) for specification.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from graphhansard.miner.catalogue import AudioCatalogue, DownloadStatus, SessionAudio
from graphhansard.miner.downloader import SessionDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def handle_scrape(args: argparse.Namespace) -> int:
    """Handle the scrape command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Default channel URL for Bahamas Parliament
    channel_url = "https://www.youtube.com/@BahamasParliament/videos"

    # Initialize downloader
    downloader = SessionDownloader(
        archive_dir="archive",
        cookies_path=args.cookies,
        sleep_interval=5,
        max_downloads=50,
        proxy_list_path=args.proxy_list,
    )

    try:
        if args.full:
            logger.info("Starting full scrape")
            downloader.run_full_scrape(channel_url)
        elif args.incremental:
            logger.info("Starting incremental scrape")
            downloader.run_incremental_scrape(channel_url)
        else:
            # Default to incremental
            logger.info("Starting incremental scrape (default)")
            downloader.run_incremental_scrape(channel_url)

        logger.info("Scrape completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Scrape failed: {e}", exc_info=True)
        return 1


def handle_status(args: argparse.Namespace) -> int:
    """Handle the status command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        catalogue_path = Path("archive/catalogue.json")

        if not catalogue_path.exists():
            print("No catalogue found. Run 'scrape' command first.")
            return 0

        catalogue = AudioCatalogue(str(catalogue_path))
        entries = catalogue.get_all_entries()

        if not entries:
            print("Catalogue is empty.")
            return 0

        # Calculate statistics
        total = len(entries)
        downloaded = sum(
            1 for e in entries if e.status == DownloadStatus.DOWNLOADED
        )
        failed = sum(1 for e in entries if e.status == DownloadStatus.FAILED)
        skipped = sum(
            1 for e in entries if e.status == DownloadStatus.SKIPPED_DUPLICATE
        )

        total_duration = sum(
            e.duration_seconds
            for e in entries
            if e.status == DownloadStatus.DOWNLOADED
        )
        total_duration_hours = total_duration / 3600

        # Print statistics
        print(f"\n{'='*60}")
        print("GraphHansard Miner — Download Statistics")
        print(f"{'='*60}")
        print(f"\nTotal entries:        {total}")
        print(f"  Downloaded:         {downloaded}")
        print(f"  Failed:             {failed}")
        print(f"  Skipped/Duplicate:  {skipped}")
        print(f"\nTotal audio duration: {total_duration_hours:.2f} hours")
        print(f"\nCatalogue location:   {catalogue_path.absolute()}")
        print(f"{'='*60}\n")

        return 0

    except Exception as e:
        logger.error(f"Status command failed: {e}", exc_info=True)
        return 1


def handle_add_manual(args: argparse.Namespace) -> int:
    """Handle the add-manual command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        import hashlib

        from graphhansard.miner.download_logger import DownloadLogger

        file_path = Path(args.file)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return 1

        # Parse date
        try:
            session_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
            return 1

        # Calculate file hash
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # Get file info
        file_ext = file_path.suffix.lstrip(".")

        # Create manual entry with a synthetic video ID
        video_id = f"manual_{file_hash[:12]}"

        entry = SessionAudio(
            video_id=video_id,
            title=args.title,
            parsed_date=session_date,
            upload_date=session_date,
            duration_seconds=0,  # Unknown for manual files
            audio_format=file_ext,
            audio_bitrate_kbps=0,  # Unknown for manual files
            file_path=str(file_path),
            file_hash_sha256=file_hash,
            download_timestamp=datetime.now(timezone.utc),
            source_url=f"manual:{file_path}",
            status=DownloadStatus.DOWNLOADED,
            notes="Manually added via CLI",
        )

        # Add to catalogue
        catalogue = AudioCatalogue("archive/catalogue.json")
        catalogue.add_entry(entry)

        # Log the manual addition
        download_logger = DownloadLogger("archive/download_log.jsonl")
        download_logger.log_manual_addition(
            video_id=video_id,
            file_path=str(file_path),
            title=args.title,
        )

        logger.info(f"Successfully added manual entry: {args.title}")
        print(f"Added: {args.title} ({video_id})")

        return 0

    except Exception as e:
        logger.error(f"Add-manual command failed: {e}", exc_info=True)
        return 1


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point for the Miner."""
    parser = argparse.ArgumentParser(
        prog="graphhansard-miner",
        description="GraphHansard Audio Ingestion Pipeline",
    )
    subparsers = parser.add_subparsers(dest="command")

    # scrape command
    scrape_parser = subparsers.add_parser(
        "scrape", help="Download sessions from YouTube"
    )
    scrape_parser.add_argument(
        "--full", action="store_true", help="Full scrape (all available sessions)"
    )
    scrape_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Incremental scrape (new sessions only)",
    )
    scrape_parser.add_argument("--cookies", type=str, help="Path to cookies file")
    scrape_parser.add_argument(
        "--proxy-list", type=str, help="Path to proxy list file"
    )

    # status command
    subparsers.add_parser("status", help="Show download statistics")

    # add-manual command
    manual_parser = subparsers.add_parser(
        "add-manual", help="Add a non-YouTube audio file"
    )
    manual_parser.add_argument("file", type=str, help="Path to audio file")
    manual_parser.add_argument(
        "--date", type=str, required=True, help="Session date (YYYY-MM-DD)"
    )
    manual_parser.add_argument(
        "--title", type=str, required=True, help="Session title"
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    # Dispatch to command handlers
    if args.command == "scrape":
        return handle_scrape(args)
    elif args.command == "status":
        return handle_status(args)
    elif args.command == "add-manual":
        return handle_add_manual(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
