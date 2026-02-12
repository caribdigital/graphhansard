"""Layer 2 — The Brain: NLP & Graph Construction Pipeline.

Transforms raw audio into structured, sentiment-scored political interaction
networks through four sequential stages:
1. Transcription & Diarization
2. Entity Extraction & Co-reference Resolution
3. Sentiment Scoring
4. Graph Construction & Metric Computation
"""

from graphhansard.brain.diarizer import Diarizer
from graphhansard.brain.pipeline import TranscriptionPipeline, create_pipeline
from graphhansard.brain.transcriber import (
    DiarizedTranscript,
    Transcriber,
    TranscriptSegment,
    WordToken,
)

__all__ = [
    "Transcriber",
    "Diarizer",
    "TranscriptionPipeline",
    "create_pipeline",
    "DiarizedTranscript",
    "TranscriptSegment",
    "WordToken",
]
