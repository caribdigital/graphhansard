"""CLI interface for the Miner pipeline.

Entry point: python -m graphhansard.miner.cli
See SRD §7.2 (MN-12) for specification.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point for the Miner."""
    parser = argparse.ArgumentParser(
        prog="graphhansard-miner",
        description="GraphHansard Audio Ingestion Pipeline",
    )
    subparsers = parser.add_subparsers(dest="command")

    # scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Download sessions from YouTube")
    scrape_parser.add_argument(
        "--full", action="store_true", help="Full scrape (all available sessions)"
    )
    scrape_parser.add_argument(
        "--incremental", action="store_true", help="Incremental scrape (new sessions only)"
    )
    scrape_parser.add_argument("--cookies", type=str, help="Path to cookies file")
    scrape_parser.add_argument("--proxy-list", type=str, help="Path to proxy list file")

    # status command
    subparsers.add_parser("status", help="Show download statistics")

    # add-manual command
    manual_parser = subparsers.add_parser("add-manual", help="Add a non-YouTube audio file")
    manual_parser.add_argument("file", type=str, help="Path to audio file")
    manual_parser.add_argument("--date", type=str, required=True, help="Session date (YYYY-MM-DD)")
    manual_parser.add_argument("--title", type=str, required=True, help="Session title")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    # TODO: Implement command handlers — see Issues #6, #7, #8
    print(f"Command '{args.command}' is not yet implemented.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
