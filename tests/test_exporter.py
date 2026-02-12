"""Tests for Golden Record export functionality (GR-10)."""

import csv
import json
from datetime import datetime
from pathlib import Path

import pytest

from graphhansard.golden_record.exporter import GoldenRecordExporter

GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


@pytest.fixture
def exporter():
    """Create a GoldenRecordExporter instance."""
    return GoldenRecordExporter(str(GOLDEN_RECORD_PATH))


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "exports"
    output_dir.mkdir()
    return output_dir


class TestJSONExport:
    """Test JSON export functionality."""

    def test_json_export_with_metadata_header(self, exporter, temp_output_dir):
        """JSON export includes metadata header."""
        output_path = temp_output_dir / "test_export.json"
        exporter.export_json(str(output_path), include_metadata_header=True)

        assert output_path.exists()

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check metadata header
        assert "export_metadata" in data
        assert "golden_record" in data
        assert data["export_metadata"]["export_format"] == "json"
        assert "exported_at" in data["export_metadata"]
        assert "golden_record_version" in data["export_metadata"]

        # Check golden record data
        assert "metadata" in data["golden_record"]
        assert "mps" in data["golden_record"]
        assert len(data["golden_record"]["mps"]) == 39

    def test_json_export_without_metadata_header(self, exporter, temp_output_dir):
        """JSON export without metadata header matches original structure."""
        output_path = temp_output_dir / "test_export_no_header.json"
        exporter.export_json(str(output_path), include_metadata_header=False)

        assert output_path.exists()

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Should have original structure
        assert "metadata" in data
        assert "mps" in data
        assert "export_metadata" not in data
        assert len(data["mps"]) == 39

    def test_json_export_preserves_structure(self, exporter, temp_output_dir):
        """JSON export preserves all MP fields."""
        output_path = temp_output_dir / "test_export.json"
        exporter.export_json(str(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check first MP has required fields
        first_mp = data["golden_record"]["mps"][0]
        assert "node_id" in first_mp
        assert "full_name" in first_mp
        assert "common_name" in first_mp
        assert "party" in first_mp
        assert "constituency" in first_mp
        assert "portfolios" in first_mp
        assert "aliases" in first_mp


class TestCSVExport:
    """Test CSV export functionality."""

    def test_csv_export_creates_file(self, exporter, temp_output_dir):
        """CSV export creates a valid file."""
        output_path = temp_output_dir / "test_export.csv"
        exporter.export_csv(str(output_path))

        assert output_path.exists()

    def test_csv_export_includes_metadata_header(self, exporter, temp_output_dir):
        """CSV export includes metadata in comment lines."""
        output_path = temp_output_dir / "test_export.csv"
        exporter.export_csv(str(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Check comment lines
        assert lines[0].startswith("# Golden Record Export")
        assert "# Version:" in lines[1]
        assert "# Exported:" in lines[2]
        assert "# Total MPs:" in lines[3]

    def test_csv_export_has_correct_headers(self, exporter, temp_output_dir):
        """CSV export has correct column headers."""
        output_path = temp_output_dir / "test_export.csv"
        exporter.export_csv(str(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Find header row (skip comment lines and blank line)
        header_row = None
        for row in rows:
            if row and not row[0].startswith("#"):
                header_row = row
                break

        assert header_row is not None
        expected_headers = [
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
        ]
        assert header_row == expected_headers

    def test_csv_export_has_all_mps(self, exporter, temp_output_dir):
        """CSV export includes all 39 MPs."""
        output_path = temp_output_dir / "test_export.csv"
        exporter.export_csv(str(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = [row for row in reader if row and not row[0].startswith("#")]

        # Should have header + 39 data rows
        assert len(rows) == 40  # 1 header + 39 MPs

    def test_csv_export_data_validity(self, exporter, temp_output_dir):
        """CSV export contains valid data."""
        output_path = temp_output_dir / "test_export.csv"
        exporter.export_csv(str(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            # Skip comment lines and blank lines
            reader = csv.DictReader(
                (row for row in f if row.strip() and not row.startswith("#")),
                skipinitialspace=True
            )
            rows = list(reader)

        assert len(rows) == 39

        # Check first MP
        first_mp = rows[0]
        assert first_mp["node_id"]
        assert first_mp["full_name"]
        assert first_mp["party"] in ["PLP", "FNM", "COI", "IND"]
        assert int(first_mp["total_aliases"]) > 0


class TestAliasIndexExport:
    """Test alias index export functionality."""

    def test_alias_index_export_creates_file(self, exporter, temp_output_dir):
        """Alias index export creates a valid file."""
        output_path = temp_output_dir / "test_alias_index.json"
        exporter.export_alias_index(str(output_path))

        assert output_path.exists()

    def test_alias_index_includes_metadata(self, exporter, temp_output_dir):
        """Alias index export includes metadata."""
        output_path = temp_output_dir / "test_alias_index.json"
        exporter.export_alias_index(str(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "metadata" in data
        assert "alias_index" in data
        assert data["metadata"]["export_format"] == "alias_index"
        assert "exported_at" in data["metadata"]
        assert "golden_record_version" in data["metadata"]
        assert "parliament" in data["metadata"]
        assert "total_aliases" in data["metadata"]
        assert "alias_collisions" in data["metadata"]

    def test_alias_index_has_correct_structure(self, exporter, temp_output_dir):
        """Alias index has correct structure (alias -> node_ids)."""
        output_path = temp_output_dir / "test_alias_index.json"
        exporter.export_alias_index(str(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        alias_index = data["alias_index"]

        # Check that all entries are normalized (lowercase)
        for alias in alias_index.keys():
            assert alias == alias.lower()

        # Check that values are lists of node_ids
        for node_ids in alias_index.values():
            assert isinstance(node_ids, list)
            assert len(node_ids) > 0
            assert all(isinstance(nid, str) for nid in node_ids)

    def test_alias_index_has_expected_size(self, exporter, temp_output_dir):
        """Alias index has expected number of aliases."""
        output_path = temp_output_dir / "test_alias_index.json"
        exporter.export_alias_index(str(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Should have at least 357 aliases as per SRD
        assert len(data["alias_index"]) >= 357
        assert data["metadata"]["total_aliases"] == len(data["alias_index"])

    def test_alias_index_detects_collisions(self, exporter, temp_output_dir):
        """Alias index correctly identifies collisions."""
        output_path = temp_output_dir / "test_alias_index.json"
        exporter.export_alias_index(str(output_path))

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        alias_index = data["alias_index"]

        # Count actual collisions
        collisions = {k: v for k, v in alias_index.items() if len(v) > 1}

        assert data["metadata"]["alias_collisions"] == len(collisions)
        assert len(collisions) >= 6  # Per SRD, there are 6 known collisions


class TestExportAll:
    """Test export_all functionality."""

    def test_export_all_creates_all_formats(self, exporter, temp_output_dir):
        """export_all creates JSON, CSV, and alias index files."""
        exports = exporter.export_all(str(temp_output_dir))

        assert "json" in exports
        assert "csv" in exports
        assert "alias_index" in exports

        # Check files exist
        assert Path(exports["json"]).exists()
        assert Path(exports["csv"]).exists()
        assert Path(exports["alias_index"]).exists()

    def test_export_all_with_custom_prefix(self, exporter, temp_output_dir):
        """export_all uses custom prefix for filenames."""
        exports = exporter.export_all(str(temp_output_dir), prefix="test")

        for path in exports.values():
            assert "test_" in Path(path).name

    def test_export_all_creates_output_dir(self, exporter, tmp_path):
        """export_all creates output directory if it doesn't exist."""
        output_dir = tmp_path / "new_exports"
        assert not output_dir.exists()

        exports = exporter.export_all(str(output_dir))

        assert output_dir.exists()
        assert len(exports) == 3
