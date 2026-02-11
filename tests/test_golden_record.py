"""Tests for Layer 0 — Golden Record.

Covers: data model validation, alias resolution, collision detection.
See Issues #1 through #5.
"""

from pathlib import Path

from graphhansard.golden_record.models import GoldenRecord, MPNode


GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


class TestGoldenRecordSchema:
    """Validate mps.json against Pydantic schemas."""

    def test_golden_record_loads(self):
        """mps.json loads and validates against the GoldenRecord schema."""
        assert GOLDEN_RECORD_PATH.exists(), f"mps.json not found at {GOLDEN_RECORD_PATH}"
        data = GOLDEN_RECORD_PATH.read_text(encoding="utf-8")
        record = GoldenRecord.model_validate_json(data)
        assert len(record.mps) == 39, f"Expected 39 MPs, got {len(record.mps)}"

    def test_all_mps_have_node_ids(self):
        """Every MP has a unique, non-empty node_id."""
        data = GOLDEN_RECORD_PATH.read_text(encoding="utf-8")
        record = GoldenRecord.model_validate_json(data)
        node_ids = [mp.node_id for mp in record.mps]
        assert len(node_ids) == len(set(node_ids)), "Duplicate node_ids found"
        assert all(nid for nid in node_ids), "Empty node_id found"

    def test_all_mps_have_aliases(self):
        """Every MP has at least one alias."""
        data = GOLDEN_RECORD_PATH.read_text(encoding="utf-8")
        record = GoldenRecord.model_validate_json(data)
        for mp in record.mps:
            assert len(mp.aliases) > 0, f"{mp.node_id} has no aliases"

    def test_speaker_is_control_node(self):
        """The Speaker of the House has node_type 'control'."""
        data = GOLDEN_RECORD_PATH.read_text(encoding="utf-8")
        record = GoldenRecord.model_validate_json(data)
        speaker = next((mp for mp in record.mps if mp.node_id == "mp_deveaux_patricia"), None)
        assert speaker is not None, "Speaker not found"
        assert speaker.node_type == "control"

    def test_party_composition(self):
        """Party composition matches expected: 32 PLP, 6 FNM, 1 COI."""
        data = GOLDEN_RECORD_PATH.read_text(encoding="utf-8")
        record = GoldenRecord.model_validate_json(data)
        parties = {}
        for mp in record.mps:
            parties[mp.party] = parties.get(mp.party, 0) + 1
        assert parties.get("PLP", 0) == 32
        assert parties.get("FNM", 0) == 6
        assert parties.get("COI", 0) == 1
