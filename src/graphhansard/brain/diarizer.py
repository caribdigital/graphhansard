"""Stage 1b — Speaker diarization using pyannote.audio.

Segments audio by individual speaker turns and merges with transcription
output via whisperx alignment. See SRD §8.2 (BR-2, BR-5, BR-7).
"""

from __future__ import annotations

import os
from typing import Any


class Diarizer:
    """Speaker diarization using pyannote.audio 3.x.

    See SRD §8.2.2 for specification. Requires HuggingFace token
    and acceptance of pyannote model terms.
    """

    def __init__(
        self,
        hf_token: str | None = None,
        device: str = "cuda",
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ):
        """Initialize the Diarizer.

        Args:
            hf_token: HuggingFace token for pyannote model access. If None, will try HF_TOKEN env var.
            device: Device to run on ("cuda" or "cpu")
            min_speakers: Minimum number of speakers (None for automatic)
            max_speakers: Maximum number of speakers (None for automatic)
        """
        self.hf_token = hf_token or os.environ.get("HF_TOKEN")
        if not self.hf_token:
            raise ValueError(
                "HuggingFace token required for pyannote. "
                "Provide via hf_token parameter or HF_TOKEN environment variable. "
                "Get token at: https://huggingface.co/settings/tokens"
            )

        self.device = device
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self._pipeline = None

    def _load_pipeline(self):
        """Lazy-load the pyannote diarization pipeline."""
        if self._pipeline is not None:
            return self._pipeline

        try:
            from pyannote.audio import Pipeline
        except ImportError:
            raise ImportError(
                "pyannote.audio not installed. Install with: pip install pyannote.audio"
            )

        # Load the speaker diarization pipeline
        self._pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1", use_auth_token=self.hf_token
        )

        # Move to specified device
        if self.device == "cuda":
            try:
                import torch

                if torch.cuda.is_available():
                    self._pipeline.to(torch.device("cuda"))
            except ImportError:
                pass

        return self._pipeline

    def diarize(self, audio_path: str) -> list[dict]:
        """Perform speaker diarization on an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            List of diarization segments with speaker labels and timestamps:
            [{"speaker": "SPEAKER_00", "start": 0.5, "end": 3.2}, ...]
        """
        pipeline = self._load_pipeline()

        # Run diarization
        diarization_result = pipeline(
            audio_path,
            min_speakers=self.min_speakers,
            max_speakers=self.max_speakers,
        )

        # Convert to list of segments
        segments = []
        for turn, _, speaker in diarization_result.itertracks(yield_label=True):
            segments.append(
                {"speaker": speaker, "start": turn.start, "end": turn.end}
            )

        return segments

    def align_with_transcript(
        self, diarization: list[dict], transcript_segments: list[dict]
    ) -> list[dict]:
        """Merge diarization output with transcript segments.

        This performs a simple overlap-based alignment. For each transcript segment,
        it finds the diarization speaker with the most overlap and assigns that speaker.

        Args:
            diarization: List of diarization segments from diarize()
            transcript_segments: List of transcript segments with start/end times

        Returns:
            List of aligned segments with speaker labels added
        """
        aligned_segments = []

        for trans_seg in transcript_segments:
            trans_start = trans_seg["start"]
            trans_end = trans_seg["end"]

            # Find best matching speaker based on overlap
            best_speaker = "UNKNOWN"
            max_overlap = 0.0

            for diar_seg in diarization:
                # Calculate overlap
                overlap_start = max(trans_start, diar_seg["start"])
                overlap_end = min(trans_end, diar_seg["end"])
                overlap = max(0, overlap_end - overlap_start)

                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = diar_seg["speaker"]

            # Create aligned segment
            aligned_seg = trans_seg.copy()
            aligned_seg["speaker"] = best_speaker
            aligned_segments.append(aligned_seg)

        return aligned_segments

    def align_with_whisperx(
        self, audio_path: str, transcript_result: dict, language: str = "en"
    ) -> dict:
        """Use WhisperX for advanced alignment of transcript with diarization.

        WhisperX provides more accurate alignment using forced alignment and
        better speaker attribution.

        Args:
            audio_path: Path to audio file
            transcript_result: Whisper transcription result
            language: Language code

        Returns:
            Aligned transcript with speaker labels
        """
        try:
            import whisperx
        except ImportError:
            raise ImportError(
                "whisperx not installed. Install with: pip install whisperx"
            )

        # Load audio
        audio = whisperx.load_audio(audio_path)

        # Align whisper output
        model_a, metadata = whisperx.load_align_model(
            language_code=language, device=self.device
        )
        result_aligned = whisperx.align(
            transcript_result["segments"],
            model_a,
            metadata,
            audio,
            self.device,
            return_char_alignments=False,
        )

        # Perform diarization with WhisperX
        diarize_model = whisperx.DiarizationPipeline(
            use_auth_token=self.hf_token, device=self.device
        )
        diarize_segments = diarize_model(
            audio,
            min_speakers=self.min_speakers,
            max_speakers=self.max_speakers,
        )

        # Assign speaker labels to segments
        result_with_speakers = whisperx.assign_word_speakers(
            diarize_segments, result_aligned
        )

        return result_with_speakers
