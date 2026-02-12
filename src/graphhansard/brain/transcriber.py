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
    Supports both faster-whisper and insanely-fast-whisper backends.
    """

    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        backend: str = "faster-whisper",
    ):
        """Initialize the Transcriber.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
            device: Device to run on ("cuda" or "cpu")
            compute_type: Computation precision ("float16", "int8", "float32")
            backend: "faster-whisper" (CTranslate2) or "insanely-fast-whisper" (Flash Attention 2)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.backend = backend
        self._model = None

    def _normalize_confidence(self, log_prob: float) -> float:
        """Convert log probability to confidence score in [0, 1] range.
        
        Whisper's avg_logprob is typically in range [-inf, 0], where:
        - 0.0 = perfect confidence (prob=1.0)
        - -1.0 = ~0.37 confidence (prob=exp(-1))
        - -2.0 = ~0.14 confidence (prob=exp(-2))
        
        We use exp(log_prob) bounded to [0, 1].
        """
        import math
        try:
            confidence = math.exp(log_prob)
            return max(0.0, min(1.0, confidence))
        except (ValueError, OverflowError):
            # Handle edge cases (very negative log_prob)
            return 0.0

    def _load_model(self):
        """Lazy-load the transcription model."""
        if self._model is not None:
            return self._model

        if self.backend == "faster-whisper":
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise ImportError(
                    "faster-whisper not installed. Install with: pip install faster-whisper"
                )

            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        elif self.backend == "insanely-fast-whisper":
            try:
                import torch
                from transformers import pipeline
            except ImportError:
                raise ImportError(
                    "transformers and torch required for insanely-fast-whisper. "
                    "Install with: pip install transformers torch"
                )

            device_id = 0 if self.device == "cuda" and torch.cuda.is_available() else -1
            self._model = pipeline(
                "automatic-speech-recognition",
                model=f"openai/whisper-{self.model_size}",
                device=device_id,
                torch_dtype=torch.float16 if device_id >= 0 else torch.float32,
            )
        else:
            raise ValueError(
                f"Unknown backend: {self.backend}. Use 'faster-whisper' or 'insanely-fast-whisper'"
            )

        return self._model

    def transcribe(
        self, audio_path: str, language: str = "en", return_word_timestamps: bool = True
    ) -> dict:
        """Transcribe an audio file with word-level timestamps.

        Args:
            audio_path: Path to audio file
            language: Language code (default: "en")
            return_word_timestamps: Whether to include word-level timestamps

        Returns:
            Dictionary with transcription results including segments and word timestamps
        """
        model = self._load_model()

        if self.backend == "faster-whisper":
            segments, info = model.transcribe(
                audio_path,
                language=language,
                word_timestamps=return_word_timestamps,
                vad_filter=True,  # Voice activity detection to filter silences
            )

            # Convert generator to list and extract segments
            result_segments = []
            for segment in segments:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "confidence": self._normalize_confidence(segment.avg_logprob),  # Transform log prob to [0,1]
                    "words": [],
                }

                if return_word_timestamps and segment.words:
                    segment_dict["words"] = [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "confidence": word.probability,
                        }
                        for word in segment.words
                    ]

                result_segments.append(segment_dict)

            return {
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "segments": result_segments,
            }

        elif self.backend == "insanely-fast-whisper":
            result = model(
                audio_path,
                return_timestamps="word" if return_word_timestamps else True,
            )

            # Transform to consistent format
            segments = []
            for chunk in result.get("chunks", []):
                segment_dict = {
                    "start": chunk["timestamp"][0],
                    "end": chunk["timestamp"][1],
                    "text": chunk["text"],
                    "confidence": 1.0,  # Not directly available in this backend
                    "words": [],
                }

                # Extract word-level timestamps if available
                if return_word_timestamps and "words" in chunk:
                    segment_dict["words"] = [
                        {
                            "word": word["text"],
                            "start": word["timestamp"][0],
                            "end": word["timestamp"][1],
                            "confidence": word.get("probability", 1.0),
                        }
                        for word in chunk["words"]
                    ]

                segments.append(segment_dict)

            return {
                "language": language,
                "language_probability": 1.0,
                "duration": 0.0,  # Not directly available
                "segments": segments,
            }

    def transcribe_to_transcript(
        self, audio_path: str, session_id: str, language: str = "en"
    ) -> DiarizedTranscript:
        """Transcribe audio and return a DiarizedTranscript (without diarization).

        Note: This creates segments without speaker labels. Use the Diarizer
        to add speaker attribution.

        Args:
            audio_path: Path to audio file
            session_id: Session identifier
            language: Language code

        Returns:
            DiarizedTranscript with unlabeled segments
        """
        result = self.transcribe(audio_path, language=language)

        segments = []
        for seg in result["segments"]:
            # Calculate average confidence from word confidences
            if seg["words"]:
                avg_confidence = sum(w["confidence"] for w in seg["words"]) / len(
                    seg["words"]
                )
            else:
                avg_confidence = seg["confidence"]

            segments.append(
                TranscriptSegment(
                    speaker_label="UNKNOWN",  # No diarization yet
                    start_time=seg["start"],
                    end_time=seg["end"],
                    text=seg["text"],
                    confidence=avg_confidence,
                    words=[
                        WordToken(
                            word=w["word"],
                            start=w["start"],
                            end=w["end"],
                            confidence=w["confidence"],
                        )
                        for w in seg["words"]
                    ],
                )
            )

        return DiarizedTranscript(session_id=session_id, segments=segments)
