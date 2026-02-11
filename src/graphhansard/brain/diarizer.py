"""Stage 1b — Speaker diarization using pyannote.audio.

Segments audio by individual speaker turns and merges with transcription
output via whisperx alignment. See SRD §8.2 (BR-2, BR-5, BR-7).
"""

from __future__ import annotations


class Diarizer:
    """Speaker diarization using pyannote.audio 3.x.

    See SRD §8.2.2 for specification. Requires HuggingFace token
    and acceptance of pyannote model terms.
    """

    def __init__(self, hf_token: str | None = None, device: str = "cuda"):
        raise NotImplementedError("Diarizer not yet implemented — see Issue #9")

    def diarize(self, audio_path: str) -> list[dict]:
        """Perform speaker diarization on an audio file.

        Returns a list of segments with speaker labels and timestamps.
        """
        raise NotImplementedError

    def align_with_transcript(self, diarization: list[dict], transcript: dict) -> dict:
        """Merge diarization output with Whisper transcript via whisperx."""
        raise NotImplementedError
