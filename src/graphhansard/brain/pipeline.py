"""Stage 1 Pipeline — Complete transcription and diarization pipeline.

Orchestrates Whisper transcription with pyannote diarization to produce
structured, speaker-attributed transcripts. Includes audio quality analysis
per BC-8, BC-9, BC-10. See SRD §8.2 and §11.3.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from graphhansard.brain.audio_quality import AudioQualityAnalyzer
from graphhansard.brain.diarizer import Diarizer
from graphhansard.brain.transcriber import (
    DiarizedTranscript,
    Transcriber,
    TranscriptSegment,
    WordToken,
)

logger = logging.getLogger(__name__)


class TranscriptionPipeline:
    """Complete pipeline for transcription and speaker diarization.

    This class orchestrates the entire process:
    1. Transcribe audio using Whisper
    2. Perform speaker diarization using pyannote
    3. Align and merge results to produce speaker-attributed segments
    4. Analyze audio quality and flag low-quality/hot-mic segments (BC-8, BC-9, BC-10)
    """

    def __init__(
        self,
        transcriber: Transcriber | None = None,
        diarizer: Diarizer | None = None,
        use_whisperx: bool = True,
        quality_analyzer: AudioQualityAnalyzer | None = None,
        enable_quality_analysis: bool = True,
    ):
        """Initialize the pipeline.

        Args:
            transcriber: Transcriber instance. If None, creates default.
            diarizer: Diarizer instance. If None, creates default
                (requires HF_TOKEN).
            use_whisperx: Whether to use WhisperX for advanced alignment
                (recommended).
            quality_analyzer: AudioQualityAnalyzer instance. If None,
                creates default.
            enable_quality_analysis: Whether to perform audio quality
                analysis (BC-8, BC-9, BC-10).
        """
        self.transcriber = transcriber or Transcriber()
        self.diarizer = diarizer
        self.use_whisperx = use_whisperx
        self.quality_analyzer = quality_analyzer or AudioQualityAnalyzer()
        self.enable_quality_analysis = enable_quality_analysis

    def process(
        self,
        audio_path: str,
        session_id: str,
        language: str = "en",
        enable_diarization: bool = True,
    ) -> DiarizedTranscript:
        """Process an audio file through the complete pipeline.

        Includes audio quality analysis per BC-8, BC-9, BC-10.

        Args:
            audio_path: Path to audio file
            session_id: Unique session identifier
            language: Language code (default: "en")
            enable_diarization: Whether to perform speaker diarization

        Returns:
            DiarizedTranscript with speaker-attributed segments and quality flags
        """
        # Step 1: Transcribe audio
        transcript_result = self.transcriber.transcribe(
            audio_path, language=language, return_word_timestamps=True
        )

        # Step 2: Perform diarization if enabled
        transcript = None
        if enable_diarization and self.diarizer:
            if self.use_whisperx:
                # Use WhisperX for advanced alignment
                aligned_result = self.diarizer.align_with_whisperx(
                    audio_path, transcript_result, language=language
                )
                transcript = self._convert_whisperx_to_transcript(
                    aligned_result, session_id
                )
            else:
                # Use simple overlap-based alignment
                diarization = self.diarizer.diarize(audio_path)
                aligned_segments = self.diarizer.align_with_transcript(
                    diarization, transcript_result["segments"]
                )
                transcript = self._convert_to_transcript(aligned_segments, session_id)
        else:
            # No diarization - return transcript with UNKNOWN speaker
            transcript = self._convert_to_transcript(
                transcript_result["segments"], session_id, default_speaker="UNKNOWN"
            )

        # Step 3: Perform audio quality analysis (BC-8, BC-9, BC-10)
        if self.enable_quality_analysis:
            self._apply_quality_analysis(transcript, audio_path)

        return transcript

    def _apply_quality_analysis(
        self, transcript: DiarizedTranscript, audio_path: str
    ) -> None:
        """Apply audio quality analysis to transcript segments.

        Updates segments in-place with quality flags per BC-8, BC-9, BC-10.

        Args:
            transcript: DiarizedTranscript to analyze
            audio_path: Path to audio file for detailed analysis
        """
        logger.info(
            f"Performing audio quality analysis on "
            f"{len(transcript.segments)} segments"
        )

        # Analyze all segments
        quality_metrics = self.quality_analyzer.analyze_session(
            transcript.segments, audio_path
        )

        # Apply quality metadata to segments
        for segment, metrics in zip(transcript.segments, quality_metrics):
            segment.quality_flag = metrics.quality_flag.value
            segment.snr_db = metrics.snr_db
            segment.exclude_from_extraction = metrics.exclude_from_extraction

        # Log summary
        excluded = sum(1 for s in transcript.segments if s.exclude_from_extraction)
        logger.info(
            f"Quality analysis complete: {excluded}/{len(transcript.segments)} "
            f"segments flagged for exclusion"
        )

    def _convert_to_transcript(
        self,
        segments: list[dict],
        session_id: str,
        default_speaker: str = "UNKNOWN",
    ) -> DiarizedTranscript:
        """Convert aligned segments to DiarizedTranscript format."""
        transcript_segments = []

        for seg in segments:
            # Calculate average confidence
            if seg.get("words"):
                avg_confidence = sum(w["confidence"] for w in seg["words"]) / len(
                    seg["words"]
                )
            else:
                avg_confidence = seg.get("confidence", 1.0)

            transcript_segments.append(
                TranscriptSegment(
                    speaker_label=seg.get("speaker", default_speaker),
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
                        for w in seg.get("words", [])
                    ],
                )
            )

        return DiarizedTranscript(session_id=session_id, segments=transcript_segments)

    def _convert_whisperx_to_transcript(
        self, whisperx_result: dict, session_id: str
    ) -> DiarizedTranscript:
        """Convert WhisperX aligned result to DiarizedTranscript format."""
        transcript_segments = []

        for seg in whisperx_result.get("segments", []):
            # Get speaker label (may be at segment or word level)
            speaker = seg.get("speaker", "UNKNOWN")

            # Extract words with timestamps
            words = []
            if "words" in seg:
                for word_data in seg["words"]:
                    # WhisperX may assign speaker at word level
                    if "speaker" in word_data and speaker == "UNKNOWN":
                        speaker = word_data["speaker"]

                    words.append(
                        WordToken(
                            word=word_data.get("word", word_data.get("text", "")),
                            start=word_data["start"],
                            end=word_data["end"],
                            confidence=word_data.get(
                                "score", word_data.get("confidence", 1.0)
                            ),
                        )
                    )

            # Calculate average confidence
            if words:
                avg_confidence = sum(w.confidence for w in words) / len(words)
            else:
                avg_confidence = 1.0

            transcript_segments.append(
                TranscriptSegment(
                    speaker_label=speaker,
                    start_time=seg["start"],
                    end_time=seg["end"],
                    text=seg["text"],
                    confidence=avg_confidence,
                    words=words,
                )
            )

        return DiarizedTranscript(session_id=session_id, segments=transcript_segments)

    def process_batch(
        self,
        audio_files: list[tuple[str, str]],
        output_dir: str,
        language: str = "en",
        enable_diarization: bool = True,
    ) -> list[Path]:
        """Process multiple audio files in batch.

        Args:
            audio_files: List of (audio_path, session_id) tuples
            output_dir: Directory to save transcript JSON files
            language: Language code
            enable_diarization: Whether to perform speaker diarization

        Returns:
            List of paths to generated transcript files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        generated_files = []

        for audio_path, session_id in audio_files:
            # Process the file
            transcript = self.process(
                audio_path, session_id, language, enable_diarization
            )

            # Save to JSON
            output_file = output_path / f"{session_id}_transcript.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(transcript.model_dump(), f, indent=2, ensure_ascii=False)

            generated_files.append(output_file)

        return generated_files

    def save_transcript(self, transcript: DiarizedTranscript, output_path: str):
        """Save a DiarizedTranscript to JSON file.

        Args:
            transcript: The transcript to save
            output_path: Path to output JSON file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript.model_dump(), f, indent=2, ensure_ascii=False)

    def load_transcript(self, json_path: str) -> DiarizedTranscript:
        """Load a DiarizedTranscript from JSON file.

        Args:
            json_path: Path to JSON file

        Returns:
            DiarizedTranscript instance
        """
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return DiarizedTranscript.model_validate(data)


def create_pipeline(
    model_size: str = "large-v3",
    device: str = "cuda",
    hf_token: str | None = None,
    use_whisperx: bool = True,
    backend: str = "faster-whisper",
    enable_quality_analysis: bool = True,
    snr_threshold_db: float = 10.0,
) -> TranscriptionPipeline:
    """Factory function to create a configured pipeline.

    Args:
        model_size: Whisper model size
        device: Device to run on ("cuda" or "cpu")
        hf_token: HuggingFace token for pyannote (required for diarization)
        use_whisperx: Whether to use WhisperX alignment
        backend: Transcription backend
            ("faster-whisper" or "insanely-fast-whisper")
        enable_quality_analysis: Whether to enable audio quality analysis
            (BC-8, BC-9, BC-10)
        snr_threshold_db: SNR threshold in dB for quality flagging
            (default: 10.0 per BC-9)

    Returns:
        Configured TranscriptionPipeline instance
    """
    transcriber = Transcriber(
        model_size=model_size, device=device, backend=backend
    )

    diarizer = None
    if hf_token:
        diarizer = Diarizer(hf_token=hf_token, device=device)

    quality_analyzer = None
    if enable_quality_analysis:
        quality_analyzer = AudioQualityAnalyzer(snr_threshold_db=snr_threshold_db)

    return TranscriptionPipeline(
        transcriber=transcriber,
        diarizer=diarizer,
        use_whisperx=use_whisperx,
        quality_analyzer=quality_analyzer,
        enable_quality_analysis=enable_quality_analysis,
    )
