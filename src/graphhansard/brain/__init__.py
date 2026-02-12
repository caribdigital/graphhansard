"""Layer 2 — The Brain: NLP & Graph Construction Pipeline.

Transforms raw audio into structured, sentiment-scored political interaction
networks through four sequential stages:
1. Transcription & Diarization
2. Entity Extraction & Co-reference Resolution
3. Sentiment Scoring
4. Graph Construction & Metric Computation

Includes Bahamian Creole normalization utilities (BC-1, BC-2, BC-3).
Includes audio quality analysis per BC-8, BC-9, BC-10 (SRD §11.3).
"""

try:
    from graphhansard.brain.audio_quality import (
        AudioQualityAnalyzer,
        AudioQualityFlag,
        AudioQualityMetrics,
    )
except ImportError:
    AudioQualityAnalyzer = None
    AudioQualityFlag = None
    AudioQualityMetrics = None

from graphhansard.brain.creole_utils import (
    normalize_bahamian_creole,
    normalize_th_stopping,
    normalize_vowel_shifts,
)
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
    "AudioQualityAnalyzer",
    "AudioQualityFlag",
    "AudioQualityMetrics",
    "normalize_bahamian_creole",
    "normalize_th_stopping",
    "normalize_vowel_shifts",
]
