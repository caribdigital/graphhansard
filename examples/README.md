# GraphHansard Examples

This directory contains practical examples demonstrating how to use GraphHansard's various components.

## Transcription & Diarization

### transcribe_session.py

A complete example showing how to transcribe parliamentary audio with optional speaker diarization.

**Basic Usage (Transcription only):**
```bash
python examples/transcribe_session.py audio.wav
```

**With Speaker Diarization:**
```bash
# Set HuggingFace token first
export HF_TOKEN="hf_your_token_here"

# Run with diarization
python examples/transcribe_session.py audio.wav --with-diarization
```

**Advanced Options:**
```bash
# Use larger model for better accuracy
python examples/transcribe_session.py audio.wav --model large-v3

# Specify output file
python examples/transcribe_session.py audio.wav --output results/transcript.json
```

**Output:**
- Creates a JSON file with the transcript
- Shows summary statistics
- Displays first few segments as preview

## Sentiment Analysis

### sentiment_demo.py

Demonstrates the sentiment scoring pipeline for MP-to-MP mentions. This shows how to classify parliamentary references as positive, neutral, or negative, and how to detect parliamentary markers like "point of order" and heckling.

**Usage:**
```bash
python examples/sentiment_demo.py
```

**Features:**
- Zero-shot sentiment classification using BART
- Parliamentary marker detection
- Batch processing demonstration
- Sample parliamentary contexts with expected results

**Note:** Requires internet access on first run to download the BART model (~1.6GB). Subsequent runs use the cached model.

## More Examples (Coming Soon)

- Entity extraction from transcripts
- Graph construction from mentions
- Dashboard visualization

## Requirements

Install the brain dependencies:
```bash
pip install -e ".[brain]"
```

For GPU acceleration, install CUDA-enabled PyTorch:
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Getting Help

For detailed documentation:
- See `src/graphhansard/brain/README.md` for transcription pipeline docs
- Run `python -m graphhansard.brain.cli info` for system information
- Check the main README.md for overall project documentation

## License

MIT License - See LICENSE file for details
