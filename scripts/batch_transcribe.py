#!/usr/bin/env python3
"""Azure GPU batch transcription with automated session metadata loading.

This script handles batch processing of parliamentary session audio files on Azure GPUs
with automatic metadata management. Session metadata (date, title) can be:
  1. Loaded from an external JSON file (--metadata flag)
  2. Auto-extracted from YouTube using yt-dlp (via fetch_session_metadata.py)
  3. Defaulted to video_id as session_id if no metadata is provided

Usage:
    # With external metadata JSON file
    python scripts/batch_transcribe.py <audio_dir> --output-dir <dir> --metadata sessions.json

    # Without metadata (uses video_id as session_id)
    python scripts/batch_transcribe.py <audio_dir> --output-dir <dir>

    # Generate metadata first, then process
    python scripts/fetch_session_metadata.py urls.txt --output sessions.json
    python scripts/batch_transcribe.py archive/ --metadata sessions.json

Metadata JSON Format:
    {
      "7cuPpo7ko78": {
        "date": "2026-01-28",
        "title": "House of Assembly 28 Jan 2026 Morning"
      },
      "Y--YlPwcI8o": {
        "date": "2026-02-04",
        "title": "House of Assembly 4 Feb 2026 Morning"
      }
    }

Requirements:
    - pip install -e ".[brain]"
    - CUDA-capable GPU (Azure NC-series or equivalent)
    - Set HF_TOKEN environment variable for diarization
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def validate_date_format(date_string: str) -> bool:
    """Validate that date string is in ISO 8601 format (YYYY-MM-DD).

    Args:
        date_string: Date string to validate

    Returns:
        True if valid ISO 8601 date, False otherwise
    """
    try:
        datetime.fromisoformat(date_string)
        return True
    except (ValueError, TypeError):
        return False


def load_session_metadata(metadata_path: str | Path) -> dict[str, dict[str, str]]:
    """Load session metadata from JSON file.

    Args:
        metadata_path: Path to JSON file containing session metadata

    Returns:
        Dictionary mapping video_id to metadata dict with 'date' and 'title'

    Raises:
        FileNotFoundError: If metadata file doesn't exist
        ValueError: If JSON is invalid or dates are malformed
    """
    metadata_path = Path(metadata_path)

    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in metadata file: {e}")

    # Validate metadata structure and date formats
    validated_metadata = {}
    for video_id, meta in metadata.items():
        if not isinstance(meta, dict):
            logger.warning(f"Skipping {video_id}: metadata must be a dictionary")
            continue

        if "date" not in meta:
            logger.warning(f"Skipping {video_id}: missing 'date' field")
            continue

        if not validate_date_format(meta["date"]):
            logger.warning(
                f"Skipping {video_id}: invalid date format '{meta['date']}'. "
                "Expected ISO 8601 (YYYY-MM-DD)"
            )
            continue

        validated_metadata[video_id] = {
            "date": meta["date"],
            "title": meta.get("title", f"Session {video_id}"),
        }

    logger.info(f"Loaded metadata for {len(validated_metadata)} sessions")
    return validated_metadata


def discover_audio_files(audio_dir: Path) -> list[Path]:
    """Discover all audio files in the given directory.

    Args:
        audio_dir: Directory containing audio files

    Returns:
        List of audio file paths
    """
    patterns = ["*.mp3", "*.wav", "*.opus", "*.m4a", "*.flac"]
    audio_files = []

    for pattern in patterns:
        audio_files.extend(audio_dir.glob(pattern))

    # Sort for deterministic ordering
    audio_files.sort()

    logger.info(f"Discovered {len(audio_files)} audio files in {audio_dir}")
    return audio_files


def extract_session_id(audio_path: Path) -> str:
    """Extract session ID from audio filename.

    The session ID is typically the video ID, extracted from the filename stem.

    Args:
        audio_path: Path to audio file

    Returns:
        Session ID (typically video ID from filename)
    """
    return audio_path.stem


def process_batch(
    audio_dir: str | Path,
    output_dir: str | Path,
    metadata: dict[str, dict[str, str]] | None = None,
    model_size: str = "base",
    device: str = "cuda",
    backend: str = "faster-whisper",
    enable_diarization: bool = True,
) -> dict[str, Any]:
    """Process a batch of audio files with session metadata tracking.

    Args:
        audio_dir: Directory containing audio files
        output_dir: Directory to save transcripts
        metadata: Optional session metadata dict {video_id: {date, title}}
        model_size: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
        device: Device to use (cuda, cpu)
        backend: Transcription backend (faster-whisper, insanely-fast-whisper)
        enable_diarization: Whether to enable speaker diarization

    Returns:
        Batch processing results with statistics
    """
    # Lazy import to avoid slow startup and allow testing without brain installed
    from graphhansard.brain.pipeline import create_pipeline

    audio_dir = Path(audio_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Discover audio files
    audio_files = discover_audio_files(audio_dir)

    if not audio_files:
        logger.error(f"No audio files found in {audio_dir}")
        return {
            "status": "error",
            "message": "No audio files found",
            "processed": 0,
            "failed": 0,
        }

    # Create processing pipeline
    logger.info(f"Initializing pipeline (model={model_size}, device={device})")
    try:
        pipeline = create_pipeline(
            model_size=model_size,
            device=device,
            backend=backend,
            use_whisperx=enable_diarization,
        )
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        return {
            "status": "error",
            "message": f"Pipeline initialization failed: {e}",
            "processed": 0,
            "failed": 0,
        }

    # Process files
    results = {
        "status": "success",
        "processing_timestamp": datetime.now().isoformat(),
        "total_files": len(audio_files),
        "processed": 0,
        "failed": 0,
        "sessions": [],
        "errors": [],
    }

    for i, audio_path in enumerate(audio_files, 1):
        session_id = extract_session_id(audio_path)

        # Get metadata for this session (or use defaults)
        session_meta = metadata.get(session_id, {}) if metadata else {}
        session_date = session_meta.get("date", None)
        session_title = session_meta.get("title", f"Session {session_id}")

        logger.info(f"[{i}/{len(audio_files)}] Processing: {audio_path.name}")
        logger.info(f"  Session ID: {session_id}")
        if session_date:
            logger.info(f"  Date: {session_date}")
        logger.info(f"  Title: {session_title}")

        try:
            # Process audio
            transcript = pipeline.process(
                audio_path=str(audio_path),
                session_id=session_id,
                language="en",
                enable_diarization=enable_diarization,
            )

            # Build output data with embedded metadata
            output_data = {
                "transcript": transcript.model_dump(mode="json"),
                "session_metadata": {
                    "session_id": session_id,
                    "date": session_date,
                    "title": session_title,
                    "audio_file": audio_path.name,
                    "processing_timestamp": datetime.now().isoformat(),
                    "device": device,
                    "model": model_size,
                },
            }

            # Save transcript with metadata
            output_path = output_dir / f"{session_id}_transcript.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            logger.info(f"  [OK] Saved to: {output_path}")
            logger.info(f"  Segments: {len(transcript.segments)}")

            results["processed"] += 1
            results["sessions"].append({
                "session_id": session_id,
                "date": session_date,
                "title": session_title,
                "output_file": str(output_path),
                "segments": len(transcript.segments),
            })

        except Exception as e:
            logger.error(f"  [FAIL] Failed to process {audio_path.name}: {e}")
            results["failed"] += 1
            results["errors"].append({
                "session_id": session_id,
                "audio_file": audio_path.name,
                "error": str(e),
            })

    # Save batch summary
    summary_path = output_dir / "batch_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*70}")
    logger.info("Batch Processing Complete")
    logger.info(f"{'='*70}")
    logger.info(f"Total files: {results['total_files']}")
    logger.info(f"Processed: {results['processed']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Summary saved to: {summary_path}")

    return results


def main():
    """Main entry point for Azure GPU batch transcription."""
    parser = argparse.ArgumentParser(
        description="Azure GPU batch transcription with session metadata automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Required arguments
    parser.add_argument(
        "audio_dir",
        help="Directory containing audio files to process",
    )

    # Optional arguments
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for transcripts (default: output/)",
    )
    parser.add_argument(
        "--metadata",
        help="Path to JSON file containing session metadata",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="Device to use for processing (default: cuda)",
    )
    parser.add_argument(
        "--backend",
        default="faster-whisper",
        choices=["faster-whisper", "insanely-fast-whisper"],
        help="Transcription backend (default: faster-whisper)",
    )
    parser.add_argument(
        "--no-diarization",
        action="store_true",
        help="Disable speaker diarization",
    )

    args = parser.parse_args()

    # Validate audio directory exists
    audio_dir = Path(args.audio_dir)
    if not audio_dir.exists():
        logger.error(f"Audio directory not found: {audio_dir}")
        sys.exit(1)

    if not audio_dir.is_dir():
        logger.error(f"Audio path is not a directory: {audio_dir}")
        sys.exit(1)

    # Load metadata if provided
    metadata = None
    if args.metadata:
        try:
            metadata = load_session_metadata(args.metadata)
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Failed to load metadata: {e}")
            sys.exit(1)
    else:
        logger.info("No metadata file provided. Using video_id as session_id.")

    # Process batch
    results = process_batch(
        audio_dir=audio_dir,
        output_dir=args.output_dir,
        metadata=metadata,
        model_size=args.model,
        device=args.device,
        backend=args.backend,
        enable_diarization=not args.no_diarization,
    )

    # Exit with error code if any failures
    if results["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
