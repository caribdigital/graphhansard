"""Example usage of the EntityExtractor.

Demonstrates how to extract and resolve MP mentions from a transcript.
"""

import json
from pathlib import Path

from graphhansard.brain.entity_extractor import EntityExtractor

# Path to the Golden Record
GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


def example_basic_extraction():
    """Basic example of mention extraction."""
    print("="*70)
    print("Example 1: Basic Mention Extraction")
    print("="*70)
    
    # Initialize the extractor
    extractor = EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=False)
    
    # Create a sample transcript
    transcript = {
        "session_id": "2023-11-15-budget-debate",
        "segments": [
            {
                "text": "The Prime Minister announced the new budget allocation for infrastructure.",
                "speaker_node_id": "mp_thompson_iram",
                "start_time": 0.0,
                "end_time": 5.0,
            },
            {
                "text": "The Member for Cat Island, Rum Cay and San Salvador responded to the statement.",
                "speaker_node_id": "mp_cooper_chester",
                "start_time": 5.0,
                "end_time": 10.0,
            },
            {
                "text": "The Minister of Finance presented detailed figures to the House.",
                "speaker_node_id": "mp_munroe_michael",
                "start_time": 10.0,
                "end_time": 15.0,
            },
        ],
    }
    
    # Extract mentions
    mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
    
    # Display results
    print(f"\nFound {len(mentions)} mention(s):\n")
    for i, mention in enumerate(mentions, 1):
        print(f"{i}. Mention: '{mention.raw_mention}'")
        print(f"   Source: {mention.source_node_id}")
        print(f"   Target: {mention.target_node_id}")
        print(f"   Resolution: {mention.resolution_method.value} (score: {mention.resolution_score:.2f})")
        print(f"   Timestamp: {mention.timestamp_start:.1f}s - {mention.timestamp_end:.1f}s")
        print(f"   Context: {mention.context_window[:100]}...")
        print()


def example_temporal_disambiguation():
    """Example showing temporal disambiguation of portfolios."""
    print("="*70)
    print("Example 2: Temporal Disambiguation")
    print("="*70)
    
    extractor = EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=False)
    
    # Same mention text, different dates
    transcript_before = {
        "session_id": "2023-08-01-session",
        "segments": [
            {
                "text": "The Minister of Works addressed the infrastructure concerns.",
                "speaker_node_id": "mp_cooper_chester",
                "start_time": 0.0,
                "end_time": 5.0,
            },
        ],
    }
    
    transcript_after = {
        "session_id": "2023-10-15-session",
        "segments": [
            {
                "text": "The Minister of Works addressed the infrastructure concerns.",
                "speaker_node_id": "mp_cooper_chester",
                "start_time": 0.0,
                "end_time": 5.0,
            },
        ],
    }
    
    # Extract with different dates
    mentions_before = extractor.extract_mentions(transcript_before, debate_date="2023-08-01")
    mentions_after = extractor.extract_mentions(transcript_after, debate_date="2023-10-15")
    
    print("\nBefore September 2023 reshuffle (2023-08-01):")
    if mentions_before:
        print(f"  'Minister of Works' resolved to: {mentions_before[0].target_node_id}")
    
    print("\nAfter September 2023 reshuffle (2023-10-15):")
    if mentions_after:
        print(f"  'Minister of Works' resolved to: {mentions_after[0].target_node_id}")
    
    print("\n(Portfolio assignments changed during cabinet reshuffle)")


def example_unresolved_mentions():
    """Example showing how unresolved mentions are handled."""
    print("="*70)
    print("Example 3: Unresolved Mention Handling")
    print("="*70)
    
    extractor = EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=False)
    
    transcript = {
        "session_id": "2023-11-15-session",
        "segments": [
            {
                "text": "The Speaker recognized the Member for Nassau and the unknown representative.",
                "speaker_node_id": "mp_thompson_iram",
                "start_time": 0.0,
                "end_time": 5.0,
            },
        ],
    }
    
    mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
    
    print(f"\nExtracted {len(mentions)} mention(s):")
    for mention in mentions:
        status = "✓ RESOLVED" if mention.target_node_id else "✗ UNRESOLVED"
        print(f"\n  {status}")
        print(f"  Raw mention: '{mention.raw_mention}'")
        print(f"  Target: {mention.target_node_id or 'None'}")
        print(f"  Method: {mention.resolution_method.value}")
    
    # Show unresolved count
    unresolved = [m for m in mentions if not m.target_node_id]
    print(f"\nTotal unresolved: {len(unresolved)}")
    print("(These would be logged for human review in production)")


def example_with_spacy():
    """Example using spaCy NER (if available)."""
    print("="*70)
    print("Example 4: Enhanced Extraction with spaCy NER")
    print("="*70)
    
    try:
        extractor = EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=True)
        
        if not extractor.use_spacy:
            print("\nspaCy is not available. Install with:")
            print("  pip install spacy")
            print("  python -m spacy download en_core_web_sm")
            return
        
        transcript = {
            "session_id": "2023-11-15-session",
            "segments": [
                {
                    "text": "Brave Davis and Chester Cooper discussed the proposal with Fred Mitchell.",
                    "speaker_node_id": "mp_thompson_iram",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
        
        print(f"\nspaCy enabled: {extractor.use_spacy}")
        print(f"Found {len(mentions)} mention(s) using pattern matching + NER:\n")
        
        for mention in mentions:
            print(f"  - '{mention.raw_mention}' → {mention.target_node_id}")
    
    except ImportError:
        print("\nspaCy is not installed. To use NER:")
        print("  pip install spacy")
        print("  python -m spacy download en_core_web_sm")


def example_export_mentions():
    """Example showing how to export mentions to JSON."""
    print("="*70)
    print("Example 5: Exporting Mentions to JSON")
    print("="*70)
    
    extractor = EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=False)
    
    transcript = {
        "session_id": "2023-11-15-budget-debate",
        "segments": [
            {
                "text": "The Prime Minister thanked the Deputy Prime Minister for the report.",
                "speaker_node_id": "mp_thompson_iram",
                "start_time": 0.0,
                "end_time": 5.0,
            },
        ],
    }
    
    mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
    
    # Convert to dictionaries
    mention_dicts = [mention.model_dump() for mention in mentions]
    
    # Export to JSON
    output = {
        "session_id": "2023-11-15-budget-debate",
        "total_mentions": len(mentions),
        "mentions": mention_dicts,
    }
    
    print("\nMention records ready for export:")
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*18 + "EntityExtractor Usage Examples" + " "*20 + "║")
    print("╚" + "="*68 + "╝")
    print()
    
    example_basic_extraction()
    print("\n")
    
    example_temporal_disambiguation()
    print("\n")
    
    example_unresolved_mentions()
    print("\n")
    
    example_with_spacy()
    print("\n")
    
    example_export_mentions()
    print("\n")
    
    print("="*70)
    print("Examples complete!")
    print("="*70)
