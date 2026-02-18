# Layer 2 — The Brain: Transcription & Diarization Pipeline

This module implements the core transcription and speaker diarization pipeline for GraphHansard, transforming raw parliamentary audio into structured, speaker-attributed transcripts with word-level timestamps.

## Features

- **Transcription**: Whisper-based speech-to-text with word-level timestamps
- **Speaker Diarization**: pyannote.audio for identifying different speakers
- **Integration**: WhisperX for optimal alignment between transcription and diarization
- **GPU Acceleration**: CUDA support for fast inference (6x+ real-time on RTX 3080+)
- **Multiple Backends**: Choose between `faster-whisper` (lower VRAM) or `insanely-fast-whisper` (faster on RTX GPUs)

## Requirements (SRD §8.2)

| ID | Requirement | Status |
|----|-------------|--------|
| BR-1 | Transcribe audio using Whisper with word-level timestamps | ✅ Implemented |
| BR-2 | Speaker diarization to segment by individual speaker turns | ✅ Implemented |
| BR-3 | Output structured transcript with speaker, timestamps, text | ✅ Implemented |
| BR-4 | WER ≤ 15% on Bahamian parliamentary speech | 🧪 Needs validation |
| BR-5 | DER ≤ 20% on multi-speaker House sessions | 🧪 Needs validation |
| BR-6 | GPU acceleration (1 hr audio in ≤10 min on RTX 3080) | ✅ Supported |
| BR-7 | Handle audio artifacts (echo, cross-talk, etc.) | ✅ VAD filtering |
| BR-8 | Manual correction interface (editable JSON) | ✅ JSON output |

## Installation

### Basic Installation

```bash
# Install core dependencies
pip install -e .

# Install brain dependencies
pip install -e ".[brain]"
```

### GPU Setup (Recommended)

```bash
# Install with CUDA support
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -e ".[brain]"
```

### HuggingFace Token Setup

Speaker diarization requires a HuggingFace token:

1. Get token: https://huggingface.co/settings/tokens
2. Accept model terms: https://huggingface.co/pyannote/speaker-diarization-3.1
3. Set environment variable:

```bash
export HF_TOKEN="hf_your_token_here"
```

## Usage

### Command-Line Interface

#### Single File Transcription

```bash
# Basic transcription (no diarization)
python -m graphhansard.brain.cli transcribe audio.wav \
  --session-id "session_2024_01_15" \
  --no-diarization

# Full pipeline with diarization
python -m graphhansard.brain.cli transcribe audio.wav \
  --session-id "session_2024_01_15" \
  --hf-token "hf_your_token"

# Advanced options
python -m graphhansard.brain.cli transcribe audio.wav \
  --session-id "session_2024_01_15" \
  --model large-v3 \
  --device cuda \
  --backend faster-whisper \
  --language en \
  --output transcript.json
```

#### Batch Processing

```bash
# Process entire directory
python -m graphhansard.brain.cli batch ./audio_files \
  --output-dir ./transcripts \
  --hf-token "hf_your_token"
```

#### System Information

```bash
python -m graphhansard.brain.cli info
```

### Python API

#### Quick Start

```python
from graphhansard.brain import create_pipeline

# Create pipeline (transcription only)
pipeline = create_pipeline(
    model_size="large-v3",
    device="cuda",
    backend="faster-whisper"
)

# Process audio
transcript = pipeline.process(
    audio_path="session_audio.wav",
    session_id="session_2024_01_15",
    enable_diarization=False
)

# Save result
pipeline.save_transcript(transcript, "output.json")
```

#### With Diarization

```python
from graphhansard.brain import create_pipeline
import os

# Create pipeline with diarization
pipeline = create_pipeline(
    model_size="large-v3",
    device="cuda",
    hf_token=os.environ.get("HF_TOKEN"),
    use_whisperx=True
)

# Process with speaker attribution
transcript = pipeline.process(
    audio_path="session_audio.wav",
    session_id="session_2024_01_15",
    language="en",
    enable_diarization=True
)

# Access results
for segment in transcript.segments:
    print(f"[{segment.speaker_label}] {segment.start_time:.1f}s - {segment.end_time:.1f}s")
    print(f"  {segment.text}")
    print(f"  Confidence: {segment.confidence:.2f}")
```

#### Manual Component Usage

```python
from graphhansard.brain import Transcriber, Diarizer

# Initialize components separately
transcriber = Transcriber(
    model_size="large-v3",
    device="cuda",
    backend="faster-whisper"
)

diarizer = Diarizer(
    hf_token="hf_your_token",
    device="cuda",
    min_speakers=2,
    max_speakers=10
)

# Transcribe
transcript_result = transcriber.transcribe("audio.wav")

# Diarize
diarization = diarizer.diarize("audio.wav")

# Align
aligned = diarizer.align_with_transcript(
    diarization,
    transcript_result["segments"]
)
```

#### Batch Processing

```python
from pathlib import Path
from graphhansard.brain import create_pipeline

pipeline = create_pipeline(
    device="cuda",
    hf_token="hf_your_token"
)

# Prepare file list
audio_files = [
    ("session_001.wav", "session_2024_01_15"),
    ("session_002.wav", "session_2024_01_22"),
]

# Process batch
output_files = pipeline.process_batch(
    audio_files=audio_files,
    output_dir="./transcripts",
    enable_diarization=True
)

print(f"Processed {len(output_files)} files")
```

## Output Format

### DiarizedTranscript JSON Schema

```json
{
  "session_id": "session_2024_01_15",
  "segments": [
    {
      "speaker_label": "SPEAKER_00",
      "speaker_node_id": null,
      "start_time": 0.0,
      "end_time": 5.2,
      "text": "Madam Speaker, I rise on a point of order.",
      "confidence": 0.92,
      "words": [
        {
          "word": "Madam",
          "start": 0.0,
          "end": 0.4,
          "confidence": 0.95
        },
        {
          "word": "Speaker",
          "start": 0.5,
          "end": 0.9,
          "confidence": 0.93
        }
      ]
    }
  ]
}
```

### Fields

- **session_id**: Unique identifier linking to source audio
- **speaker_label**: Diarization label (e.g., "SPEAKER_00", "SPEAKER_01")
- **speaker_node_id**: Resolved MP node ID (populated by entity extraction stage)
- **start_time**: Segment start in seconds
- **end_time**: Segment end in seconds
- **text**: Transcribed text
- **confidence**: Average word-level confidence (0.0-1.0)
- **words**: Array of word-level tokens with timestamps

## Model Selection

### Whisper Models

| Model | Parameters | Speed (CPU) | WER | Use Case |
|-------|-----------|-------------|-----|----------|
| tiny | 39M | ~10x realtime | Higher | Quick testing |
| base | 74M | ~7x realtime | High | Development |
| small | 244M | ~4x realtime | Medium | Fast preview |
| medium | 769M | ~2x realtime | Low | Good balance |
| large-v2 | 1550M | ~1x realtime | Lower | High accuracy |
| **large-v3** | 1550M | ~1x realtime | **Lowest** | **Production (recommended)** |

### Backends

**faster-whisper** (recommended for most users):
- Based on CTranslate2
- Lower VRAM usage
- Good speed on CPU and GPU
- Easy installation

**insanely-fast-whisper** (for RTX GPUs):
- Uses Flash Attention 2
- Faster on modern GPUs (RTX 30/40 series)
- Requires more VRAM
- Best for batch processing

## Performance

### GPU Acceleration (RTX 3080)

With `large-v3` model:
- Transcription only: ~6-8x realtime
- With diarization: ~5-6x realtime
- Target: 1 hour audio in ≤10 minutes ✅

### CPU Performance

With `large-v3` model:
- Transcription: ~1x realtime (slow)
- Not recommended for production

## Limitations & Known Issues

1. **Dialectal Variation**: WER may be higher on Bahamian English
   - Solution: Future fine-tuning on Bahamian parliamentary corpus
   
2. **Speaker Overlaps**: Cross-talk and heckling may confuse diarization
   - Solution: VAD filtering helps; manual review for critical segments

3. **Speaker Count**: Diarization accuracy decreases with >10 speakers
   - Solution: Set `min_speakers` and `max_speakers` if known

4. **Audio Quality**: Background noise affects both transcription and diarization
   - Solution: Audio preprocessing (planned for v1.1)

## Testing

```bash
# Run tests
pytest tests/test_brain.py -v

# Run with coverage
pytest tests/test_brain.py --cov=graphhansard.brain --cov-report=html
```

## Contributing

When improving this module:

1. Maintain backward compatibility with the JSON schema
2. Update tests for new features
3. Measure WER/DER on test corpus
4. Document performance impact
5. Handle edge cases (silence, overlaps, artifacts)

## Speaker Identity Resolution

### Overview

The speaker resolution module bridges the gap between diarization labels (SPEAKER_XX) and actual MP identities by using heuristic-based pattern matching. This enables "who said what" analysis in the graph.

### Heuristics Implemented

1. **Chair Detection** (Confidence: 0.6-0.9)
   - Identifies Speaker/Deputy Speaker by procedural language
   - Patterns: "The Chair recognizes", "Order, order", "The House will come to order"
   - Typically resolves 1-2 speakers per session

2. **Recognition Chaining** (Confidence: 0.75)
   - Links recognized MPs to their subsequent speech
   - Patterns: "I recognize the Member for [constituency]", "The Honourable [Name] has the floor"
   - Resolves 3-5 additional speakers per session

3. **Portfolio Fingerprinting** (Confidence: 0.3-0.6)
   - Matches discussion topics to MP portfolios
   - Keywords: finance, tourism, health, education, etc.
   - Lower confidence, used as supplementary signal

4. **Self-Reference Detection** (Placeholder)
   - Future enhancement to integrate with entity extraction
   - Will detect when speaker mentions themselves

### Usage

Enable speaker resolution in the pipeline:

```python
from graphhansard.brain import create_pipeline

pipeline = create_pipeline(
    model_size="large-v3",
    enable_speaker_resolution=True,
    golden_record_path="golden_record/mps.json"
)

transcript = pipeline.process(
    audio_path="session.wav",
    session_id="2024-01-15"
)

# Segments now have speaker_node_id populated
for segment in transcript.segments:
    print(f"{segment.speaker_label} -> {segment.speaker_node_id}")
```

Or via CLI:

```bash
python -m graphhansard.brain process audio.wav \
  --session-id "2024-01-15" \
  --golden-record golden_record/mps.json \
  --enable-speaker-resolution
```

### Resolution Quality

- **Expected Resolution Rate**: 40-60% of speakers per session
- **Precision Target**: ≥95% (no false mappings)
- **Recall Target**: ≥40% (resolve at least Chair + 3 MPs)

Unresolved speakers remain as SPEAKER_XX to avoid false mappings.

### Demo Script

Run the demonstration to see speaker resolution in action:

```bash
python scripts/demo_speaker_resolution.py
```

## References

- SRD §8.2: Stage 1 — Transcription & Diarization
- Whisper paper: https://arxiv.org/abs/2212.04356
- pyannote.audio: https://github.com/pyannote/pyannote-audio
- WhisperX: https://github.com/m-bain/whisperx

## License

MIT License - See LICENSE file for details
