"""Tests for the validation corpus script.

Tests the validation script that validates the alias resolver
against the manually annotated corpus.
"""

import json
from pathlib import Path

import pytest

from graphhansard.golden_record.resolver import AliasResolver


def test_annotated_corpus_structure():
    """Verify the annotated corpus has the correct structure."""
    corpus_path = Path("golden_record/validation/annotated_mentions.json")
    assert corpus_path.exists(), "Annotated corpus file does not exist"

    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)

    # Check metadata
    assert "metadata" in corpus
    assert "version" in corpus["metadata"]
    assert "total_mentions" in corpus["metadata"]
    assert "sources" in corpus["metadata"]

    # Check mentions
    assert "mentions" in corpus
    assert len(corpus["mentions"]) >= 50, "Corpus should have at least 50 mentions"

    # Verify metadata total matches actual count
    assert (
        corpus["metadata"]["total_mentions"] == len(corpus["mentions"])
    ), "Metadata total_mentions should match actual count"

    # Check each mention has required fields
    required_fields = [
        "mention_id",
        "raw_mention",
        "expected_node_id",
        "session_id",
        "timestamp",
        "debate_date",
        "context_window",
        "mention_type",
    ]

    for mention in corpus["mentions"]:
        for field in required_fields:
            assert field in mention, f"Mention {mention.get('mention_id')} missing {field}"


def test_annotated_corpus_node_ids_valid():
    """Verify all expected_node_ids in corpus exist in golden record."""
    corpus_path = Path("golden_record/validation/annotated_mentions.json")
    golden_record_path = Path("golden_record/mps.json")

    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)

    with open(golden_record_path, encoding="utf-8") as f:
        golden_record = json.load(f)

    # Get all valid node_ids
    valid_node_ids = {mp["node_id"] for mp in golden_record["mps"]}

    # Check each expected_node_id is valid
    for mention in corpus["mentions"]:
        node_id = mention["expected_node_id"]
        assert (
            node_id in valid_node_ids
        ), f"Mention {mention['mention_id']}: invalid node_id '{node_id}'"


def test_validation_script_meets_target():
    """Verify validation meets the SRD §6.5 requirement (90%+ precision and recall)."""
    corpus_path = Path("golden_record/validation/annotated_mentions.json")
    golden_record_path = Path("golden_record/mps.json")

    # Load corpus
    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)

    # Initialize resolver
    resolver = AliasResolver(str(golden_record_path))

    # Run validation
    total_mentions = len(corpus["mentions"])
    correct_resolutions = 0
    incorrect_resolutions = 0
    unresolved_mentions = 0

    for mention in corpus["mentions"]:
        raw_mention = mention["raw_mention"]
        expected_node_id = mention["expected_node_id"]
        debate_date = mention.get("debate_date")

        # Resolve the mention
        result = resolver.resolve(raw_mention, debate_date)

        # Determine if resolution was correct
        is_correct = result.node_id == expected_node_id
        was_resolved = result.node_id is not None

        if is_correct:
            correct_resolutions += 1
        elif was_resolved:
            incorrect_resolutions += 1
        else:
            unresolved_mentions += 1

    # Calculate metrics
    tp = correct_resolutions
    fp = incorrect_resolutions
    fn = unresolved_mentions

    total_resolutions = tp + fp
    precision = tp / total_resolutions if total_resolutions > 0 else 0.0

    total_positives = tp + fn
    recall = tp / total_positives if total_positives > 0 else 0.0

    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    # Assert meets target (90%+ on both)
    target = 0.90
    assert (
        precision >= target
    ), f"Precision {precision*100:.1f}% does not meet target {target*100:.0f}%"
    assert (
        recall >= target
    ), f"Recall {recall*100:.1f}% does not meet target {target*100:.0f}%"

    # Print results for documentation
    print(f"\nValidation Results:")
    print(f"  Precision: {precision*100:.1f}%")
    print(f"  Recall: {recall*100:.1f}%")
    print(f"  F1 Score: {f1_score*100:.1f}%")
    print(f"  Total Mentions: {total_mentions}")
    print(f"  Correct: {correct_resolutions}")
    print(f"  Incorrect: {incorrect_resolutions}")
    print(f"  Unresolved: {unresolved_mentions}")


def test_corpus_has_diverse_mention_types():
    """Verify the corpus includes diverse mention types."""
    corpus_path = Path("golden_record/validation/annotated_mentions.json")

    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)

    # Count mention types
    mention_types = {}
    for mention in corpus["mentions"]:
        mention_type = mention.get("mention_type", "unknown")
        mention_types[mention_type] = mention_types.get(mention_type, 0) + 1

    # Should have at least these types represented
    expected_types = ["full_name", "portfolio", "constituency", "nickname"]
    for expected_type in expected_types:
        assert (
            expected_type in mention_types
        ), f"Corpus should include {expected_type} mentions"

    # Should have reasonable distribution (no type dominates too much)
    total = len(corpus["mentions"])
    for mention_type, count in mention_types.items():
        percentage = (count / total) * 100
        assert (
            percentage < 50
        ), f"Mention type '{mention_type}' ({percentage:.1f}%) should not dominate corpus"


def test_corpus_includes_temporal_disambiguation():
    """Verify the corpus includes temporal disambiguation test cases."""
    corpus_path = Path("golden_record/validation/annotated_mentions.json")

    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)

    # Look for mentions with same raw_mention but different expected results
    # (indicating temporal disambiguation)
    mentions_by_text = {}
    for mention in corpus["mentions"]:
        raw = mention["raw_mention"]
        if raw not in mentions_by_text:
            mentions_by_text[raw] = []
        mentions_by_text[raw].append(mention)

    # Find cases where same text resolves to different MPs on different dates
    temporal_cases = []
    for raw, mentions in mentions_by_text.items():
        if len(mentions) > 1:
            # Check if they have different expected_node_ids or dates
            node_ids = {m["expected_node_id"] for m in mentions}
            dates = {m.get("debate_date") for m in mentions}
            if len(node_ids) > 1 or len(dates) > 1:
                temporal_cases.append(raw)

    # Should have at least one temporal disambiguation case
    # (like "Minister of Works" which changed after Sept 2023 reshuffle)
    assert (
        len(temporal_cases) >= 1
    ), "Corpus should include temporal disambiguation test cases"


def test_corpus_sources_documented():
    """Verify the corpus metadata includes source documentation."""
    corpus_path = Path("golden_record/validation/annotated_mentions.json")

    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)

    sources = corpus["metadata"]["sources"]

    # Should have at least 3 sources (per acceptance criteria)
    assert len(sources) >= 3, "Corpus should include at least 3 source sessions"

    # Each source should have required fields
    required_source_fields = ["session_id", "date", "session_type"]
    for source in sources:
        for field in required_source_fields:
            assert (
                field in source
            ), f"Source {source.get('session_id')} missing {field}"
