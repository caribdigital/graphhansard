"""Tests for GR-7 (Speaker Control Node) and GR-8 (Temporal Versioning).

Validates edge semantic types, procedural edge handling, and parliament term tracking.
"""

from pathlib import Path

from graphhansard.brain.graph_builder import (
    EdgeRecord,
    EdgeSemanticType,
    SessionGraph,
)
from graphhansard.golden_record.models import GoldenRecord, NodeType

GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


def _load_record() -> GoldenRecord:
    """Load and validate the Golden Record from mps.json."""
    data = GOLDEN_RECORD_PATH.read_text(encoding="utf-8")
    return GoldenRecord.model_validate_json(data)


class TestSpeakerControlNode:
    """Test GR-7: Speaker as control node with distinct edge semantics."""

    def test_speaker_has_control_node_type(self):
        """GR-7: Speaker (Patricia Deveaux) has node_type: control."""
        record = _load_record()
        speaker = next(
            (mp for mp in record.mps if mp.node_id == "mp_deveaux_patricia"), None
        )
        assert speaker is not None, "Speaker Patricia Deveaux not found"
        assert speaker.node_type == NodeType.CONTROL, (
            f"Speaker should have node_type=control, got {speaker.node_type}"
        )

    def test_edge_semantic_types_defined(self):
        """GR-7: EdgeSemanticType enum includes all required categories."""
        assert EdgeSemanticType.RECOGNIZING.value == "recognizing"
        assert EdgeSemanticType.ADMONISHING.value == "admonishing"
        assert EdgeSemanticType.CUTTING_OFF.value == "cutting_off"
        assert EdgeSemanticType.RULING.value == "ruling"
        assert EdgeSemanticType.MENTION.value == "mention"

    def test_edge_record_has_semantic_type(self):
        """GR-7: EdgeRecord supports semantic_type field."""
        edge = EdgeRecord(
            source_node_id="mp_deveaux_patricia",
            target_node_id="mp_davis_brave",
            total_mentions=1,
            semantic_type=EdgeSemanticType.RECOGNIZING,
        )
        assert edge.semantic_type == EdgeSemanticType.RECOGNIZING

    def test_edge_record_has_procedural_flag(self):
        """GR-7: EdgeRecord supports is_procedural field."""
        edge = EdgeRecord(
            source_node_id="mp_deveaux_patricia",
            target_node_id="mp_davis_brave",
            total_mentions=1,
            is_procedural=True,
        )
        assert edge.is_procedural is True

    def test_edge_record_defaults_to_non_procedural(self):
        """GR-7: EdgeRecord defaults to is_procedural=False."""
        edge = EdgeRecord(
            source_node_id="mp_davis_brave",
            target_node_id="mp_cooper_chester",
            total_mentions=1,
        )
        assert edge.is_procedural is False
        assert edge.semantic_type == EdgeSemanticType.MENTION

    def test_session_graph_filters_procedural_edges(self):
        """GR-7: SessionGraph.political_edges() excludes procedural edges."""
        edges = [
            EdgeRecord(
                source_node_id="mp_davis_brave",
                target_node_id="mp_cooper_chester",
                total_mentions=5,
                is_procedural=False,
            ),
            EdgeRecord(
                source_node_id="mp_deveaux_patricia",
                target_node_id="mp_davis_brave",
                total_mentions=2,
                is_procedural=True,
                semantic_type=EdgeSemanticType.RECOGNIZING,
            ),
            EdgeRecord(
                source_node_id="mp_cooper_chester",
                target_node_id="mp_mitchell_fred",
                total_mentions=3,
                is_procedural=False,
            ),
        ]

        graph = SessionGraph(
            session_id="test_session",
            date="2024-01-15",
            graph_file="test.graphml",
            edges=edges,
        )

        political = graph.political_edges()
        assert len(political) == 2, f"Expected 2 political edges, got {len(political)}"
        assert all(not e.is_procedural for e in political)

        procedural = graph.procedural_edges()
        msg = f"Expected 1 procedural edge, got {len(procedural)}"
        assert len(procedural) == 1, msg
        assert all(e.is_procedural for e in procedural)
        assert procedural[0].semantic_type == EdgeSemanticType.RECOGNIZING

    def test_speaker_edge_semantic_types(self):
        """GR-7: All four Speaker edge semantic types can be instantiated."""
        recognizing = EdgeRecord(
            source_node_id="mp_deveaux_patricia",
            target_node_id="mp_davis_brave",
            total_mentions=1,
            is_procedural=True,
            semantic_type=EdgeSemanticType.RECOGNIZING,
        )
        assert recognizing.semantic_type == EdgeSemanticType.RECOGNIZING

        admonishing = EdgeRecord(
            source_node_id="mp_deveaux_patricia",
            target_node_id="mp_pintard_michael",
            total_mentions=1,
            is_procedural=True,
            semantic_type=EdgeSemanticType.ADMONISHING,
        )
        assert admonishing.semantic_type == EdgeSemanticType.ADMONISHING

        cutting_off = EdgeRecord(
            source_node_id="mp_deveaux_patricia",
            target_node_id="mp_wilchcombe_ivan",
            total_mentions=1,
            is_procedural=True,
            semantic_type=EdgeSemanticType.CUTTING_OFF,
        )
        assert cutting_off.semantic_type == EdgeSemanticType.CUTTING_OFF

        ruling = EdgeRecord(
            source_node_id="mp_deveaux_patricia",
            target_node_id="mp_symonette_michael",
            total_mentions=1,
            is_procedural=True,
            semantic_type=EdgeSemanticType.RULING,
        )
        assert ruling.semantic_type == EdgeSemanticType.RULING


class TestTemporalVersioning:
    """Test GR-8: Temporal versioning by parliamentary term."""

    def test_golden_record_has_parliament_field(self):
        """GR-8: GoldenRecordMetadata has parliament field."""
        record = _load_record()
        assert record.metadata.parliament is not None
        assert "14th Parliament" in record.metadata.parliament

    def test_mpnode_has_parliament_terms_field(self):
        """GR-8: MPNode has parliament_terms field for tracking across terms."""
        record = _load_record()
        # All MPs should have the parliament_terms field (even if empty list by default)
        for mp in record.mps:
            assert hasattr(mp, "parliament_terms"), (
                f"{mp.node_id} missing parliament_terms field"
            )
            # Field should be a list
            assert isinstance(mp.parliament_terms, list), (
                f"{mp.node_id}.parliament_terms should be a list"
            )

    def test_parliament_terms_field_optional(self):
        """GR-8: parliament_terms field defaults to empty list (optional)."""
        record = _load_record()
        # Since we haven't populated parliament_terms in the Golden Record yet,
        # all MPs should have empty lists by default
        for mp in record.mps:
            # The field exists and defaults to []
            assert isinstance(mp.parliament_terms, list)

    def test_stable_node_id_across_terms(self):
        """GR-8: node_id design allows tracking MPs across terms.

        Example: Brave Davis has served in multiple parliaments
        (13th, 14th). The node_id 'mp_davis_brave' remains stable
        across terms.
        """
        record = _load_record()
        brave = next(mp for mp in record.mps if mp.node_id == "mp_davis_brave")

        # Verify the node_id is stable (not parliament-specific)
        assert "mp_davis_brave" == brave.node_id

        # Verify first_elected predates current parliament
        # Brave was first elected in 1992, current parliament started 2021
        assert brave.first_elected == "1992"

        # The parliament_terms field can track which parliaments he served in
        # (This would be populated in future versions of the Golden Record)
        assert hasattr(brave, "parliament_terms")
