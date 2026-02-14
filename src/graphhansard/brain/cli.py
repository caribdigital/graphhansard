"""Command-line interface for the GraphHansard brain pipeline.

Provides CLI access to all stages of the data processing pipeline:

Stage 1 - Transcription & Diarization:
    python -m graphhansard.brain transcribe <audio_file> --session-id <id>
    python -m graphhansard.brain batch <audio_dir> --output-dir <dir>

Stage 2 - Entity Extraction:
    python -m graphhansard.brain extract <transcript.json> --golden-record <mps.json>

Stage 3 - Sentiment Scoring:
    python -m graphhansard.brain sentiment <mentions.json>

Stage 4 - Graph Construction:
    python -m graphhansard.brain build-graph <mentions.json> --session-id <id> --date <date>

Full Pipeline (Stages 1-5):
    python -m graphhansard.brain process <audio_file> --session-id <id> --golden-record <mps.json>
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


def extract_command(args):
    """Handle the extract command (Stage 2: Entity Extraction)."""
    import json
    from graphhansard.brain.entity_extractor import EntityExtractor

    print(f"Extracting mentions from: {args.transcript}")
    print(f"Golden Record: {args.golden_record}")

    # Load transcript
    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"Error: Transcript file not found: {transcript_path}", file=sys.stderr)
        return 1

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    # Initialize extractor
    extractor = EntityExtractor(
        golden_record_path=args.golden_record,
        use_spacy=args.use_spacy,
    )

    # Extract mentions
    print("\nExtracting mentions...")
    mentions = extractor.extract_mentions(transcript, debate_date=args.date)

    # Save mentions
    output_path = args.output or f"{transcript.get('session_id', 'session')}_mentions.json"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            [m.model_dump(mode="json") for m in mentions],
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n✓ Extracted {len(mentions)} mentions")
    print(f"  Output: {output_path}")

    # Print summary statistics
    resolved = sum(1 for m in mentions if m.target_node_id is not None)
    print(f"  Resolved: {resolved}/{len(mentions)}")


def sentiment_command(args):
    """Handle the sentiment command (Stage 3: Sentiment Scoring)."""
    import json
    from graphhansard.brain.entity_extractor import MentionRecord
    from graphhansard.brain.sentiment import SentimentScorer

    print(f"Scoring sentiment for: {args.mentions}")

    # Load mentions
    mentions_path = Path(args.mentions)
    if not mentions_path.exists():
        print(f"Error: Mentions file not found: {mentions_path}", file=sys.stderr)
        return 1

    with open(mentions_path, "r", encoding="utf-8") as f:
        mentions_data = json.load(f)

    mentions = [MentionRecord(**m) for m in mentions_data]

    # Initialize scorer
    print("\nInitializing sentiment scorer...")
    scorer = SentimentScorer(model_name=args.model)

    # Score mentions
    print("Scoring sentiment...")
    scored_mentions = []
    for mention in mentions:
        sentiment = scorer.score(mention.context_window)
        mention_dict = mention.model_dump(mode="json")
        mention_dict["sentiment_label"] = sentiment.label.value
        mention_dict["sentiment_confidence"] = sentiment.confidence
        mention_dict["parliamentary_markers"] = sentiment.parliamentary_markers
        scored_mentions.append(mention_dict)

    # Save scored mentions
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = mentions_path.parent / f"{mentions_path.stem}_scored.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scored_mentions, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Scored {len(scored_mentions)} mentions")
    print(f"  Output: {output_path}")

    # Print summary statistics
    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
    for m in scored_mentions:
        sentiment_counts[m["sentiment_label"]] += 1

    print(f"  Positive: {sentiment_counts['positive']}")
    print(f"  Neutral: {sentiment_counts['neutral']}")
    print(f"  Negative: {sentiment_counts['negative']}")


def build_graph_command(args):
    """Handle the build-graph command (Stage 4: Graph Construction)."""
    import json
    from graphhansard.brain.graph_builder import GraphBuilder

    print(f"Building session graph from: {args.mentions}")
    print(f"Session ID: {args.session_id}")
    print(f"Date: {args.date}")

    # Load mentions
    mentions_path = Path(args.mentions)
    if not mentions_path.exists():
        print(f"Error: Mentions file not found: {mentions_path}", file=sys.stderr)
        return 1

    with open(mentions_path, "r", encoding="utf-8") as f:
        mentions = json.load(f)

    # Load MP registry if provided
    mp_registry = None
    if args.golden_record:
        with open(args.golden_record, "r", encoding="utf-8") as f:
            golden_data = json.load(f)
            mp_registry = {}
            for mp in golden_data.get("mps", []):
                mp_registry[mp["node_id"]] = {
                    "common_name": mp["common_name"],
                    "party": mp.get("party", "Unknown"),
                    "constituency": mp.get("constituency"),
                    "current_portfolio": mp.get("current_portfolio"),
                }

    # Build graph
    print("\nBuilding session graph...")
    builder = GraphBuilder()
    session_graph = builder.build_session_graph(
        mentions=mentions,
        session_id=args.session_id,
        date=args.date,
        mp_registry=mp_registry,
    )

    # Save graph
    output_path = args.output or f"output/sample_session_{args.session_id}.json"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    builder.export_json(session_graph, str(output_path))

    print(f"\n✓ Session graph built successfully")
    print(f"  Output: {output_path}")
    print(f"  Nodes: {session_graph.node_count} MPs")
    print(f"  Edges: {session_graph.edge_count} interactions")

    # Export additional formats if requested
    if args.graphml:
        graphml_path = output_path.with_suffix(".graphml")
        nx_graph = builder.build_graph_from_session(session_graph)
        builder.export_graphml(nx_graph, str(graphml_path))
        print(f"  GraphML: {graphml_path}")

    if args.csv:
        csv_path = output_path.with_suffix(".csv")
        builder.export_csv(session_graph, str(csv_path))
        print(f"  CSV: {csv_path}")


def process_command(args):
    """Handle the process command (Full pipeline: Stages 1-5)."""
    import json
    from graphhansard.brain.pipeline import create_pipeline
    from graphhansard.brain.entity_extractor import EntityExtractor
    from graphhansard.brain.sentiment import SentimentScorer
    from graphhansard.brain.graph_builder import GraphBuilder

    print("=" * 70)
    print("GraphHansard End-to-End Pipeline")
    print("=" * 70)
    print(f"\nInput: {args.audio_file}")
    print(f"Session ID: {args.session_id}")
    print(f"Output Directory: {args.output_dir}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: Transcription & Diarization
    print("\n" + "=" * 70)
    print("Stage 1: Transcription & Diarization")
    print("=" * 70)

    pipeline = create_pipeline(
        model_size=args.model,
        device=args.device,
        hf_token=args.hf_token,
        use_whisperx=args.use_whisperx,
        backend=args.backend,
    )

    transcript = pipeline.process(
        audio_path=args.audio_file,
        session_id=args.session_id,
        language=args.language,
        enable_diarization=not args.no_diarization,
    )

    transcript_path = output_dir / f"{args.session_id}_transcript.json"
    pipeline.save_transcript(transcript, str(transcript_path))
    print(f"✓ Transcript saved: {transcript_path}")
    print(f"  Segments: {len(transcript.segments)}")

    # Stage 2: Entity Extraction
    print("\n" + "=" * 70)
    print("Stage 2: Entity Extraction")
    print("=" * 70)

    extractor = EntityExtractor(
        golden_record_path=args.golden_record,
        use_spacy=args.use_spacy,
    )

    # Convert transcript to dict for extractor
    transcript_dict = transcript.model_dump(mode="json")
    mentions = extractor.extract_mentions(transcript_dict, debate_date=args.date)

    mentions_path = output_dir / f"{args.session_id}_mentions.json"
    with open(mentions_path, "w", encoding="utf-8") as f:
        json.dump(
            [m.model_dump(mode="json") for m in mentions],
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"✓ Mentions extracted: {mentions_path}")
    print(f"  Total mentions: {len(mentions)}")
    resolved = sum(1 for m in mentions if m.target_node_id is not None)
    print(f"  Resolved: {resolved}/{len(mentions)}")

    # Stage 3: Sentiment Scoring
    print("\n" + "=" * 70)
    print("Stage 3: Sentiment Scoring")
    print("=" * 70)

    scorer = SentimentScorer(model_name=args.sentiment_model)

    scored_mentions = []
    for mention in mentions:
        sentiment = scorer.score(mention.context_window)
        mention_dict = mention.model_dump(mode="json")
        mention_dict["sentiment_label"] = sentiment.label.value
        mention_dict["sentiment_confidence"] = sentiment.confidence
        mention_dict["parliamentary_markers"] = sentiment.parliamentary_markers
        scored_mentions.append(mention_dict)

    scored_path = output_dir / f"{args.session_id}_mentions_scored.json"
    with open(scored_path, "w", encoding="utf-8") as f:
        json.dump(scored_mentions, f, indent=2, ensure_ascii=False)

    print(f"✓ Sentiment scored: {scored_path}")
    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
    for m in scored_mentions:
        sentiment_counts[m["sentiment_label"]] += 1
    print(f"  Positive: {sentiment_counts['positive']}")
    print(f"  Neutral: {sentiment_counts['neutral']}")
    print(f"  Negative: {sentiment_counts['negative']}")

    # Stage 4: Graph Construction
    print("\n" + "=" * 70)
    print("Stage 4: Graph Construction")
    print("=" * 70)

    # Load MP registry
    with open(args.golden_record, "r", encoding="utf-8") as f:
        golden_data = json.load(f)
        mp_registry = {}
        for mp in golden_data.get("mps", []):
            mp_registry[mp["node_id"]] = {
                "common_name": mp["common_name"],
                "party": mp.get("party", "Unknown"),
                "constituency": mp.get("constituency"),
                "current_portfolio": mp.get("current_portfolio"),
            }

    builder = GraphBuilder()
    session_graph = builder.build_session_graph(
        mentions=scored_mentions,
        session_id=args.session_id,
        date=args.date or "unknown",
        mp_registry=mp_registry,
    )

    # Stage 5: Export Dashboard-Ready Output
    print("\n" + "=" * 70)
    print("Stage 5: Export Dashboard-Ready Output")
    print("=" * 70)

    graph_json_path = output_dir / f"sample_session_{args.session_id}.json"
    builder.export_json(session_graph, str(graph_json_path))
    print(f"✓ Dashboard JSON: {graph_json_path}")

    if args.export_all:
        graphml_path = output_dir / f"{args.session_id}.graphml"
        nx_graph = builder.build_graph_from_session(session_graph)
        builder.export_graphml(nx_graph, str(graphml_path))
        print(f"✓ GraphML: {graphml_path}")

        csv_path = output_dir / f"{args.session_id}_edges.csv"
        builder.export_csv(session_graph, str(csv_path))
        print(f"✓ CSV: {csv_path}")

    print("\n" + "=" * 70)
    print("✅ Pipeline Complete!")
    print("=" * 70)
    print(f"\nDashboard-ready output: {graph_json_path}")
    print(f"Nodes: {session_graph.node_count} MPs")
    print(f"Edges: {session_graph.edge_count} interactions")


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

    # Extract command (Stage 2)
    extract_parser = subparsers.add_parser(
        "extract", help="Extract MP mentions from transcript (Stage 2)"
    )
    extract_parser.add_argument("transcript", help="Path to transcript JSON file")
    extract_parser.add_argument(
        "--golden-record",
        required=True,
        help="Path to Golden Record mps.json file",
    )
    extract_parser.add_argument(
        "--output", "-o", help="Output JSON file path (default: <session_id>_mentions.json)"
    )
    extract_parser.add_argument(
        "--date", help="Session date for temporal resolution (ISO format: YYYY-MM-DD)"
    )
    extract_parser.add_argument(
        "--use-spacy", action="store_true", help="Enable spaCy NER (requires model)"
    )

    # Sentiment command (Stage 3)
    sentiment_parser = subparsers.add_parser(
        "sentiment", help="Score sentiment for mentions (Stage 3)"
    )
    sentiment_parser.add_argument("mentions", help="Path to mentions JSON file")
    sentiment_parser.add_argument(
        "--output", "-o", help="Output JSON file path (default: <input>_scored.json)"
    )
    sentiment_parser.add_argument(
        "--model",
        default="facebook/bart-large-mnli",
        help="Sentiment model name (default: facebook/bart-large-mnli)",
    )

    # Build-graph command (Stage 4)
    build_graph_parser = subparsers.add_parser(
        "build-graph", help="Build session graph from mentions (Stage 4)"
    )
    build_graph_parser.add_argument("mentions", help="Path to scored mentions JSON file")
    build_graph_parser.add_argument(
        "--session-id", required=True, help="Session identifier"
    )
    build_graph_parser.add_argument(
        "--date", required=True, help="Session date (ISO format: YYYY-MM-DD)"
    )
    build_graph_parser.add_argument(
        "--output", "-o", help="Output JSON file path (default: output/sample_session_<id>.json)"
    )
    build_graph_parser.add_argument(
        "--golden-record", help="Path to Golden Record mps.json for MP metadata"
    )
    build_graph_parser.add_argument(
        "--graphml", action="store_true", help="Also export GraphML format"
    )
    build_graph_parser.add_argument(
        "--csv", action="store_true", help="Also export CSV edge list"
    )

    # Process command (Full Pipeline: Stages 1-5)
    process_parser = subparsers.add_parser(
        "process", help="Run full pipeline: audio → dashboard output (Stages 1-5)"
    )
    process_parser.add_argument("audio_file", help="Path to audio file")
    process_parser.add_argument(
        "--session-id", required=True, help="Session identifier"
    )
    process_parser.add_argument(
        "--golden-record",
        required=True,
        help="Path to Golden Record mps.json file",
    )
    process_parser.add_argument(
        "--output-dir",
        "-o",
        default="./output",
        help="Output directory for all files (default: ./output)",
    )
    process_parser.add_argument(
        "--date", help="Session date for temporal resolution (ISO format: YYYY-MM-DD)"
    )
    process_parser.add_argument(
        "--model", default="large-v3", help="Whisper model size (default: large-v3)"
    )
    process_parser.add_argument(
        "--device", default="cuda", choices=["cuda", "cpu"], help="Device to use"
    )
    process_parser.add_argument(
        "--backend",
        default="faster-whisper",
        choices=["faster-whisper", "insanely-fast-whisper"],
        help="Transcription backend",
    )
    process_parser.add_argument(
        "--language", default="en", help="Language code (default: en)"
    )
    process_parser.add_argument(
        "--hf-token", help="HuggingFace token (or set HF_TOKEN env var)"
    )
    process_parser.add_argument(
        "--no-diarization", action="store_true", help="Disable speaker diarization"
    )
    process_parser.add_argument(
        "--no-whisperx",
        action="store_false",
        dest="use_whisperx",
        help="Disable WhisperX alignment",
    )
    process_parser.add_argument(
        "--use-spacy", action="store_true", help="Enable spaCy NER for entity extraction"
    )
    process_parser.add_argument(
        "--sentiment-model",
        default="facebook/bart-large-mnli",
        help="Sentiment model name (default: facebook/bart-large-mnli)",
    )
    process_parser.add_argument(
        "--export-all",
        action="store_true",
        help="Export all formats (JSON, GraphML, CSV)",
    )

    args = parser.parse_args()

    if args.command == "transcribe":
        return transcribe_command(args)
    elif args.command == "batch":
        return batch_command(args)
    elif args.command == "info":
        return info_command(args)
    elif args.command == "extract":
        return extract_command(args)
    elif args.command == "sentiment":
        return sentiment_command(args)
    elif args.command == "build-graph":
        return build_graph_command(args)
    elif args.command == "process":
        return process_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
