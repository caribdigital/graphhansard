#!/usr/bin/env python
"""Demonstration script for speaker resolution feature.

This script demonstrates how the speaker resolution module maps
diarization labels (SPEAKER_XX) to actual MP node IDs using heuristics.
"""

import json
from pathlib import Path

from graphhansard.brain.speaker_resolver import (
    SpeakerResolver,
    load_mp_registry_from_golden_record,
)


def main():
    """Run speaker resolution demonstration."""
    # Load MP registry
    golden_record_path = Path(__file__).parent.parent / "golden_record" / "mps.json"
    mp_registry = load_mp_registry_from_golden_record(golden_record_path)
    
    # Create resolver
    resolver = SpeakerResolver(mp_registry=mp_registry)
    
    # Sample transcript with various patterns
    sample_transcript = {
        "session_id": "demo_session_2024-01-15",
        "segments": [
            {
                "speaker_label": "SPEAKER_00",
                "text": "Good morning. The House will come to order. The Chair recognizes the Honourable Member for Cat Island, Rum Cay and San Salvador.",
                "start_time": 0.0,
                "end_time": 8.0,
            },
            {
                "speaker_label": "SPEAKER_01",
                "text": "Thank you, Madam Speaker. I rise today to speak about the importance of sustainable development in our constituency. The people of Cat Island deserve better infrastructure and economic opportunities.",
                "start_time": 8.5,
                "end_time": 20.0,
            },
            {
                "speaker_label": "SPEAKER_00",
                "text": "Order, order. The Member has the floor. I recognize the Deputy Prime Minister.",
                "start_time": 20.5,
                "end_time": 25.0,
            },
            {
                "speaker_label": "SPEAKER_02",
                "text": "Thank you, Madam Speaker. I want to commend the Prime Minister on the budget proposals. Tourism is vital to our economy, and we must continue to attract more visitors to support our hotels and ensure our aviation sector remains strong.",
                "start_time": 25.5,
                "end_time": 38.0,
            },
            {
                "speaker_label": "SPEAKER_00",
                "text": "I recognize the Minister of Foreign Affairs.",
                "start_time": 38.5,
                "end_time": 40.5,
            },
            {
                "speaker_label": "SPEAKER_03",
                "text": "Thank you. I wish to address the international relations and our diplomatic efforts in the Caribbean region. Our foreign policy must reflect our values and interests.",
                "start_time": 41.0,
                "end_time": 50.0,
            },
            {
                "speaker_label": "SPEAKER_04",
                "text": "I want to discuss the budget and finance proposals. The tax revenue and fiscal policy are critical for our economic growth and prosperity.",
                "start_time": 50.5,
                "end_time": 58.0,
            },
        ]
    }
    
    print("=" * 80)
    print("SPEAKER RESOLUTION DEMONSTRATION")
    print("=" * 80)
    print()
    print("Sample Transcript:")
    print(f"  Session ID: {sample_transcript['session_id']}")
    print(f"  Total Segments: {len(sample_transcript['segments'])}")
    print(f"  Unique Speakers: {len(set(s['speaker_label'] for s in sample_transcript['segments']))}")
    print()
    
    # Perform speaker resolution
    print("Resolving speakers...")
    print()
    resolutions = resolver.resolve_speakers(sample_transcript, confidence_threshold=0.5)
    
    # Display resolutions
    print("=" * 80)
    print("RESOLUTION RESULTS")
    print("=" * 80)
    print()
    
    for speaker_label, resolution in sorted(resolutions.items()):
        mp_name = mp_registry.get(resolution.resolved_node_id, {}).get("common_name", "Unknown")
        print(f"{speaker_label}:")
        print(f"  → Resolved to: {resolution.resolved_node_id} ({mp_name})")
        print(f"  → Confidence: {resolution.confidence:.2f}")
        print(f"  → Method: {resolution.method}")
        if resolution.evidence:
            print(f"  → Evidence:")
            for evidence in resolution.evidence[:3]:  # Show first 3 pieces of evidence
                print(f"      - {evidence}")
        print()
    
    # Apply resolutions to transcript
    updated_transcript = resolver.apply_resolutions(sample_transcript, resolutions)
    
    # Show updated segments
    print("=" * 80)
    print("UPDATED TRANSCRIPT SEGMENTS")
    print("=" * 80)
    print()
    
    for i, segment in enumerate(updated_transcript["segments"], 1):
        speaker_label = segment["speaker_label"]
        speaker_node_id = segment.get("speaker_node_id", "UNRESOLVED")
        text_preview = segment["text"][:80] + "..." if len(segment["text"]) > 80 else segment["text"]
        
        mp_name = "Unresolved"
        if speaker_node_id != "UNRESOLVED" and speaker_node_id in mp_registry:
            mp_name = mp_registry[speaker_node_id]["common_name"]
        
        print(f"Segment {i}:")
        print(f"  Speaker Label: {speaker_label}")
        print(f"  Resolved ID: {speaker_node_id}")
        print(f"  MP Name: {mp_name}")
        print(f"  Text: {text_preview}")
        print()
    
    # Summary statistics
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    total_segments = len(updated_transcript["segments"])
    resolved_segments = sum(1 for s in updated_transcript["segments"] if s.get("speaker_node_id") is not None)
    unique_speakers = len(set(s["speaker_label"] for s in updated_transcript["segments"]))
    unique_resolved = len(resolutions)
    
    print(f"Total Segments: {total_segments}")
    print(f"Resolved Segments: {resolved_segments}/{total_segments} ({resolved_segments/total_segments*100:.1f}%)")
    print(f"Unique Speaker Labels: {unique_speakers}")
    print(f"Unique Resolved Speakers: {unique_resolved}/{unique_speakers} ({unique_resolved/unique_speakers*100:.1f}%)")
    print()
    
    # Resolution methods breakdown
    methods = {}
    for resolution in resolutions.values():
        methods[resolution.method] = methods.get(resolution.method, 0) + 1
    
    print("Resolution Methods Used:")
    for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
        print(f"  {method}: {count}")
    print()
    
    print("=" * 80)
    print()
    print("✅ Speaker resolution complete!")
    print()
    print("NEXT STEPS:")
    print("  - These resolved speaker_node_ids will be used by entity_extractor.py")
    print("  - Source edges in the graph will now show 'who said what'")
    print("  - Unresolved speakers remain as SPEAKER_XX (no false mappings)")
    print()


if __name__ == "__main__":
    main()
