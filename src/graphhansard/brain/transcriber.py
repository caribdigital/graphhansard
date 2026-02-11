"""Stage 1a — Audio transcription using Whisper.

Transcribes parliamentary session audio to text with word-level timestamps.
See SRD §8.2 (BR-1, BR-3, BR-4, BR-6) for specification.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WordToken(BaseModel):
    """A single word with timestamp and confidence."""

    word: str
    start: float
    end: float
    confidence: float


class TranscriptSegment(BaseModel):
    """A speaker-attributed segment of a transcript."""

    speaker_label: str = Field(description="Diarization label, e.g. 'SPEAKER_00'")
    speaker_node_id: str | None = Field(
        default=None, description="Resolved MP node_id"
    )
    start_time: float
    end_time: float
    text: str
    confidence: float = Field(description="Average word-level confidence (0.0-1.0)")
    words: list[WordToken] = Field(default_factory=list)


class DiarizedTranscript(BaseModel):
    """Complete diarized transcript for a single session."""

    session_id: str = Field(description="Links to SessionAudio.video_id")
    segments: list[TranscriptSegment]


class Transcriber:
    """Transcribes audio using Whisper large-v3.

    See SRD §8.2 for specification.
    """

    def __init__(self, model_size: str = "large-v3", device: str = "cuda"):
        raise NotImplementedError("Transcriber not yet implemented — see Issue #9")

    def transcribe(self, audio_path: str) -> DiarizedTranscript:
        """Transcribe an audio file and return a diarized transcript."""
        raise NotImplementedError
