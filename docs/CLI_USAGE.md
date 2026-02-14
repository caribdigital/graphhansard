# GraphHansard Brain CLI - End-to-End Pipeline Usage

This document describes the new CLI commands added to support Stages 2-5 of the data processing pipeline.

## Quick Reference

```bash
# Stage 1: Transcription (existing)
python -m graphhansard.brain transcribe <audio.mp3> --session-id <id>

# Stage 2: Entity Extraction
python -m graphhansard.brain extract <transcript.json> --golden-record mps.json

# Stage 3: Sentiment Scoring
python -m graphhansard.brain sentiment <mentions.json>

# Stage 4: Graph Construction
python -m graphhansard.brain build-graph <mentions.json> --session-id <id> --date <date>

# Full Pipeline (Stages 1-5)
python -m graphhansard.brain process <audio.mp3> --session-id <id> --golden-record mps.json
```

## Command Details

### extract - Stage 2: Entity Extraction

Extract MP mentions from a diarized transcript.

```bash
python -m graphhansard.brain extract <transcript.json> \
  --golden-record golden_record/mps.json \
  [--output mentions.json] \
  [--date 2024-01-15] \
  [--use-spacy]
```

**Arguments:**
- `transcript` - Path to transcript JSON file (from Stage 1)
- `--golden-record` - Path to Golden Record mps.json file (required)
- `--output` - Output file path (default: `<session_id>_mentions.json`)
- `--date` - Session date for temporal resolution (ISO format: YYYY-MM-DD)
- `--use-spacy` - Enable spaCy NER (requires spaCy model installation)

**Output:** JSON file containing extracted mention records

**Example:**
```bash
python -m graphhansard.brain extract \
  transcripts/session_001_transcript.json \
  --golden-record golden_record/mps.json \
  --date 2024-01-15 \
  --output mentions/session_001_mentions.json
```

### sentiment - Stage 3: Sentiment Scoring

Score sentiment for each mention using zero-shot classification.

```bash
python -m graphhansard.brain sentiment <mentions.json> \
  [--output scored_mentions.json] \
  [--model facebook/bart-large-mnli]
```

**Arguments:**
- `mentions` - Path to mentions JSON file (from Stage 2)
- `--output` - Output file path (default: `<input>_scored.json`)
- `--model` - Sentiment model name (default: facebook/bart-large-mnli)

**Output:** JSON file with sentiment labels and confidence scores added to each mention

**Example:**
```bash
python -m graphhansard.brain sentiment \
  mentions/session_001_mentions.json \
  --output mentions/session_001_scored.json
```

### build-graph - Stage 4: Graph Construction

Build session graph from scored mentions and export dashboard-ready output.

```bash
python -m graphhansard.brain build-graph <mentions.json> \
  --session-id <session_id> \
  --date <date> \
  [--output output.json] \
  [--golden-record mps.json] \
  [--graphml] \
  [--csv]
```

**Arguments:**
- `mentions` - Path to scored mentions JSON file (from Stage 3)
- `--session-id` - Session identifier (required)
- `--date` - Session date in ISO format (required)
- `--output` - Output JSON file path (default: `output/sample_session_<id>.json`)
- `--golden-record` - Path to Golden Record for MP metadata
- `--graphml` - Also export GraphML format
- `--csv` - Also export CSV edge list

**Output:** Dashboard-ready JSON with node metrics and edge data

**Example:**
```bash
python -m graphhansard.brain build-graph \
  mentions/session_001_scored.json \
  --session-id session_001 \
  --date 2024-01-15 \
  --golden-record golden_record/mps.json \
  --output output/sample_session_session_001.json \
  --graphml \
  --csv
```

### process - Full Pipeline (Stages 1-5)

Run the complete pipeline from audio to dashboard-ready output.

```bash
python -m graphhansard.brain process <audio_file> \
  --session-id <session_id> \
  --golden-record golden_record/mps.json \
  [--output-dir output/] \
  [--date 2024-01-15] \
  [--model large-v3] \
  [--device cuda] \
  [--backend faster-whisper] \
  [--language en] \
  [--hf-token <token>] \
  [--no-diarization] \
  [--no-whisperx] \
  [--use-spacy] \
  [--sentiment-model facebook/bart-large-mnli] \
  [--export-all]
```

**Arguments:**
- `audio_file` - Path to audio file
- `--session-id` - Session identifier (required)
- `--golden-record` - Path to Golden Record mps.json (required)
- `--output-dir` - Output directory for all files (default: ./output)
- `--date` - Session date for temporal resolution (ISO format)
- `--model` - Whisper model size (default: large-v3)
- `--device` - Device to use: cuda or cpu (default: cuda)
- `--backend` - Transcription backend (default: faster-whisper)
- `--language` - Language code (default: en)
- `--hf-token` - HuggingFace token for diarization
- `--no-diarization` - Disable speaker diarization
- `--no-whisperx` - Disable WhisperX alignment
- `--use-spacy` - Enable spaCy NER for entity extraction
- `--sentiment-model` - Sentiment model name (default: facebook/bart-large-mnli)
- `--export-all` - Export all formats (JSON, GraphML, CSV)

**Output:** 
- `<output-dir>/<session_id>_transcript.json` - Diarized transcript
- `<output-dir>/<session_id>_mentions.json` - Extracted mentions
- `<output-dir>/<session_id>_mentions_scored.json` - Scored mentions
- `<output-dir>/sample_session_<session_id>.json` - Dashboard-ready graph

**Example:**
```bash
python -m graphhansard.brain process \
  audio/parliament_session_001.mp3 \
  --session-id session_001 \
  --golden-record golden_record/mps.json \
  --output-dir output/ \
  --date 2024-01-15 \
  --device cuda \
  --export-all
```

## Workflow Examples

### Example 1: Step-by-Step Processing

Process each stage separately for more control:

```bash
# Stage 1: Transcribe audio
python -m graphhansard.brain transcribe \
  audio/session_001.mp3 \
  --session-id session_001 \
  --output transcripts/session_001_transcript.json

# Stage 2: Extract mentions
python -m graphhansard.brain extract \
  transcripts/session_001_transcript.json \
  --golden-record golden_record/mps.json \
  --date 2024-01-15 \
  --output mentions/session_001_mentions.json

# Stage 3: Score sentiment
python -m graphhansard.brain sentiment \
  mentions/session_001_mentions.json \
  --output mentions/session_001_scored.json

# Stage 4: Build graph
python -m graphhansard.brain build-graph \
  mentions/session_001_scored.json \
  --session-id session_001 \
  --date 2024-01-15 \
  --golden-record golden_record/mps.json \
  --output output/sample_session_session_001.json \
  --graphml --csv
```

### Example 2: One-Command Pipeline

Run the full pipeline in a single command:

```bash
python -m graphhansard.brain process \
  audio/session_001.mp3 \
  --session-id session_001 \
  --golden-record golden_record/mps.json \
  --output-dir output/ \
  --date 2024-01-15 \
  --export-all
```

### Example 3: Re-process Existing Transcript

If you already have a transcript, start from Stage 2:

```bash
# Start from entity extraction
python -m graphhansard.brain extract \
  existing_transcript.json \
  --golden-record golden_record/mps.json \
  --output mentions.json

# Continue with sentiment
python -m graphhansard.brain sentiment mentions.json

# Build graph
python -m graphhansard.brain build-graph \
  mentions_scored.json \
  --session-id session_001 \
  --date 2024-01-15
```

## Output Format

The final dashboard-ready output (`sample_session_<id>.json`) contains:

```json
{
  "session_id": "session_001",
  "date": "2024-01-15",
  "graph_file": "graphs/session_001.graphml",
  "node_count": 3,
  "edge_count": 2,
  "nodes": [
    {
      "node_id": "mp_davis_brave",
      "common_name": "Brave Davis",
      "party": "PLP",
      "constituency": "Cat Island, Rum Cay and San Salvador",
      "current_portfolio": "Prime Minister",
      "degree_in": 1,
      "degree_out": 1,
      "betweenness": 0.5,
      "eigenvector": 0.707,
      "closeness": 0.667,
      "structural_role": ["hub", "force_multiplier"],
      "community_id": 0
    }
  ],
  "edges": [
    {
      "source_node_id": "mp_davis_brave",
      "target_node_id": "mp_pintard_michael",
      "total_mentions": 1,
      "positive_count": 1,
      "neutral_count": 0,
      "negative_count": 0,
      "net_sentiment": 1.0,
      "semantic_type": "mention",
      "is_procedural": false,
      "mention_details": [
        {
          "timestamp_start": 0.0,
          "timestamp_end": 5.5,
          "context_window": "I thank the honourable Member...",
          "sentiment_label": "positive",
          "raw_mention": "the honourable Member"
        }
      ]
    }
  ],
  "modularity_score": 0.25
}
```

## Requirements

- Python 3.11+
- graphhansard package installed: `pip install -e .`
- Brain dependencies: `pip install -e ".[brain]"`
- For diarization: HuggingFace token with access to pyannote.audio models

## Next Steps

After running the pipeline, the output files can be:
- Loaded by the GraphHansard Dashboard for visualization
- Imported into network analysis tools (Gephi, yEd) using GraphML format
- Analyzed using the CSV edge list in data science tools
- Further processed or aggregated for longitudinal analysis
