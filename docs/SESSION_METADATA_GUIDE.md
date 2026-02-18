# Session Metadata Automation Guide

This guide explains how to use the automated session metadata extraction tools for batch processing parliamentary audio with Azure GPU.

## Overview

The session metadata automation eliminates the need for hardcoded metadata dictionaries. Instead, metadata (date, title) can be:

1. **Loaded from a JSON file** (recommended for production)
2. **Auto-extracted from YouTube** using `fetch_session_metadata.py`
3. **Omitted entirely** (falls back to video_id as session_id)

## Quick Start

### Option 1: With Pre-Existing Metadata JSON

If you already have a metadata JSON file:

```bash
python scripts/batch_transcribe.py archive/ \
    --output-dir output/ \
    --metadata examples/session_metadata.json \
    --model base \
    --device cuda
```

### Option 2: Extract Metadata from YouTube First

Step 1: Create a file with YouTube URLs (`urls.txt`):
```
https://www.youtube.com/watch?v=7cuPpo7ko78
https://www.youtube.com/watch?v=Y--YlPwcI8o
https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

Step 2: Extract metadata:
```bash
python scripts/fetch_session_metadata.py urls.txt \
    --output sessions.json \
    --parse-title-date
```

Step 3: Process audio with extracted metadata:
```bash
python scripts/batch_transcribe.py archive/ \
    --output-dir output/ \
    --metadata sessions.json
```

### Option 3: No Metadata (Fallback Mode)

Process audio files without metadata (uses video_id from filename as session_id):

```bash
python scripts/batch_transcribe.py archive/ \
    --output-dir output/ \
    --model base
```

## Metadata JSON Format

The metadata JSON file maps video IDs to session information:

```json
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
```

**Requirements:**
- **Keys**: Video IDs (11-character YouTube IDs, extracted from audio filenames)
- **date**: ISO 8601 format (YYYY-MM-DD), validated on load
- **title**: Optional, defaults to "Session {video_id}" if missing

## File Naming Convention

Audio files must be named with the video ID:

```
archive/
  ├── 7cuPpo7ko78.opus
  ├── Y--YlPwcI8o.mp3
  └── dQw4w9WgXcQ.wav
```

The script extracts the video ID from the filename stem (without extension).

## Script Reference

### `batch_transcribe.py`

**Purpose**: Batch process audio files with GPU acceleration and metadata tracking.

**Usage**:
```bash
python scripts/batch_transcribe.py <audio_dir> [options]
```

**Required Arguments**:
- `audio_dir`: Directory containing audio files (*.mp3, *.wav, *.opus, *.m4a, *.flac)

**Optional Arguments**:
- `--output-dir DIR`: Output directory for transcripts (default: `output/`)
- `--metadata FILE`: Path to JSON file containing session metadata
- `--model SIZE`: Whisper model size: tiny, base, small, medium, large-v2, large-v3 (default: base)
- `--device DEVICE`: Processing device: cuda or cpu (default: cuda)
- `--backend BACKEND`: Transcription backend: faster-whisper or insanely-fast-whisper (default: faster-whisper)
- `--no-diarization`: Disable speaker diarization

**Output**:
- Individual transcript JSON files: `{video_id}_transcript.json`
- Batch summary: `batch_summary.json`

**Example**:
```bash
python scripts/batch_transcribe.py archive/ \
    --output-dir transcripts/ \
    --metadata sessions.json \
    --model large-v3 \
    --device cuda \
    --backend faster-whisper
```

### `fetch_session_metadata.py`

**Purpose**: Extract metadata from YouTube videos using yt-dlp.

**Usage**:
```bash
python scripts/fetch_session_metadata.py <url_file> [options]
# OR
python scripts/fetch_session_metadata.py --urls <url1> <url2> ... [options]
```

**Input Methods**:
1. **File**: Text file with URLs (one per line, comments with #)
2. **CLI**: One or more URLs via `--urls` argument

**Optional Arguments**:
- `--output FILE, -o FILE`: Output JSON file (default: `sessions.json`)
- `--parse-title-date`: Attempt to parse date from video title (in addition to upload date)

**Date Parsing**:
The script can extract dates from:
1. **Upload date** (from YouTube metadata, always available)
2. **Title parsing** (with `--parse-title-date` flag)

Supported title date formats:
- "28 Jan 2026", "4 Feb 2026" (short month)
- "January 28, 2026" (long month)
- "2026-01-28" (ISO 8601)

**Example**:
```bash
# From file
python scripts/fetch_session_metadata.py urls.txt \
    --output sessions.json \
    --parse-title-date

# From command line
python scripts/fetch_session_metadata.py \
    --urls https://youtube.com/watch?v=7cuPpo7ko78 \
           https://youtube.com/watch?v=Y--YlPwcI8o \
    --output sessions.json
```

**Requirements**:
- `yt-dlp` must be installed: `pip install yt-dlp`

## Output Structure

Each processed session produces a JSON file with embedded metadata:

```json
{
  "transcript": {
    "session_id": "7cuPpo7ko78",
    "segments": [
      {
        "start_time": 0.0,
        "end_time": 5.2,
        "text": "The House is now in session...",
        "speaker_label": "SPEAKER_00",
        "confidence": 0.95
      }
    ]
  },
  "session_metadata": {
    "session_id": "7cuPpo7ko78",
    "date": "2026-01-28",
    "title": "House of Assembly 28 Jan 2026 Morning",
    "audio_file": "7cuPpo7ko78.opus",
    "processing_timestamp": "2026-02-18T13:00:00",
    "device": "cuda",
    "model": "base"
  }
}
```

## Validation and Error Handling

### Date Validation
- Dates must be in ISO 8601 format (YYYY-MM-DD)
- Invalid dates are logged and the entry is skipped
- If all entries are invalid, the script continues without metadata (fallback mode)

### Missing Files
- If metadata file is not found, an error is raised
- If audio directory is empty, an error is reported

### Processing Failures
- Individual file failures are logged but don't stop batch processing
- Failed files are tracked in `batch_summary.json`
- Script exits with error code 1 if any failures occurred

## Performance Tips

1. **Model Selection**: 
   - Use `base` or `small` for faster processing
   - Use `large-v3` for best accuracy (slower)

2. **GPU Acceleration**:
   - Ensure CUDA is available: `--device cuda`
   - Monitor GPU memory usage during batch processing

3. **Batch Size**:
   - Process in smaller batches if memory is limited
   - Use multiple output directories for different batches

## Troubleshooting

### "graphhansard not installed"
```bash
pip install -e ".[brain]"
```

### "yt-dlp not found"
```bash
pip install yt-dlp
```

### "Invalid date format"
Check that dates in metadata JSON are in ISO 8601 format (YYYY-MM-DD), not DD-MM-YYYY or MM/DD/YYYY.

### "No audio files found"
Ensure audio files have supported extensions: .mp3, .wav, .opus, .m4a, or .flac

### YouTube extraction fails
- Check internet connection
- Verify YouTube URL is correct
- Some videos may have download restrictions

## Migration from Hardcoded Dictionary

**Old approach** (hardcoded in script):
```python
SESSION_METADATA = {
    "7cuPpo7ko78": {"date": "2026-01-28", "title": "House of Assembly..."},
    "Y--YlPwcI8o": {"date": "2026-02-04", "title": "House of Assembly..."},
}
```

**New approach** (external JSON file):
1. Extract the dictionary to `sessions.json`
2. Run: `python scripts/batch_transcribe.py archive/ --metadata sessions.json`

**Benefits**:
- No code changes needed for new sessions
- Metadata can be version-controlled separately
- Can be auto-generated from YouTube
- Easier to maintain and audit

## See Also

- [GraphHansard README](../README.md)
- [Brain Pipeline Documentation](../src/graphhansard/brain/)
- [Test Examples](../tests/test_batch_transcribe.py)
