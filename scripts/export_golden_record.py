#!/usr/bin/env python3
"""Export the Golden Record in multiple formats.

Implements GR-10: Export the full record in JSON and CSV formats.

Usage:
    # Export all formats to exports/ directory
    python scripts/export_golden_record.py

    # Export specific format
    python scripts/export_golden_record.py --format json
    python scripts/export_golden_record.py --format csv
    python scripts/export_golden_record.py --format alias_index

    # Custom output directory
    python scripts/export_golden_record.py --output-dir /path/to/exports
"""

import argparse
from pathlib import Path

from graphhansard.golden_record.exporter import GoldenRecordExporter


def main():
    """Export the Golden Record in specified formats."""
    parser = argparse.ArgumentParser(
        description="Export the Golden Record in multiple formats (GR-10)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv", "alias_index", "all"],
        default="all",
        help="Export format (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        default="exports",
        help="Output directory for exports (default: exports/)",
    )
    parser.add_argument(
        "--prefix",
        default="golden_record",
        help="Filename prefix for exports (default: golden_record)",
    )

    args = parser.parse_args()

    # Paths
    repo_root = Path(__file__).parent.parent
    golden_record_path = repo_root / "golden_record" / "mps.json"
    output_dir = Path(args.output_dir)

    # Create exporter
    print(f"Loading Golden Record from {golden_record_path}...")
    exporter = GoldenRecordExporter(str(golden_record_path))

    print(f"Golden Record Version: {exporter.golden_record.metadata.version}")
    print(f"Parliament: {exporter.golden_record.metadata.parliament}")
    print(f"Total MPs: {len(exporter.golden_record.mps)}")
    print()

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export based on format selection
    if args.format == "all":
        print("Exporting all formats...")
        exports = exporter.export_all(str(output_dir), args.prefix)
        print("\n✅ All exports completed:")
        for fmt, path in exports.items():
            print(f"  {fmt}: {path}")
    else:
        # Generate filename
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if args.format == "json":
            output_path = output_dir / f"{args.prefix}_{timestamp}.json"
            print(f"Exporting JSON to {output_path}...")
            exporter.export_json(str(output_path))
            print(f"✅ JSON export completed: {output_path}")

        elif args.format == "csv":
            output_path = output_dir / f"{args.prefix}_{timestamp}.csv"
            print(f"Exporting CSV to {output_path}...")
            exporter.export_csv(str(output_path))
            print(f"✅ CSV export completed: {output_path}")

        elif args.format == "alias_index":
            output_path = output_dir / f"{args.prefix}_alias_index_{timestamp}.json"
            print(f"Exporting alias index to {output_path}...")
            exporter.export_alias_index(str(output_path))
            print(f"✅ Alias index export completed: {output_path}")


if __name__ == "__main__":
    main()
