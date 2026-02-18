#!/usr/bin/env python3
"""Azure GPU batch processing script for Stage 2 (Entity Extraction).

This script processes multiple transcript sessions using GPU acceleration,
saving both mention records and unresolved mentions logs for each session.

Usage:
    python scripts/azure_gpu_process.py <transcript_dir> --golden-record <mps.json> --output-dir <output>

Example:
    python scripts/azure_gpu_process.py data/transcripts/ \\
        --golden-record golden_record/mps.json \\
        --output-dir output/
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    """Process multiple transcript sessions and save unresolved mentions logs."""
    parser = argparse.ArgumentParser(
        description="Batch process transcripts with entity extraction (Stage 2)"
    )
    parser.add_argument(
        "transcript_dir",
        help="Directory containing transcript JSON files",
    )
    parser.add_argument(
        "--golden-record",
        required=True,
        help="Path to Golden Record JSON file",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for mentions and unresolved logs (default: output/)",
    )
    parser.add_argument(
        "--use-spacy",
        action="store_true",
        help="Enable spaCy NER for enhanced mention detection",
    )
    parser.add_argument(
        "--date",
        help="Debate date (ISO format: YYYY-MM-DD) for temporal resolution",
    )
    
    args = parser.parse_args()
    
    # Import here to avoid slow startup if just showing help
    from graphhansard.brain.entity_extractor import EntityExtractor
    
    # Validate inputs
    transcript_dir = Path(args.transcript_dir)
    if not transcript_dir.exists():
        print(f"Error: Transcript directory not found: {transcript_dir}", file=sys.stderr)
        return 1
    
    golden_record_path = Path(args.golden_record)
    if not golden_record_path.exists():
        print(f"Error: Golden Record not found: {golden_record_path}", file=sys.stderr)
        return 1
    
    # Find all transcript JSON files
    transcript_files = sorted(transcript_dir.glob("*_transcript.json"))
    if not transcript_files:
        # Also try without the _transcript suffix
        transcript_files = sorted(transcript_dir.glob("*.json"))
    
    if not transcript_files:
        print(f"Error: No transcript JSON files found in {transcript_dir}", file=sys.stderr)
        return 1
    
    print(f"Found {len(transcript_files)} transcript file(s)")
    print(f"Golden Record: {golden_record_path}")
    print(f"Output directory: {args.output_dir}")
    print()
    
    # Create output directory
    OUTPUT_DIR = Path(args.output_dir)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize extractor (single instance for batch processing)
    print("Initializing EntityExtractor...")
    extractor = EntityExtractor(
        golden_record_path=str(golden_record_path),
        use_spacy=args.use_spacy,
    )
    print(f"spaCy enabled: {extractor.use_spacy}")
    print()
    
    # Process each session
    print("=" * 70)
    print("Stage 2: Entity Extraction (Batch Processing)")
    print("=" * 70)
    
    total_mentions = 0
    total_resolved = 0
    total_unresolved = 0
    
    for i, transcript_file in enumerate(transcript_files, 1):
        print(f"\n[{i}/{len(transcript_files)}] Processing: {transcript_file.name}")
        
        # Load transcript
        try:
            with open(transcript_file, "r", encoding="utf-8") as f:
                transcript = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  [ERROR] Invalid JSON: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"  [ERROR] Failed to load: {e}", file=sys.stderr)
            continue
        
        # Get session ID
        session_id = transcript.get("session_id", transcript_file.stem)
        
        # Extract mentions
        try:
            mentions = extractor.extract_mentions(transcript, debate_date=args.date)
        except Exception as e:
            print(f"  [ERROR] Extraction failed: {e}", file=sys.stderr)
            continue
        
        # Save mentions
        mentions_path = OUTPUT_DIR / f"{session_id}_mentions.json"
        try:
            with open(mentions_path, "w", encoding="utf-8") as f:
                json.dump(
                    [m.model_dump(mode="json") for m in mentions],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            print(f"  [ERROR] Failed to save mentions: {e}", file=sys.stderr)
            continue
        
        # Calculate statistics
        resolved = sum(1 for m in mentions if m.target_node_id is not None)
        
        print(f"  [OK] Mentions: {len(mentions)} total, {resolved} resolved")
        
        # Save unresolved mentions log
        unresolved_path = OUTPUT_DIR / f"unresolved_{session_id}.json"
        extractor.save_unresolved_log(str(unresolved_path))
        unresolved_count = extractor.get_unresolved_count()
        print(f"  Unresolved: {unresolved_count} mentions -> {unresolved_path.name}")
        
        # Clear unresolved log for next session
        extractor.clear_unresolved_log()
        
        # Update totals
        total_mentions += len(mentions)
        total_resolved += resolved
        total_unresolved += unresolved_count
    
    # Summary
    print("\n" + "=" * 70)
    print("Batch Processing Complete")
    print("=" * 70)
    print(f"Sessions processed: {len(transcript_files)}")
    print(f"Total mentions: {total_mentions}")
    print(f"Total resolved: {total_resolved}")
    print(f"Total unresolved: {total_unresolved}")
    if total_mentions > 0:
        print(f"Resolution rate: {(total_resolved/total_mentions)*100:.1f}%")
    else:
        print("Resolution rate: 0.0%")
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print(f"  - Mention files: {len(transcript_files)} x *_mentions.json")
    print(f"  - Unresolved logs: {len(transcript_files)} x unresolved_*.json")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
