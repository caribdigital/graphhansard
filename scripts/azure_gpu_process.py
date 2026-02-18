#!/usr/bin/env python3
"""Azure GPU batch processing script for Stage 2 (Entity Extraction).

This script processes multiple transcript sessions using GPU acceleration,
saving both mention records and unresolved mentions logs for each session.

Includes pre-flight validation checks (Issue #61) to catch configuration
errors before starting processing.

Usage:
    python scripts/azure_gpu_process.py <transcript_dir> --golden-record <mps.json> --output-dir <output>

    # Run pre-flight checks only (no processing)
    python scripts/azure_gpu_process.py <transcript_dir> --golden-record <mps.json> --preflight-only

    # Skip pre-flight checks
    python scripts/azure_gpu_process.py <transcript_dir> --golden-record <mps.json> --skip-preflight

Example:
    python scripts/azure_gpu_process.py data/transcripts/ \\
        --golden-record golden_record/mps.json \\
        --output-dir output/
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

# Constants
BYTES_PER_GB = 1024**3
EXPECTED_MP_COUNT = 39


def preflight_checks(golden_record_path: Path) -> bool:
    """Run comprehensive pre-flight validation checks.

    Validates environment, dependencies, and access before starting
    processing to prevent mid-pipeline failures.

    Args:
        golden_record_path: Path to the golden record JSON file.

    Returns:
        True if all checks pass, False otherwise.
    """
    print("=" * 70)
    print("PRE-FLIGHT CHECKS")
    print("=" * 70)

    all_passed = True

    # Check 1: Golden record validation
    print("\n[1/7] Validating golden record...")
    try:
        if not golden_record_path.exists():
            print(f"  [FAIL] Golden record not found at {golden_record_path}")
            all_passed = False
        else:
            with open(golden_record_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            mp_count = len(data.get("mps", []))

            if mp_count != EXPECTED_MP_COUNT:
                print(f"  [FAIL] Expected {EXPECTED_MP_COUNT} MPs, found {mp_count}")
                all_passed = False
            else:
                print(f"  [OK] Golden record loaded successfully")
                print(f"    MPs: {mp_count}")
                print(
                    f"    Version: {data.get('metadata', {}).get('version', 'unknown')}"
                )
    except Exception as e:
        print(f"  [FAIL] Error loading golden record: {e}")
        all_passed = False

    # Check 2: Audio files validation
    print("\n[2/7] Validating audio files...")
    try:
        # Look for .opus files in common locations
        search_paths = [
            Path.cwd(),
            Path(__file__).parent.parent / "audio",
            Path(__file__).parent.parent / "data",
        ]

        opus_files = []
        for search_path in search_paths:
            if search_path.exists():
                opus_files.extend(search_path.glob("**/*.opus"))

        if not opus_files:
            print("  [WARN] No .opus files found in search paths")
            print(f"    Searched: {[str(p) for p in search_paths]}")
            print("    Note: This may be expected if audio files are provided separately")
        else:
            # Validate the first audio file with ffprobe
            test_file = opus_files[0]
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_format",
                    "-show_streams",
                    str(test_file),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                print("  [OK] Audio files found and validated")
                print(f"    Count: {len(opus_files)}")
                print(f"    Sample: {test_file.name}")
            else:
                print(f"  [FAIL] ffprobe validation failed for {test_file}")
                print(f"    Error: {result.stderr}")
                all_passed = False
    except FileNotFoundError:
        print("  [WARN] ffprobe not found (check will be performed in step 7)")
    except Exception as e:
        print(f"  [WARN] Audio file validation error: {e}")

    # Check 3: HuggingFace token validation
    print("\n[3/7] Validating HuggingFace token...")
    try:
        import huggingface_hub

        token = os.environ.get("HF_TOKEN")
        if not token:
            print("  [FAIL] HF_TOKEN environment variable not set")
            print("    Get token at: https://huggingface.co/settings/tokens")
            all_passed = False
        else:
            # Verify token is valid
            user_info = huggingface_hub.whoami(token=token)
            print("  [OK] HuggingFace token valid")
            print(f"    User: {user_info.get('name', 'unknown')}")
    except ImportError:
        print("  [FAIL] huggingface_hub not installed")
        print("    Install with: pip install huggingface_hub")
        all_passed = False
    except Exception as e:
        print(f"  [FAIL] Token validation error: {e}")
        print("    Ensure HF_TOKEN is set and valid")
        all_passed = False

    # Check 4: Gated models access validation
    print("\n[4/7] Validating gated models access...")
    try:
        from huggingface_hub import HfApi

        token = os.environ.get("HF_TOKEN")
        if not token:
            print("  [FAIL] Cannot check model access without HF_TOKEN")
            all_passed = False
        else:
            api = HfApi()
            models_to_check = [
                "pyannote/segmentation-3.0",
                "pyannote/speaker-diarization-3.1",
            ]

            for model_id in models_to_check:
                try:
                    api.model_info(model_id, token=token)
                    print(f"  [OK] Access granted: {model_id}")
                except Exception as e:
                    error_msg = str(e)
                    if "gated" in error_msg.lower() or "access" in error_msg.lower():
                        print(f"  [FAIL] No access to {model_id}")
                        print(
                            f"    Visit https://huggingface.co/{model_id} to request access"
                        )
                        all_passed = False
                    else:
                        print(f"  [FAIL] Error accessing {model_id}: {e}")
                        all_passed = False
    except ImportError:
        print("  [FAIL] huggingface_hub not installed")
        all_passed = False
    except Exception as e:
        print(f"  [FAIL] Model access validation error: {e}")
        all_passed = False

    # Check 5: Dependencies version printing
    print("\n[5/7] Checking dependency versions...")
    dependencies = [
        {"name": "pyannote.audio", "import_name": "pyannote.audio", "critical": False},
        {"name": "whisperx", "import_name": "whisperx", "critical": False},
        {"name": "torch", "import_name": "torch", "critical": False},
        {"name": "transformers", "import_name": "transformers", "critical": True},
    ]

    for dep in dependencies:
        try:
            module = importlib.import_module(dep["import_name"])
            version = getattr(module, "__version__", "unknown")
            print(f"  [OK] {dep['name']}: {version}")
        except ImportError:
            marker = "[FAIL]" if dep["critical"] else "[WARN]"
            print(f"  {marker} {dep['name']}: NOT INSTALLED")
            if dep["critical"]:
                all_passed = False

    # Check 6: GPU validation
    print("\n[6/7] Validating GPU...")
    try:
        import torch

        if not torch.cuda.is_available():
            print("  [WARN] CUDA not available (entity extraction runs on CPU)")
        else:
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)

            # Get VRAM info
            total_memory = (
                torch.cuda.get_device_properties(0).total_memory / BYTES_PER_GB
            )

            print("  [OK] CUDA available")
            print(f"    Device count: {device_count}")
            print(f"    GPU: {device_name}")
            print(f"    VRAM: {total_memory:.1f} GB")
    except ImportError:
        print("  [WARN] PyTorch not installed (not required for entity extraction)")
    except Exception as e:
        print(f"  [WARN] GPU validation error: {e}")

    # Check 7: ffmpeg validation
    print("\n[7/7] Validating ffmpeg...")
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Extract version from first line
            version_line = result.stdout.split("\n")[0]
            print("  [OK] ffmpeg installed")
            print(f"    {version_line}")
        else:
            print("  [WARN] ffmpeg not working properly")
    except FileNotFoundError:
        print("  [WARN] ffmpeg not found in PATH")
        print("    Install ffmpeg: https://ffmpeg.org/download.html")
    except Exception as e:
        print(f"  [WARN] ffmpeg validation error: {e}")

    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("[OK] ALL PRE-FLIGHT CHECKS PASSED")
        print("=" * 70)
        return True
    else:
        print("[FAIL] PRE-FLIGHT CHECKS FAILED")
        print("=" * 70)
        print("\nPlease resolve the errors above before running the pipeline.")
        return False


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
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip pre-flight validation checks",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run pre-flight checks only (no processing)",
    )

    args = parser.parse_args()

    # Validate golden record path early (needed for preflight)
    golden_record_path = Path(args.golden_record)

    # Run pre-flight checks
    if not args.skip_preflight:
        if not preflight_checks(golden_record_path):
            print("\nExiting due to failed pre-flight checks.")
            print("Use --skip-preflight to bypass.")
            return 1

        if args.preflight_only:
            return 0

    # Import here to avoid slow startup if just showing help
    from graphhansard.brain.entity_extractor import EntityExtractor

    # Validate inputs
    transcript_dir = Path(args.transcript_dir)
    if not transcript_dir.exists():
        print(
            f"Error: Transcript directory not found: {transcript_dir}", file=sys.stderr
        )
        return 1

    if not golden_record_path.exists():
        print(
            f"Error: Golden Record not found: {golden_record_path}", file=sys.stderr
        )
        return 1

    # Find all transcript JSON files
    transcript_files = sorted(transcript_dir.glob("*_transcript.json"))
    if not transcript_files:
        # Also try without the _transcript suffix
        transcript_files = sorted(transcript_dir.glob("*.json"))

    if not transcript_files:
        print(
            f"Error: No transcript JSON files found in {transcript_dir}",
            file=sys.stderr,
        )
        return 1

    print(f"Found {len(transcript_files)} transcript file(s)")
    print(f"Golden Record: {golden_record_path}")
    print(f"Output directory: {args.output_dir}")
    print()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

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
        mentions_path = output_dir / f"{session_id}_mentions.json"
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
        unresolved_path = output_dir / f"unresolved_{session_id}.json"
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
        print(f"Resolution rate: {(total_resolved / total_mentions) * 100:.1f}%")
    else:
        print("Resolution rate: 0.0%")
    print(f"\nOutput directory: {output_dir}")
    print(f"  - Mention files: {len(transcript_files)} x *_mentions.json")
    print(f"  - Unresolved logs: {len(transcript_files)} x unresolved_*.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
