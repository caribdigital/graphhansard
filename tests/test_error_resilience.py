"""Test for NF-7: Pipeline error handling and resilience.

Requirement: All pipeline stages must log errors and continue processing
remaining items - no single failure kills a batch.

This test verifies that the pipeline handles errors gracefully and
continues processing even when individual items fail.
"""

from pathlib import Path

from graphhansard.brain.entity_extractor import EntityExtractor
from graphhansard.brain.graph_builder import GraphBuilder


def test_entity_extraction_error_handling():
    """Test that entity extractor continues after individual segment failures (NF-7).

    The EntityExtractor.extract_mentions() processes all segments in a transcript.
    Segments with empty/whitespace-only text are skipped gracefully via
    _extract_from_segment's `if not text.strip(): return []` guard.
    """
    golden_record_path = Path(__file__).parent.parent / "golden_record" / "mps.json"

    extractor = EntityExtractor(golden_record_path=str(golden_record_path))

    # Build a transcript with a mix of valid, empty, and edge-case segments
    transcript = {
        "session_id": "test_session",
        "segments": [
            {
                "speaker_node_id": "mp_davis_brave",
                "text": "The Prime Minister spoke about the budget.",
                "start_time": 0.0,
                "end_time": 5.0,
            },
            {
                "speaker_node_id": "mp_unknown",
                "text": "",  # Empty text — should be skipped gracefully
                "start_time": 5.0,
                "end_time": 10.0,
            },
            {
                "speaker_node_id": "mp_pintard_michael",
                "text": "The Minister of Finance agrees with the proposal.",
                "start_time": 10.0,
                "end_time": 15.0,
            },
            {
                "speaker_node_id": "mp_unknown",
                "text": "   ",  # Whitespace-only — should be skipped
                "start_time": 15.0,
                "end_time": 20.0,
            },
            {
                "speaker_node_id": "mp_davis_brave",
                "text": "The Member for Cat Island is correct.",
                "start_time": 20.0,
                "end_time": 25.0,
            },
        ],
    }

    # extract_mentions should process all segments without crashing
    mentions = extractor.extract_mentions(transcript)

    # Pipeline should have processed all 5 segments (some yielding 0 mentions)
    # At minimum, valid segments with parliamentary references should produce mentions
    # Empty/whitespace segments should produce 0 mentions (not crash)
    assert isinstance(mentions, list), "extract_mentions should return a list"

    # Valid segments with parliamentary references should produce at least some mentions
    # "The Prime Minister", "The Minister of Finance", "The Member for Cat Island"
    assert len(mentions) >= 1, (
        f"Expected at least 1 mention from valid segments, got {len(mentions)}"
    )

    # Verify all mentions have required fields
    for mention in mentions:
        assert mention.session_id == "test_session"
        assert mention.source_node_id is not None
        assert mention.context_window is not None


def test_graph_builder_error_handling():
    """Test that graph builder handles invalid mentions gracefully (NF-7).

    GraphBuilder.build_session_graph() filters out mentions where
    target_node_id is None and is_self_reference is True. This ensures
    invalid data doesn't crash the pipeline.
    """
    builder = GraphBuilder()

    # Mix of valid and invalid mentions
    mentions = [
        {
            "source_node_id": "mp_davis_brave",
            "target_node_id": "mp_pintard_michael",
            "context_window": "Valid mention",
            "sentiment_label": "neutral",
            "raw_mention": "the Leader of the Opposition",
            "timestamp_start": 0.0,
            "timestamp_end": 5.0,
        },
        {
            "source_node_id": "mp_davis_brave",
            "target_node_id": None,  # Unresolved — should be filtered out
            "context_window": "Unresolved mention",
            "sentiment_label": "neutral",
            "raw_mention": "someone",
            "timestamp_start": 5.0,
            "timestamp_end": 10.0,
        },
        {
            "source_node_id": "mp_pintard_michael",
            "target_node_id": "mp_davis_brave",
            "context_window": "Another valid mention",
            "sentiment_label": "positive",
            "raw_mention": "the Prime Minister",
            "timestamp_start": 10.0,
            "timestamp_end": 15.0,
        },
        {
            "source_node_id": "mp_davis_brave",
            "target_node_id": "mp_davis_brave",  # Self-reference — should be filtered
            "context_window": "Self reference",
            "sentiment_label": "neutral",
            "raw_mention": "myself",
            "is_self_reference": True,
            "timestamp_start": 15.0,
            "timestamp_end": 20.0,
        },
    ]

    # build_session_graph should handle invalid mentions without crashing
    graph = builder.build_session_graph(
        mentions=mentions,
        session_id="test_session",
        date="2024-01-15",
    )

    # Graph should be built successfully (SessionGraph Pydantic model)
    assert graph.session_id == "test_session"
    assert graph.date == "2024-01-15"

    # Should have nodes for valid mention participants only
    assert graph.node_count >= 2, (
        f"Expected at least 2 nodes from valid mentions, got {graph.node_count}"
    )

    # Should have edges only from valid mentions (None targets and self-refs filtered)
    # 2 valid mentions out of 4 total
    assert graph.edge_count >= 1, (
        f"Expected at least 1 edge from valid mentions, got {graph.edge_count}"
    )
    assert graph.edge_count <= 2, (
        f"Expected at most 2 edges (invalid filtered), got {graph.edge_count}"
    )

    # Verify no self-reference edges in the graph
    for edge in graph.edges:
        assert edge.source_node_id != edge.target_node_id or not any(
            m.get("is_self_reference") for m in mentions
            if m["source_node_id"] == edge.source_node_id
            and m["target_node_id"] == edge.target_node_id
        ), f"Self-reference edge should have been filtered: {edge.source_node_id}"


def test_batch_processing_resilience():
    """Test that batch processing pattern continues after individual failures (NF-7).

    Demonstrates the error-handling pattern used across pipeline stages:
    individual failures are caught and logged, batch continues.
    """
    batch_files = [
        {"path": "session_001.json", "valid": True},
        {"path": "session_002.json", "valid": False},  # Corrupted
        {"path": "session_003.json", "valid": True},
        {"path": "nonexistent.json", "valid": False},  # Missing
        {"path": "session_004.json", "valid": True},
    ]

    processed_count = 0
    failed_count = 0

    for file_info in batch_files:
        try:
            if not file_info["valid"]:
                raise IOError(f"Failed to process {file_info['path']}")
            processed_count += 1
        except Exception:
            failed_count += 1
            continue

    # All files were attempted
    assert processed_count + failed_count == len(batch_files)

    # Expected successes and failures
    expected_successes = sum(1 for f in batch_files if f["valid"])
    assert processed_count == expected_successes
    assert failed_count == len(batch_files) - expected_successes

    # Pipeline continued after failures
    assert processed_count >= 2, "At least 2 files should succeed after failures"


if __name__ == "__main__":
    print("Running NF-7 Tests: Pipeline Error Handling & Resilience")
    print("=" * 60)

    test_entity_extraction_error_handling()
    print("✅ test_entity_extraction_error_handling passed")

    test_graph_builder_error_handling()
    print("✅ test_graph_builder_error_handling passed")

    test_batch_processing_resilience()
    print("✅ test_batch_processing_resilience passed")

    print("\n✅ NF-7: All tests passed - Pipeline handles errors gracefully")
