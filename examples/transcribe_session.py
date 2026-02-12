#!/usr/bin/env python3
"""
Example demonstrating the GraphHansard Transcription & Diarization Pipeline.

This script shows how to use the pipeline to process parliamentary audio
and produce structured, speaker-attributed transcripts.

Requirements:
    - pip install -e ".[brain]"
    - Set HF_TOKEN environment variable for diarization

Usage:
    python examples/transcribe_session.py audio.wav
    python examples/transcribe_session.py audio.wav --with-diarization
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from graphhansard.brain import create_pipeline
except ImportError:
    print("Error: graphhansard not installed. Run: pip install -e '.[brain]'")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Example: Transcribe parliamentary audio"
    )
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument(
        "--with-diarization",
        action="store_true",
        help="Enable speaker diarization (requires HF_TOKEN)",
    )
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model size (default: base for faster processing)",
    )
    parser.add_argument(
        "--output", "-o", help="Output JSON file (default: <audio_name>_transcript.json)"
    )
    args = parser.parse_args()

    # Validate audio file exists
    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_path}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = audio_path.with_suffix("").with_name(
            f"{audio_path.stem}_transcript.json"
        )

    # Extract session ID from filename
    session_id = audio_path.stem

    print("=" * 70)
    print("GraphHansard Transcription Pipeline - Example")
    print("=" * 70)
    print(f"Audio File: {audio_path}")
    print(f"Session ID: {session_id}")
    print(f"Model: {args.model}")
    print(f"Diarization: {'Enabled' if args.with_diarization else 'Disabled'}")
    print(f"Output: {output_path}")
    print("=" * 70)

    # Create pipeline
    print("\n[1/3] Initializing pipeline...")
    try:
        pipeline = create_pipeline(
            model_size=args.model,
            device="cpu",  # Use 'cuda' if you have GPU
            hf_token=None if not args.with_diarization else None,  # Will use HF_TOKEN env var
            use_whisperx=args.with_diarization,
            backend="faster-whisper",
        )
        print("✓ Pipeline initialized")
    except Exception as e:
        print(f"✗ Failed to initialize pipeline: {e}")
        sys.exit(1)

    # Process audio
    print(f"\n[2/3] Processing audio...")
    print("  (This may take several minutes depending on audio length and model)")
    try:
        transcript = pipeline.process(
            audio_path=str(audio_path),
            session_id=session_id,
            enable_diarization=args.with_diarization,
        )
        print("✓ Transcription complete")
    except Exception as e:
        print(f"✗ Transcription failed: {e}")
        if "HuggingFace token" in str(e):
            print("\nNote: Diarization requires HF_TOKEN environment variable.")
            print("Get token at: https://huggingface.co/settings/tokens")
        sys.exit(1)

    # Save results
    print(f"\n[3/3] Saving transcript...")
    try:
        pipeline.save_transcript(transcript, str(output_path))
        print(f"✓ Saved to: {output_path}")
    except Exception as e:
        print(f"✗ Failed to save: {e}")
        sys.exit(1)

    # Display summary
    print("\n" + "=" * 70)
    print("TRANSCRIPT SUMMARY")
    print("=" * 70)
    print(f"Session ID: {transcript.session_id}")
    print(f"Total Segments: {len(transcript.segments)}")

    if transcript.segments:
        speakers = set(seg.speaker_label for seg in transcript.segments)
        print(f"Unique Speakers: {len(speakers)}")
        print(f"Duration: {transcript.segments[-1].end_time:.1f} seconds")

        # Calculate average confidence
        avg_confidence = sum(seg.confidence for seg in transcript.segments) / len(
            transcript.segments
        )
        print(f"Average Confidence: {avg_confidence:.2%}")

        # Show first few segments
        print("\nFirst 3 segments:")
        for i, segment in enumerate(transcript.segments[:3], 1):
            print(f"\n  [{i}] {segment.speaker_label} ({segment.start_time:.1f}s - {segment.end_time:.1f}s)")
            print(f"      {segment.text}")
            print(f"      Confidence: {segment.confidence:.2%}")

    print("\n" + "=" * 70)
    print("✓ Processing complete!")
    print("\nNext steps:")
    print("  1. Review the transcript JSON for accuracy")
    print("  2. Use entity extraction to identify MPs mentioned")
    print("  3. Perform sentiment analysis on mentions")
    print("  4. Build the political interaction graph")
    print("=" * 70)


if __name__ == "__main__":
    main()
