"""Test EntityExtractor against the validation corpus.

Validates that the entity extractor meets BR-13 requirements:
- Recall ≥ 85%
- Precision ≥ 80%
"""

import json
from pathlib import Path

import pytest

from graphhansard.brain.entity_extractor import EntityExtractor, ResolutionMethod

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
    with open(CORPUS_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_validation_corpus_exists():
    """Verify the validation corpus file exists."""
    assert CORPUS_PATH.exists(), "Validation corpus file does not exist"


def test_entity_extractor_on_corpus(extractor, validation_corpus):
    """Test EntityExtractor against validation corpus (BR-13).
    
    Target: Precision ≥ 80%, Recall ≥ 85%
    """
    mentions = validation_corpus["mentions"]
    
    # Track results
    total_mentions = len(mentions)
    correct_resolutions = 0
    incorrect_resolutions = 0
    unresolved_mentions = 0
    
    for mention in mentions:
        raw_mention = mention["raw_mention"]
        expected_node_id = mention["expected_node_id"]
        debate_date = mention.get("debate_date")
        
        # Resolve the mention using the resolver (which EntityExtractor uses)
        result = extractor.resolver.resolve(raw_mention, debate_date)
        
        # Check if resolution was correct
        if result.node_id == expected_node_id:
            correct_resolutions += 1
        elif result.node_id is not None:
            incorrect_resolutions += 1
        else:
            unresolved_mentions += 1
    
    # Calculate metrics
    # Precision: Of all resolutions made, what % were correct?
    resolutions_made = correct_resolutions + incorrect_resolutions
    precision = (
        correct_resolutions / resolutions_made if resolutions_made > 0 else 0.0
    )
    
    # Recall: Of all mentions in corpus, what % were correctly resolved?
    recall = correct_resolutions / total_mentions if total_mentions > 0 else 0.0
    
    # F1 Score
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    
    # Print results
    print(f"\n{'='*60}")
    print(f"Entity Extractor Validation Results (BR-13)")
    print(f"{'='*60}")
    print(f"Total Mentions:         {total_mentions}")
    print(f"Correct Resolutions:    {correct_resolutions}")
    print(f"Incorrect Resolutions:  {incorrect_resolutions}")
    print(f"Unresolved Mentions:    {unresolved_mentions}")
    print(f"{'='*60}")
    print(f"Precision:              {precision*100:.1f}% (target: ≥80%)")
    print(f"Recall:                 {recall*100:.1f}% (target: ≥85%)")
    print(f"F1 Score:               {f1_score*100:.1f}%")
    print(f"{'='*60}")
    
    # Assert meets targets (BR-13)
    assert precision >= 0.80, (
        f"Precision {precision*100:.1f}% does not meet target 80%. "
        f"Need to improve pattern matching or resolution."
    )
    assert recall >= 0.85, (
        f"Recall {recall*100:.1f}% does not meet target 85%. "
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
