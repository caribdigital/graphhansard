"""Data export utilities for the Golden Record.

Implements GR-10: Export the full record in JSON and CSV formats.

Exports include:
1. Canonical JSON format (mps.json as-is)
2. Flattened CSV with one row per MP
3. Inverted alias index as JSON

All exports include metadata headers (version, date, parliament).
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import GoldenRecord


class GoldenRecordExporter:
    """Export the Golden Record in multiple formats with metadata."""

    def __init__(self, golden_record_path: str):
        """Initialize the exporter.

        Args:
            golden_record_path: Path to mps.json
        """
        self.golden_record_path = Path(golden_record_path)

        # Load the golden record
        data = self.golden_record_path.read_text(encoding="utf-8")
        self.golden_record = GoldenRecord.model_validate_json(data)

    def export_json(
        self, output_path: str, include_metadata_header: bool = True
    ) -> None:
        """Export the Golden Record as JSON (canonical format).

        Args:
            output_path: Path to save the JSON file
            include_metadata_header: If True, includes export metadata at top level
        """
        # Use validated model data for consistency
        data = json.loads(self.golden_record.model_dump_json())

        if include_metadata_header:
            export_data = {
                "export_metadata": {
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "export_format": "json",
                    "source_file": str(self.golden_record_path.name),
                    "golden_record_version": self.golden_record.metadata.version,
                    "disclaimer": "Network metrics are descriptive statistics derived from parliamentary proceedings. They do not imply wrongdoing, incompetence, or endorsement. See methodology documentation for limitations.",
                },
                "golden_record": data,
            }
        else:
            export_data = data

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

    def export_csv(self, output_path: str) -> None:
        """Export the Golden Record as a flattened CSV (one row per MP).

        CSV columns include:
        - Core MP attributes (node_id, full_name, common_name, etc.)
        - Current portfolio (if any)
        - Total alias count
        - Sample aliases (space-separated, first 5)

        Args:
            output_path: Path to save the CSV file
        """
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)

            # Write metadata header as comments (CSV-compatible)
            writer.writerow([
                f"# Golden Record Export - {self.golden_record.metadata.parliament}"
            ])
            writer.writerow([f"# Version: {self.golden_record.metadata.version}"])
            writer.writerow([
                f"# Exported: {datetime.now(timezone.utc).isoformat()}"
            ])
            writer.writerow([f"# Total MPs: {len(self.golden_record.mps)}"])
            writer.writerow([])  # Blank line
            # NF-18: Disclaimer (written as plain text with # prefix to avoid CSV quoting)
            f.write("# DISCLAIMER: Network metrics are descriptive statistics derived from parliamentary proceedings.\n")
            f.write("# They do not imply wrongdoing, incompetence, or endorsement.\n")
            f.write("# See methodology documentation for limitations.\n")
            writer.writerow([])  # Blank line

            # Write header row
            writer.writerow([
                "node_id",
                "full_name",
                "common_name",
                "party",
                "constituency",
                "is_cabinet",
                "is_opposition_frontbench",
                "gender",
                "node_type",
                "seat_status",
                "current_portfolio",
                "total_aliases",
                "sample_aliases",
            ])

            # Write data rows
            for mp in self.golden_record.mps:
                # Get current portfolio (end_date is None)
                current_portfolio = None
                for p in mp.portfolios:
                    if p.end_date is None:
                        current_portfolio = p.short_title
                        break

                # Get first 5 aliases as sample
                all_aliases = mp.all_aliases
                sample_aliases = " | ".join(all_aliases[:5])

                writer.writerow([
                    mp.node_id,
                    mp.full_name,
                    mp.common_name,
                    mp.party.value,
                    mp.constituency,
                    mp.is_cabinet,
                    mp.is_opposition_frontbench,
                    mp.gender.value,
                    mp.node_type.value,
                    mp.seat_status.value,
                    current_portfolio or "",
                    len(all_aliases),
                    sample_aliases,
                ])

    def export_alias_index(self, output_path: str) -> None:
        """Export the inverted alias index with metadata.

        The alias index maps normalized aliases to node IDs.

        Args:
            output_path: Path to save the JSON file
        """
        # Build inverted index
        alias_index: dict[str, list[str]] = {}

        for mp in self.golden_record.mps:
            for alias in mp.all_aliases:
                normalized = alias.strip().lower()
                if normalized not in alias_index:
                    alias_index[normalized] = []
                if mp.node_id not in alias_index[normalized]:
                    alias_index[normalized].append(mp.node_id)

        # Count statistics
        total_aliases = len(alias_index)
        collisions = {k: v for k, v in alias_index.items() if len(v) > 1}

        # Build export structure
        export_data = {
            "metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "export_format": "alias_index",
                "golden_record_version": self.golden_record.metadata.version,
                "parliament": self.golden_record.metadata.parliament,
                "parliament_start": self.golden_record.metadata.parliament_start,
                "total_aliases": total_aliases,
                "alias_collisions": len(collisions),
            },
            "alias_index": alias_index,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

    def export_all(
        self, output_dir: str, prefix: str = "golden_record"
    ) -> dict[str, str]:
        """Export all formats to a directory.

        Args:
            output_dir: Directory to save exports
            prefix: Filename prefix for exports

        Returns:
            Dictionary mapping format names to output file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate timestamp for unique filenames
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        exports = {}

        # Export JSON
        json_path = output_path / f"{prefix}_{timestamp}.json"
        self.export_json(str(json_path))
        exports["json"] = str(json_path)

        # Export CSV
        csv_path = output_path / f"{prefix}_{timestamp}.csv"
        self.export_csv(str(csv_path))
        exports["csv"] = str(csv_path)

        # Export alias index
        alias_index_path = output_path / f"{prefix}_alias_index_{timestamp}.json"
        self.export_alias_index(str(alias_index_path))
        exports["alias_index"] = str(alias_index_path)

        return exports
