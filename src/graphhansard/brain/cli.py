"""Command-line interface for transcription and diarization pipeline.

Usage:
    python -m graphhansard.brain.cli transcribe <audio_file> --session-id <id>
    python -m graphhansard.brain.cli batch <audio_dir> --output-dir <dir>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from graphhansard.brain.pipeline import create_pipeline


def transcribe_command(args):
    """Handle the transcribe command."""
    print(f"Transcribing: {args.audio_file}")
    print(f"Session ID: {args.session_id}")
    print(f"Model: {args.model}")
    print(f"Device: {args.device}")
    print(f"Backend: {args.backend}")

    # Create pipeline
    pipeline = create_pipeline(
        model_size=args.model,
        device=args.device,
        hf_token=args.hf_token,
        use_whisperx=args.use_whisperx,
        backend=args.backend,
    )

    # Process audio
    print("\nProcessing...")
    transcript = pipeline.process(
        audio_path=args.audio_file,
        session_id=args.session_id,
        language=args.language,
        enable_diarization=not args.no_diarization,
    )

    # Save result
    output_path = args.output or f"{args.session_id}_transcript.json"
    pipeline.save_transcript(transcript, output_path)

    print(f"\n✓ Transcript saved to: {output_path}")
    print(f"  Segments: {len(transcript.segments)}")

    # Print summary statistics
    if transcript.segments:
        speakers = set(seg.speaker_label for seg in transcript.segments)
        print(f"  Speakers: {len(speakers)}")
        print(f"  Duration: {transcript.segments[-1].end_time:.1f}s")
        avg_conf = sum(seg.confidence for seg in transcript.segments) / len(
            transcript.segments
        )
        print(f"  Avg Confidence: {avg_conf:.2f}")


def batch_command(args):
    """Handle the batch processing command."""
    audio_dir = Path(args.audio_dir)
    if not audio_dir.exists():
        print(f"Error: Directory not found: {audio_dir}", file=sys.stderr)
        return 1

    # Find audio files
    patterns = ["*.mp3", "*.wav", "*.opus", "*.m4a", "*.flac"]
    audio_files = []
    for pattern in patterns:
        audio_files.extend(audio_dir.glob(pattern))

    if not audio_files:
        print(f"No audio files found in: {audio_dir}", file=sys.stderr)
        return 1

    print(f"Found {len(audio_files)} audio files")

    # Prepare file list with session IDs
    file_list = []
    for audio_file in audio_files:
        session_id = audio_file.stem  # Use filename without extension as session_id
        file_list.append((str(audio_file), session_id))

    # Create pipeline
    pipeline = create_pipeline(
        model_size=args.model,
        device=args.device,
        hf_token=args.hf_token,
        use_whisperx=args.use_whisperx,
        backend=args.backend,
    )

    # Process batch
    print(f"\nProcessing {len(file_list)} files...")
    output_files = pipeline.process_batch(
        audio_files=file_list,
        output_dir=args.output_dir,
        language=args.language,
        enable_diarization=not args.no_diarization,
    )

    print(f"\n✓ Processed {len(output_files)} files")
    print(f"  Output directory: {args.output_dir}")


def info_command(args):
    """Display information about available models and configuration."""
    print("GraphHansard Transcription & Diarization Pipeline")
    print("=" * 60)
    print("\nAvailable Whisper Models:")
    print("  - tiny      (39M params, ~10x realtime on CPU)")
    print("  - base      (74M params, ~7x realtime on CPU)")
    print("  - small     (244M params, ~4x realtime on CPU)")
    print("  - medium    (769M params, ~2x realtime on CPU)")
    print("  - large-v2  (1550M params, ~1x realtime on CPU)")
    print("  - large-v3  (1550M params, ~1x realtime on CPU) [recommended]")

    print("\nBackends:")
    print("  - faster-whisper         (CTranslate2, lower VRAM)")
    print("  - insanely-fast-whisper  (Flash Attention 2, faster on RTX GPUs)")

    print("\nDiarization:")
    print("  - Requires HuggingFace token for pyannote.audio")
    print("  - Get token at: https://huggingface.co/settings/tokens")
    print("  - Accept model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1")

    print("\nConfiguration:")
    print("  - Set HF_TOKEN environment variable for automatic token loading")
    print("  - Use --device cuda for GPU acceleration")
    print("  - Use --use-whisperx for best alignment quality")

    print("\nPerformance Targets (SRD Requirements):")
    print("  - WER ≤ 15% on Bahamian parliamentary speech")
    print("  - DER ≤ 20% on multi-speaker sessions")
    print("  - GPU: 1 hour audio in ≤10 min (RTX 3080+)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GraphHansard Transcription & Diarization Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Transcribe command
    transcribe_parser = subparsers.add_parser(
        "transcribe", help="Transcribe a single audio file"
    )
    transcribe_parser.add_argument("audio_file", help="Path to audio file")
    transcribe_parser.add_argument(
        "--session-id", required=True, help="Session identifier"
    )
    transcribe_parser.add_argument(
        "--output", "-o", help="Output JSON file path (default: <session_id>_transcript.json)"
    )
    transcribe_parser.add_argument(
        "--model", default="large-v3", help="Whisper model size (default: large-v3)"
    )
    transcribe_parser.add_argument(
        "--device", default="cuda", choices=["cuda", "cpu"], help="Device to use"
    )
    transcribe_parser.add_argument(
        "--backend",
        default="faster-whisper",
        choices=["faster-whisper", "insanely-fast-whisper"],
        help="Transcription backend",
    )
    transcribe_parser.add_argument(
        "--language", default="en", help="Language code (default: en)"
    )
    transcribe_parser.add_argument(
        "--hf-token", help="HuggingFace token (or set HF_TOKEN env var)"
    )
    transcribe_parser.add_argument(
        "--no-diarization", action="store_true", help="Disable speaker diarization"
    )
    transcribe_parser.add_argument(
        "--no-whisperx",
        action="store_false",
        dest="use_whisperx",
        help="Disable WhisperX alignment (use simple overlap)",
    )

    # Batch command
    batch_parser = subparsers.add_parser(
        "batch", help="Process multiple audio files"
    )
    batch_parser.add_argument("audio_dir", help="Directory containing audio files")
    batch_parser.add_argument(
        "--output-dir",
        "-o",
        default="./transcripts",
        help="Output directory for transcripts",
    )
    batch_parser.add_argument(
        "--model", default="large-v3", help="Whisper model size (default: large-v3)"
    )
    batch_parser.add_argument(
        "--device", default="cuda", choices=["cuda", "cpu"], help="Device to use"
    )
    batch_parser.add_argument(
        "--backend",
        default="faster-whisper",
        choices=["faster-whisper", "insanely-fast-whisper"],
        help="Transcription backend",
    )
    batch_parser.add_argument(
        "--language", default="en", help="Language code (default: en)"
    )
    batch_parser.add_argument(
        "--hf-token", help="HuggingFace token (or set HF_TOKEN env var)"
    )
    batch_parser.add_argument(
        "--no-diarization", action="store_true", help="Disable speaker diarization"
    )
    batch_parser.add_argument(
        "--no-whisperx",
        action="store_false",
        dest="use_whisperx",
        help="Disable WhisperX alignment",
    )

    # Info command
    info_parser = subparsers.add_parser("info", help="Display system information")

    args = parser.parse_args()

    if args.command == "transcribe":
        return transcribe_command(args)
    elif args.command == "batch":
        return batch_command(args)
    elif args.command == "info":
        return info_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
