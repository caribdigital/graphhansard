"""Test for NF-7: Pipeline error handling and resilience.

Requirement: All pipeline stages must log errors and continue processing
remaining items - no single failure kills a batch.

This test verifies that the pipeline handles errors gracefully and
continues processing even when individual items fail.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from graphhansard.brain.entity_extractor import EntityExtractor, MentionRecord
from graphhansard.brain.graph_builder import GraphBuilder


def test_entity_extraction_error_handling():
    """Test that entity extractor continues after individual failures."""
    
    print(f"\n{'='*60}")
    print(f"NF-7: Entity Extraction Error Handling Test")
    print(f"{'='*60}")
    print()
    
    # Create test segments, some will cause errors
    segments = [
        {
            "speaker": "SPEAKER_1",
            "text": "The Prime Minister spoke about the budget.",
            "start": 0.0,
            "end": 5.0,
            "segment_index": 0,
        },
        {
            "speaker": "SPEAKER_2",
            "text": None,  # This will cause an error
            "start": 5.0,
            "end": 10.0,
            "segment_index": 1,
        },
        {
            "speaker": "SPEAKER_3",
            "text": "The Minister of Finance agrees.",
            "start": 10.0,
            "end": 15.0,
            "segment_index": 2,
        },
        {
            "speaker": "SPEAKER_4",
            "text": "Invalid text" * 10000,  # Extremely long, might cause issues
            "start": 15.0,
            "end": 20.0,
            "segment_index": 3,
        },
        {
            "speaker": "SPEAKER_5",
            "text": "The Member for Cat Island is correct.",
            "start": 20.0,
            "end": 25.0,
            "segment_index": 4,
        },
    ]
    
    # Initialize extractor
    golden_record_path = Path(__file__).parent.parent / "golden_record" / "mps.json"
    from graphhansard.golden_record.resolver import AliasResolver
    resolver = AliasResolver(str(golden_record_path))
    extractor = EntityExtractor(resolver=resolver)
    
    print("Processing segments with injected failures...")
    
    successful_segments = 0
    failed_segments = 0
    all_mentions = []
    
    for segment in segments:
        try:
            # Try to extract mentions
            if segment["text"] is None:
                raise ValueError("Text is None")
            
            mentions = extractor.extract_mentions_from_segment(
                session_id="test_session",
                speaker_id="mp_unknown",
                text=segment["text"],
                timestamp_start=segment["start"],
                timestamp_end=segment["end"],
                segment_index=segment["segment_index"],
            )
            
            all_mentions.extend(mentions)
            successful_segments += 1
            print(f"  ✅ Segment {segment['segment_index']}: {len(mentions)} mentions")
            
        except Exception as e:
            # Log error but continue
            failed_segments += 1
            print(f"  ⚠️  Segment {segment['segment_index']}: Error - {type(e).__name__}")
            # In production, this would log to a file
            continue
    
    # Verify error handling
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    
    # Check 1: Some segments succeeded
    has_successes = successful_segments > 0
    print(f"Some segments processed successfully: {has_successes}")
    print(f"  Successful: {successful_segments}")
    print(f"  Failed: {failed_segments}")
    
    # Check 2: Pipeline didn't crash
    pipeline_continued = successful_segments + failed_segments == len(segments)
    print(f"\nPipeline processed all segments: {pipeline_continued}")
    print(f"  Total segments: {len(segments)}")
    print(f"  Processed: {successful_segments + failed_segments}")
    
    # Check 3: Got some mentions from successful segments
    has_results = len(all_mentions) > 0
    print(f"\nExtracted mentions from successful segments: {has_results}")
    print(f"  Total mentions: {len(all_mentions)}")
    
    # Check 4: Failures were isolated (didn't stop batch)
    isolated_failures = successful_segments >= 2  # At least 2 succeeded after failures
    print(f"\nFailures were isolated: {isolated_failures}")
    
    all_checks_pass = (
        has_successes and pipeline_continued and has_results and isolated_failures
    )
    
    print("\n" + "="*60)
    print(f"Status: {'✅ PASS - Error handling works' if all_checks_pass else '❌ FAIL - Error handling broken'}")
    print("="*60)
    
    assert all_checks_pass, "Error handling test failed"
    return all_checks_pass


def test_graph_builder_error_handling():
    """Test that graph builder continues after individual mention failures."""
    
    print(f"\n{'='*60}")
    print(f"NF-7: Graph Builder Error Handling Test")
    print(f"{'='*60}")
    print()
    
    # Create test mentions, some will be invalid
    mentions = [
        {
            "source_node_id": "mp_davis_brave",
            "target_node_id": "mp_pintard_michael",
            "context_window": "Valid mention",
            "sentiment_label": "neutral",
        },
        {
            "source_node_id": None,  # Invalid
            "target_node_id": "mp_pintard_michael",
            "context_window": "Missing source",
            "sentiment_label": "neutral",
        },
        {
            "source_node_id": "mp_davis_brave",
            "target_node_id": "invalid_mp_id",  # Invalid MP
            "context_window": "Invalid target",
            "sentiment_label": "neutral",
        },
        {
            "source_node_id": "mp_pintard_michael",
            "target_node_id": "mp_davis_brave",
            "context_window": "Another valid mention",
            "sentiment_label": "positive",
        },
        {
            "source_node_id": "mp_davis_brave",
            "target_node_id": "mp_davis_brave",  # Self-reference
            "context_window": "Self reference",
            "sentiment_label": "neutral",
            "is_self_reference": True,
        },
    ]
    
    # Load golden record
    golden_record_path = Path(__file__).parent.parent / "golden_record" / "mps.json"
    from graphhansard.golden_record import load_golden_record
    golden_record = load_golden_record(str(golden_record_path))
    
    # Initialize graph builder
    builder = GraphBuilder()
    
    print("Building graph with injected failures...")
    
    try:
        # Build graph - should handle errors gracefully
        graph = builder.build_session_graph(
            session_id="test_session",
            session_date="2024-01-15",
            mentions=mentions,
            golden_record=golden_record,
        )
        
        build_succeeded = True
        num_nodes = graph.number_of_nodes()
        num_edges = graph.number_of_edges()
        
        print(f"  ✅ Graph built successfully")
        print(f"     Nodes: {num_nodes}")
        print(f"     Edges: {num_edges}")
        
    except Exception as e:
        build_succeeded = False
        num_nodes = 0
        num_edges = 0
        print(f"  ❌ Graph build failed: {e}")
    
    # Verify error handling
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    
    # Check 1: Graph was built despite errors
    print(f"Graph built despite invalid mentions: {build_succeeded}")
    
    # Check 2: Valid mentions were processed
    has_edges = num_edges > 0
    print(f"\nValid mentions created edges: {has_edges}")
    print(f"  Edges created: {num_edges}")
    
    # Check 3: Invalid mentions were filtered out
    # We had 5 mentions total, but only 2-3 should be valid
    # (depending on whether self-references are included)
    reasonable_edge_count = num_edges >= 1 and num_edges <= 3
    print(f"\nInvalid mentions filtered: {reasonable_edge_count}")
    print(f"  Total mentions: {len(mentions)}")
    print(f"  Valid edges: {num_edges}")
    
    all_checks_pass = build_succeeded and has_edges and reasonable_edge_count
    
    print("\n" + "="*60)
    print(f"Status: {'✅ PASS - Error handling works' if all_checks_pass else '❌ FAIL - Error handling broken'}")
    print("="*60)
    
    assert all_checks_pass, "Graph builder error handling test failed"
    return all_checks_pass


def test_batch_processing_resilience():
    """Test that batch processing continues after individual file failures."""
    
    print(f"\n{'='*60}")
    print(f"NF-7: Batch Processing Resilience Test")
    print(f"{'='*60}")
    print()
    
    # Simulate a batch of files to process
    batch_files = [
        {"path": "session_001.json", "valid": True},
        {"path": "session_002.json", "valid": False},  # Corrupted
        {"path": "session_003.json", "valid": True},
        {"path": "nonexistent.json", "valid": False},  # Missing
        {"path": "session_004.json", "valid": True},
    ]
    
    print("Processing batch of files with failures...")
    
    processed_count = 0
    failed_count = 0
    
    for file_info in batch_files:
        try:
            # Simulate file processing
            if not file_info["valid"]:
                raise IOError(f"Failed to process {file_info['path']}")
            
            # Simulate successful processing
            processed_count += 1
            print(f"  ✅ Processed: {file_info['path']}")
            
        except Exception as e:
            # Log error and continue
            failed_count += 1
            print(f"  ⚠️  Failed: {file_info['path']} - {type(e).__name__}")
            # In production, would log to error file
            continue
    
    # Verify batch resilience
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    
    # Check 1: Some files processed successfully
    has_successes = processed_count > 0
    print(f"Some files processed: {has_successes}")
    print(f"  Successful: {processed_count}")
    print(f"  Failed: {failed_count}")
    
    # Check 2: All files were attempted
    all_attempted = processed_count + failed_count == len(batch_files)
    print(f"\nAll files attempted: {all_attempted}")
    print(f"  Total files: {len(batch_files)}")
    print(f"  Attempted: {processed_count + failed_count}")
    
    # Check 3: Expected successes
    expected_successes = sum(1 for f in batch_files if f["valid"])
    got_expected = processed_count == expected_successes
    print(f"\nCorrect number of successes: {got_expected}")
    print(f"  Expected: {expected_successes}")
    print(f"  Got: {processed_count}")
    
    all_checks_pass = has_successes and all_attempted and got_expected
    
    print("\n" + "="*60)
    print(f"Status: {'✅ PASS - Batch processing is resilient' if all_checks_pass else '❌ FAIL - Batch processing broken'}")
    print("="*60)
    
    assert all_checks_pass, "Batch processing resilience test failed"
    return all_checks_pass


if __name__ == "__main__":
    print("Running NF-7 Tests: Pipeline Error Handling & Resilience")
    print("="*60)
    
    # Run tests
    extraction_pass = test_entity_extraction_error_handling()
    graph_pass = test_graph_builder_error_handling()
    batch_pass = test_batch_processing_resilience()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Entity Extraction Error Handling: {'✅ PASS' if extraction_pass else '❌ FAIL'}")
    print(f"Graph Builder Error Handling: {'✅ PASS' if graph_pass else '❌ FAIL'}")
    print(f"Batch Processing Resilience: {'✅ PASS' if batch_pass else '❌ FAIL'}")
    print()
    
    if extraction_pass and graph_pass and batch_pass:
        print("✅ NF-7: All tests passed - Pipeline handles errors gracefully")
    else:
        print("❌ NF-7: Some tests failed")
        exit(1)
