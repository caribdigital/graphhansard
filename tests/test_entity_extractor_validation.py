"""Test EntityExtractor against the validation corpus.

Validates that the entity extractor meets BR-13 requirements:
- Recall ≥ 85%
- Precision ≥ 80%
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from graphhansard.brain.entity_extractor import EntityExtractor, ResolutionMethod
from validate_corpus import load_corpus, validate_corpus

PROJECT_ROOT = Path(__file__).parent.parent
CORPUS_PATH = PROJECT_ROOT / "golden_record" / "validation" / "annotated_mentions.json"
GOLDEN_RECORD_PATH = PROJECT_ROOT / "golden_record" / "mps.json"


@pytest.fixture
def extractor():
    """Create an EntityExtractor for testing."""
    return EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=False)


@pytest.fixture
def validation_corpus():
    """Load the validation corpus."""
    return load_corpus(CORPUS_PATH)


def test_validation_corpus_exists():
    """Verify the validation corpus file exists."""
    assert CORPUS_PATH.exists(), "Validation corpus file does not exist"


def test_entity_extractor_on_corpus(extractor, validation_corpus):
    """Test EntityExtractor against validation corpus (BR-13).

    Target: Precision ≥ 80%, Recall ≥ 85%
    """
    metrics, _ = validate_corpus(extractor.resolver, validation_corpus)

    # Print results
    print(f"\n{'='*60}")
    print(f"Entity Extractor Validation Results (BR-13)")
    print(f"{'='*60}")
    print(f"Total Mentions:         {metrics.total_mentions}")
    print(f"Correct Resolutions:    {metrics.correct_resolutions}")
    print(f"Incorrect Resolutions:  {metrics.incorrect_resolutions}")
    print(f"Unresolved Mentions:    {metrics.unresolved_mentions}")
    print(f"{'='*60}")
    print(f"Precision:              {metrics.precision*100:.1f}% (target: ≥80%)")
    print(f"Recall:                 {metrics.recall*100:.1f}% (target: ≥85%)")
    print(f"F1 Score:               {metrics.f1_score*100:.1f}%")
    print(f"{'='*60}")

    # Assert meets BR-13 targets
    assert metrics.precision >= 0.80, (
        f"Precision {metrics.precision*100:.1f}% does not meet target 80%. "
        f"Need to improve pattern matching or resolution."
    )
    assert metrics.recall >= 0.85, (
        f"Recall {metrics.recall*100:.1f}% does not meet target 85%. "
        f"Need to detect more mentions or improve patterns."
    )

    print("✓ PASSED: Entity extractor meets BR-13 requirements!")


def test_pattern_coverage_on_corpus(extractor, validation_corpus):
    """Test that patterns can detect different mention types."""
    mentions = validation_corpus["mentions"]

    # Track which mention types we can detect
    detected_by_type = {}
    total_by_type = {}

    for mention in mentions:
        raw_mention = mention["raw_mention"]
        mention_type = mention.get("mention_type", "unknown")

        # Count total of this type
        total_by_type[mention_type] = total_by_type.get(mention_type, 0) + 1

        # Try to detect with pattern matching
        pattern_matches = extractor._extract_pattern_mentions(raw_mention)

        if len(pattern_matches) > 0:
            detected_by_type[mention_type] = detected_by_type.get(mention_type, 0) + 1

    # Print coverage by type
    print(f"\n{'='*60}")
    print(f"Pattern Matching Coverage by Mention Type")
    print(f"{'='*60}")

    for mention_type in sorted(total_by_type.keys()):
        total = total_by_type[mention_type]
        detected = detected_by_type.get(mention_type, 0)
        coverage = (detected / total * 100) if total > 0 else 0.0
        print(f"{mention_type:20s}: {detected:2d}/{total:2d} ({coverage:5.1f}%)")

    print(f"{'='*60}")
