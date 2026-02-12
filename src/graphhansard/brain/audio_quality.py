"""Audio Quality Analysis — Quality assessment and filtering.

Implements BC-8, BC-9, and BC-10 requirements for handling variable audio
quality in parliamentary recordings. Detects low-quality segments and "hot mic"
scenarios where audio should be excluded from processing.

See SRD §11.3 for specification.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from graphhansard.brain.transcriber import TranscriptSegment

logger = logging.getLogger(__name__)


class AudioQualityFlag(str, Enum):
    """Quality flags for transcript segments."""

    OK = "ok"
    LOW_QUALITY = "low_quality"  # SNR < threshold
    HOT_MIC = "hot_mic"  # Off-the-record detected
    OVERLAPPING_VOICES = "overlapping_voices"  # Heckling detected
    MICROPHONE_CUT = "microphone_cut"  # Detected as silence/gap


class AudioQualityMetrics(BaseModel):
    """Audio quality metrics for a segment."""

    snr_db: float | None = Field(
        default=None, description="Signal-to-Noise Ratio in dB"
    )
    rms_energy: float | None = Field(
        default=None, description="Root Mean Square energy level"
    )
    is_low_confidence: bool = Field(
        default=False, description="Transcription confidence below threshold"
    )
    quality_flag: AudioQualityFlag = Field(
        default=AudioQualityFlag.OK, description="Overall quality assessment"
    )
    exclude_from_extraction: bool = Field(
        default=False,
        description="Whether to exclude from entity extraction (BC-9, BC-10)",
    )


class AudioQualityAnalyzer:
    """Analyzes audio quality and flags segments for exclusion.

    Implements:
    - BC-8: Variable quality handling (compression, echo, overlapping voices)
    - BC-9: SNR threshold detection (< 10dB flagged)
    - BC-10: Hot mic detection (off-the-record segments)
    """

    def __init__(
        self,
        snr_threshold_db: float = 10.0,
        low_confidence_threshold: float = 0.5,
        hot_mic_volume_ratio: float = 0.3,
        min_formal_indicators: int = 0,
    ):
        """Initialize the audio quality analyzer.

        Args:
            snr_threshold_db: SNR threshold in dB (default: 10.0 per BC-9)
            low_confidence_threshold: Confidence below which segment is
                flagged (default: 0.5)
            hot_mic_volume_ratio: Ratio of segment RMS to session average
                for hot mic detection (default: 0.3)
            min_formal_indicators: Minimum formal indicators to avoid
                hot mic flag (default: 0)
        """
        self.snr_threshold_db = snr_threshold_db
        self.low_confidence_threshold = low_confidence_threshold
        self.hot_mic_volume_ratio = hot_mic_volume_ratio
        self.min_formal_indicators = min_formal_indicators

    def estimate_snr(
        self, audio_data: np.ndarray, sample_rate: int = 16000
    ) -> float:
        """Estimate Signal-to-Noise Ratio for an audio segment.

        Energy-based estimation:
        1. Calculate RMS of entire segment (signal + noise)
        2. Estimate noise floor from quietest 10% of frames
        3. SNR = 20 * log10(signal_rms / noise_rms)

        For clean signals with no noise variation, returns a high SNR value.

        Args:
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate in Hz

        Returns:
            Estimated SNR in dB (higher is better)
        """
        if len(audio_data) == 0:
            return 0.0

        # Calculate RMS energy in frames (100ms windows)
        frame_length = int(0.1 * sample_rate)  # 100ms frames
        frames = []

        for i in range(0, len(audio_data), frame_length):
            frame = audio_data[i : i + frame_length]
            if len(frame) > 0:
                rms = np.sqrt(np.mean(frame**2))
                frames.append(rms)

        if len(frames) == 0:
            return 0.0

        frames = np.array(frames)

        # Signal RMS (mean of all frames)
        signal_rms = np.mean(frames)

        # Noise floor estimate (10th percentile of frame RMS values)
        noise_rms = np.percentile(frames, 10)

        # Check for edge case: pure signal with no variation (like sine wave)
        # In this case, noise_rms ≈ signal_rms, which would give low SNR
        # For such cases, use standard deviation of frames as noise estimate
        frame_std = np.std(frames)
        if frame_std < 0.01 * signal_rms:  # Very low variation
            # Use a small fraction of signal as effective noise floor
            # This represents that the signal is very consistent (high quality)
            # 0.001 * signal_rms gives SNR = 20*log10(1/0.001) = 60dB
            noise_rms = max(0.001 * signal_rms, 1e-10)

        if noise_rms == 0 or signal_rms == 0:
            return 0.0

        # Calculate SNR in dB
        snr_db = 20 * np.log10(signal_rms / noise_rms)

        return float(snr_db)

    def calculate_rms_energy(self, audio_data: np.ndarray) -> float:
        """Calculate RMS energy of an audio segment.

        Args:
            audio_data: Audio samples as numpy array

        Returns:
            RMS energy value
        """
        if len(audio_data) == 0:
            return 0.0

        rms = np.sqrt(np.mean(audio_data**2))
        return float(rms)

    def detect_hot_mic(
        self,
        segment_text: str,
        segment_rms: float,
        session_avg_rms: float,
        segment_confidence: float,
    ) -> bool:
        """Detect "hot mic" scenarios (off-the-record speech).

        Heuristics per BC-10:
        1. Volume significantly lower than chamber average
        2. No preceding formal speaker recognition patterns
        3. Conversational tone inconsistent with formal debate

        Args:
            segment_text: Transcribed text of the segment
            segment_rms: RMS energy of this segment
            session_avg_rms: Average RMS energy for the session
            segment_confidence: Transcription confidence

        Returns:
            True if segment appears to be off-the-record
        """
        # Check volume ratio
        if session_avg_rms > 0:
            volume_ratio = segment_rms / session_avg_rms
            is_quiet = volume_ratio < self.hot_mic_volume_ratio
        else:
            is_quiet = False

        # Check for formal debate indicators
        formal_indicators = [
            "Mr. Speaker",
            "Madam Speaker",
            "Mr. Chairman",
            "Madam Chairman",
            "honourable member",
            "honourable prime minister",
            "honourable minister",
            "point of order",
            "member for",
        ]

        # Case-insensitive check
        text_lower = segment_text.lower()
        has_formal_indicator = any(
            indicator.lower() in text_lower for indicator in formal_indicators
        )

        # Hot mic if:
        # - Volume is significantly lower than average AND
        # - No formal indicators present AND
        # - Text is not empty
        is_hot_mic = (
            is_quiet
            and not has_formal_indicator
            and len(segment_text.strip()) > 0
        )

        if is_hot_mic:
            logger.info(
                f"Hot mic detected: volume_ratio={volume_ratio:.2f}, "
                f"formal_indicators={has_formal_indicator}, "
                f"text_len={len(segment_text)}"
            )

        return is_hot_mic

    def detect_overlapping_voices(
        self, segment_confidence: float, segment_text: str
    ) -> bool:
        """Detect overlapping voices during heckling.

        Indicators:
        - Lower confidence transcription
        - Presence of multiple speaker patterns
        - Fragmented or incoherent text

        Args:
            segment_confidence: Transcription confidence
            segment_text: Transcribed text

        Returns:
            True if overlapping voices suspected
        """
        # Low confidence suggests poor audio quality (possibly overlapping)
        is_low_confidence = segment_confidence < self.low_confidence_threshold

        # Check for common heckling patterns
        heckling_patterns = [
            "[inaudible]",
            "[crosstalk]",
            "[overlapping]",
            "[multiple speakers]",
        ]
        has_heckling_marker = any(
            pattern in segment_text.lower() for pattern in heckling_patterns
        )

        # Very fragmented text (many short words)
        words = segment_text.split()
        if len(words) > 5:
            avg_word_length = sum(len(w) for w in words) / len(words)
            is_fragmented = avg_word_length < 3.0  # Very short words
        else:
            is_fragmented = False

        return (
            is_low_confidence and (has_heckling_marker or is_fragmented)
        ) or has_heckling_marker

    def detect_microphone_cut(
        self, segment_duration: float, segment_text: str
    ) -> bool:
        """Detect microphone cuts (silence gaps).

        Indicators:
        - Very short duration with minimal text
        - Empty or near-empty transcription
        - Excessive duration with no text

        Args:
            segment_duration: Duration in seconds
            segment_text: Transcribed text

        Returns:
            True if microphone cut suspected
        """
        text_stripped = segment_text.strip()

        # Empty transcription
        if len(text_stripped) == 0:
            return True

        # Very long segment with very little text (silence with noise)
        if segment_duration > 5.0 and len(text_stripped) < 10:
            return True

        return False

    def analyze_segment(
        self,
        segment: TranscriptSegment,
        audio_data: np.ndarray | None = None,
        sample_rate: int = 16000,
        session_avg_rms: float | None = None,
    ) -> AudioQualityMetrics:
        """Analyze audio quality for a single transcript segment.

        Args:
            segment: Transcript segment to analyze
            audio_data: Optional audio samples for SNR calculation
            sample_rate: Audio sample rate
            session_avg_rms: Average RMS for the session (for hot mic detection)

        Returns:
            AudioQualityMetrics with quality assessment
        """
        metrics = AudioQualityMetrics()

        # Calculate SNR if audio data available
        if audio_data is not None:
            metrics.snr_db = self.estimate_snr(audio_data, sample_rate)
            metrics.rms_energy = self.calculate_rms_energy(audio_data)

            # Flag low SNR per BC-9
            if metrics.snr_db < self.snr_threshold_db:
                metrics.quality_flag = AudioQualityFlag.LOW_QUALITY
                metrics.exclude_from_extraction = True
                logger.info(
                    f"Low quality detected: SNR={metrics.snr_db:.1f}dB "
                    f"(threshold={self.snr_threshold_db}dB)"
                )

        # Check confidence
        metrics.is_low_confidence = (
            segment.confidence < self.low_confidence_threshold
        )

        # Calculate segment duration
        segment_duration = segment.end_time - segment.start_time

        # Detect microphone cuts
        if self.detect_microphone_cut(segment_duration, segment.text):
            metrics.quality_flag = AudioQualityFlag.MICROPHONE_CUT
            # Don't exclude - just flag for information
            logger.debug(f"Microphone cut detected: duration={segment_duration:.1f}s")

        # Detect overlapping voices (heckling)
        elif self.detect_overlapping_voices(segment.confidence, segment.text):
            metrics.quality_flag = AudioQualityFlag.OVERLAPPING_VOICES
            # Flag but don't automatically exclude unless also low quality
            logger.info(
                f"Overlapping voices detected: "
                f"confidence={segment.confidence:.2f}"
            )

        # Detect hot mic (BC-10)
        if audio_data is not None and session_avg_rms is not None:
            if self.detect_hot_mic(
                segment.text,
                metrics.rms_energy or 0.0,
                session_avg_rms,
                segment.confidence,
            ):
                metrics.quality_flag = AudioQualityFlag.HOT_MIC
                metrics.exclude_from_extraction = True
                logger.info("Hot mic segment flagged for exclusion")

        return metrics

    def analyze_session(
        self,
        segments: list[TranscriptSegment],
        audio_file_path: str | None = None,
    ) -> list[AudioQualityMetrics]:
        """Analyze audio quality for all segments in a session.

        Args:
            segments: List of transcript segments
            audio_file_path: Optional path to audio file for detailed analysis

        Returns:
            List of AudioQualityMetrics, one per segment
        """
        metrics_list = []

        # If audio file provided, load it for RMS calculation
        session_avg_rms = None
        if audio_file_path:
            try:
                import librosa

                # Load audio (this may be slow for large files)
                audio, sr = librosa.load(audio_file_path, sr=16000, mono=True)

                # Calculate session average RMS
                session_avg_rms = float(np.sqrt(np.mean(audio**2)))

                logger.info(f"Session average RMS: {session_avg_rms:.6f}")
            except Exception as e:
                logger.warning(
                    f"Could not load audio file for detailed analysis: {e}"
                )
                audio = None
                sr = 16000

        # Analyze each segment
        for i, segment in enumerate(segments):
            # Extract audio segment if available
            audio_segment = None
            if audio_file_path and session_avg_rms is not None:
                try:
                    import librosa

                    # Load specific segment
                    audio_segment, sr = librosa.load(
                        audio_file_path,
                        sr=16000,
                        mono=True,
                        offset=segment.start_time,
                        duration=segment.end_time - segment.start_time,
                    )
                except Exception as e:
                    logger.debug(
                        f"Could not extract audio for segment {i}: {e}"
                    )

            # Analyze segment
            metrics = self.analyze_segment(
                segment,
                audio_data=audio_segment,
                sample_rate=16000,
                session_avg_rms=session_avg_rms,
            )

            metrics_list.append(metrics)

        # Log summary statistics
        excluded_count = sum(1 for m in metrics_list if m.exclude_from_extraction)
        low_quality_count = sum(
            1 for m in metrics_list if m.quality_flag == AudioQualityFlag.LOW_QUALITY
        )
        hot_mic_count = sum(
            1 for m in metrics_list if m.quality_flag == AudioQualityFlag.HOT_MIC
        )

        logger.info(
            f"Quality analysis complete: {len(segments)} segments analyzed, "
            f"{excluded_count} excluded ({low_quality_count} low quality, "
            f"{hot_mic_count} hot mic)"
        )

        return metrics_list
