"""Tests for audio quality analysis module.

Tests BC-8, BC-9, BC-10 requirements for handling variable audio quality.
"""

import numpy as np
import pytest

from graphhansard.brain.audio_quality import (
    AudioQualityAnalyzer,
    AudioQualityFlag,
    AudioQualityMetrics,
)
from graphhansard.brain.transcriber import TranscriptSegment


class TestAudioQualityMetrics:
    """Test AudioQualityMetrics schema validation."""

    def test_metrics_creation(self):
        """Test creating AudioQualityMetrics."""
        metrics = AudioQualityMetrics(
            snr_db=15.5,
            rms_energy=0.05,
            is_low_confidence=False,
            quality_flag=AudioQualityFlag.OK,
            exclude_from_extraction=False,
        )
        assert metrics.snr_db == 15.5
        assert metrics.rms_energy == 0.05
        assert metrics.quality_flag == AudioQualityFlag.OK
        assert not metrics.exclude_from_extraction

    def test_metrics_defaults(self):
        """Test default values."""
        metrics = AudioQualityMetrics()
        assert metrics.snr_db is None
        assert metrics.quality_flag == AudioQualityFlag.OK
        assert not metrics.exclude_from_extraction


class TestAudioQualityAnalyzer:
    """Test AudioQualityAnalyzer class."""

    def test_analyzer_initialization(self):
        """Test analyzer initializes with correct defaults."""
        analyzer = AudioQualityAnalyzer()
        assert analyzer.snr_threshold_db == 10.0
        assert analyzer.low_confidence_threshold == 0.5

    def test_analyzer_custom_thresholds(self):
        """Test analyzer with custom thresholds."""
        analyzer = AudioQualityAnalyzer(
            snr_threshold_db=15.0,
            low_confidence_threshold=0.7,
        )
        assert analyzer.snr_threshold_db == 15.0
        assert analyzer.low_confidence_threshold == 0.7


class TestSNREstimation:
    """Test SNR (Signal-to-Noise Ratio) estimation (BC-9)."""

    def test_snr_clean_signal(self):
        """Test SNR estimation for clean signal."""
        analyzer = AudioQualityAnalyzer()

        # Create a clean signal (sine wave)
        sample_rate = 16000
        duration = 1.0
        frequency = 440.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)

        snr = analyzer.estimate_snr(audio, sample_rate)

        # Clean signal should have high SNR
        assert snr > 10.0

    def test_snr_noisy_signal(self):
        """Test SNR estimation for noisy signal."""
        analyzer = AudioQualityAnalyzer()

        # Create a noisy signal (mostly noise)
        sample_rate = 16000
        duration = 1.0
        audio = np.random.normal(0, 0.1, int(sample_rate * duration)).astype(
            np.float32
        )

        snr = analyzer.estimate_snr(audio, sample_rate)

        # Noisy signal should have lower SNR
        assert snr < 10.0

    def test_snr_mixed_signal(self):
        """Test SNR with signal + noise."""
        analyzer = AudioQualityAnalyzer()

        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Signal
        signal = np.sin(2 * np.pi * 440 * t)

        # Add moderate noise
        noise = np.random.normal(0, 0.1, len(signal))
        audio = (signal + noise).astype(np.float32)

        snr = analyzer.estimate_snr(audio, sample_rate)

        # Mixed signal should have good SNR (signal is stronger than noise)
        assert 0.0 < snr < 80.0  # Reasonable upper bound

    def test_snr_empty_audio(self):
        """Test SNR with empty audio."""
        analyzer = AudioQualityAnalyzer()
        audio = np.array([], dtype=np.float32)

        snr = analyzer.estimate_snr(audio, 16000)
        assert snr == 0.0

    def test_snr_silent_audio(self):
        """Test SNR with silent audio."""
        analyzer = AudioQualityAnalyzer()
        audio = np.zeros(16000, dtype=np.float32)

        snr = analyzer.estimate_snr(audio, 16000)
        assert snr == 0.0


class TestRMSEnergy:
    """Test RMS energy calculation."""

    def test_rms_calculation(self):
        """Test RMS energy calculation."""
        analyzer = AudioQualityAnalyzer()

        # Test with known values
        audio = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        rms = analyzer.calculate_rms_energy(audio)

        expected_rms = np.sqrt(np.mean(audio**2))
        assert abs(rms - expected_rms) < 1e-6

    def test_rms_empty_audio(self):
        """Test RMS with empty audio."""
        analyzer = AudioQualityAnalyzer()
        audio = np.array([], dtype=np.float32)

        rms = analyzer.calculate_rms_energy(audio)
        assert rms == 0.0


class TestHotMicDetection:
    """Test hot mic detection (BC-10)."""

    def test_hot_mic_quiet_informal(self):
        """Test hot mic detection with quiet, informal speech."""
        analyzer = AudioQualityAnalyzer(hot_mic_volume_ratio=0.3)

        # Quiet segment, no formal indicators
        is_hot_mic = analyzer.detect_hot_mic(
            segment_text="Yeah, I think that's a good point",
            segment_rms=0.01,
            session_avg_rms=0.05,  # Segment is 20% of average (< 30%)
            segment_confidence=0.9,
        )

        assert is_hot_mic

    def test_hot_mic_quiet_formal(self):
        """Test that formal speech is not flagged as hot mic."""
        analyzer = AudioQualityAnalyzer(hot_mic_volume_ratio=0.3)

        # Quiet but has formal indicator
        is_hot_mic = analyzer.detect_hot_mic(
            segment_text="Mr. Speaker, I rise to make a point",
            segment_rms=0.01,
            session_avg_rms=0.05,
            segment_confidence=0.9,
        )

        assert not is_hot_mic

    def test_hot_mic_normal_volume(self):
        """Test that normal volume speech is not flagged."""
        analyzer = AudioQualityAnalyzer(hot_mic_volume_ratio=0.3)

        # Normal volume
        is_hot_mic = analyzer.detect_hot_mic(
            segment_text="This is normal conversation",
            segment_rms=0.04,
            session_avg_rms=0.05,  # 80% of average
            segment_confidence=0.9,
        )

        assert not is_hot_mic

    def test_hot_mic_empty_text(self):
        """Test that empty text is not flagged as hot mic."""
        analyzer = AudioQualityAnalyzer(hot_mic_volume_ratio=0.3)

        is_hot_mic = analyzer.detect_hot_mic(
            segment_text="",
            segment_rms=0.01,
            session_avg_rms=0.05,
            segment_confidence=0.9,
        )

        assert not is_hot_mic

    def test_hot_mic_various_formal_indicators(self):
        """Test various formal speech indicators."""
        analyzer = AudioQualityAnalyzer(hot_mic_volume_ratio=0.3)

        formal_phrases = [
            "Madam Speaker, I object",
            "The honourable member makes a point",
            "Point of order, Mr. Chairman",
            "The Honourable Prime Minister",
            "The member for Nassau",
        ]

        for phrase in formal_phrases:
            is_hot_mic = analyzer.detect_hot_mic(
                segment_text=phrase,
                segment_rms=0.01,
                session_avg_rms=0.05,
                segment_confidence=0.9,
            )
            assert not is_hot_mic, f"Formal phrase incorrectly flagged: {phrase}"


class TestOverlappingVoicesDetection:
    """Test overlapping voices detection (BC-8)."""

    def test_overlapping_low_confidence(self):
        """Test detection with low confidence."""
        analyzer = AudioQualityAnalyzer(low_confidence_threshold=0.5)

        is_overlapping = analyzer.detect_overlapping_voices(
            segment_confidence=0.3,
            segment_text="This is some text",
        )

        # Low confidence alone might indicate overlapping
        # But without markers or fragmentation, not conclusive
        assert not is_overlapping

    def test_overlapping_with_markers(self):
        """Test detection with explicit markers."""
        analyzer = AudioQualityAnalyzer()

        is_overlapping = analyzer.detect_overlapping_voices(
            segment_confidence=0.8,
            segment_text="Mr. Speaker [crosstalk] I rise to",
        )

        assert is_overlapping

    def test_overlapping_fragmented_low_confidence(self):
        """Test detection with fragmented text and low confidence."""
        analyzer = AudioQualityAnalyzer(low_confidence_threshold=0.5)

        # Very short words suggest fragmentation
        is_overlapping = analyzer.detect_overlapping_voices(
            segment_confidence=0.3,
            segment_text="I a go no we do",  # Average word length: 1.83
        )

        assert is_overlapping

    def test_no_overlapping_normal_speech(self):
        """Test that normal speech is not flagged."""
        analyzer = AudioQualityAnalyzer()

        is_overlapping = analyzer.detect_overlapping_voices(
            segment_confidence=0.9,
            segment_text="Mr. Speaker, I rise to address this important matter",
        )

        assert not is_overlapping


class TestMicrophoneCutDetection:
    """Test microphone cut detection (BC-8)."""

    def test_microphone_cut_empty_text(self):
        """Test detection with empty transcription."""
        analyzer = AudioQualityAnalyzer()

        is_cut = analyzer.detect_microphone_cut(
            segment_duration=2.0,
            segment_text="",
        )

        assert is_cut

    def test_microphone_cut_long_silence(self):
        """Test detection with long duration and minimal text."""
        analyzer = AudioQualityAnalyzer()

        is_cut = analyzer.detect_microphone_cut(
            segment_duration=8.0,
            segment_text="um",  # Very little text for 8 seconds
        )

        assert is_cut

    def test_no_microphone_cut_normal_segment(self):
        """Test that normal segments are not flagged."""
        analyzer = AudioQualityAnalyzer()

        is_cut = analyzer.detect_microphone_cut(
            segment_duration=5.0,
            segment_text="Mr. Speaker, I rise to make an important point about this matter",
        )

        assert not is_cut

    def test_microphone_cut_whitespace_only(self):
        """Test that whitespace-only text is detected."""
        analyzer = AudioQualityAnalyzer()

        is_cut = analyzer.detect_microphone_cut(
            segment_duration=3.0,
            segment_text="   \n\t  ",
        )

        assert is_cut


class TestSegmentAnalysis:
    """Test complete segment analysis."""

    def test_analyze_high_quality_segment(self):
        """Test analyzing a high-quality segment."""
        analyzer = AudioQualityAnalyzer()

        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=5.0,
            text="Mr. Speaker, I rise to address this matter with great concern",
            confidence=0.95,
        )

        # Create clean audio
        audio = np.sin(
            2 * np.pi * 440 * np.linspace(0, 1, 16000)
        ).astype(np.float32)

        metrics = analyzer.analyze_segment(
            segment, audio_data=audio, session_avg_rms=0.05
        )

        assert metrics.quality_flag == AudioQualityFlag.OK
        assert not metrics.exclude_from_extraction
        assert metrics.snr_db is not None
        assert metrics.snr_db > 10.0

    def test_analyze_low_snr_segment(self):
        """Test analyzing segment with low SNR (BC-9)."""
        analyzer = AudioQualityAnalyzer(snr_threshold_db=10.0)

        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=1.0,
            text="Some text",
            confidence=0.8,
        )

        # Create noisy audio
        audio = np.random.normal(0, 0.1, 16000).astype(np.float32)

        metrics = analyzer.analyze_segment(
            segment, audio_data=audio, session_avg_rms=0.05
        )

        assert metrics.quality_flag == AudioQualityFlag.LOW_QUALITY
        assert metrics.exclude_from_extraction
        assert metrics.snr_db is not None
        assert metrics.snr_db < 10.0

    def test_analyze_hot_mic_segment(self):
        """Test analyzing hot mic segment (BC-10)."""
        analyzer = AudioQualityAnalyzer(hot_mic_volume_ratio=0.3)

        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=2.0,
            text="Yeah, that's interesting",
            confidence=0.85,
        )

        # Create quiet audio (hot mic scenario)
        audio = (
            np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)) * 0.1
        ).astype(np.float32)

        metrics = analyzer.analyze_segment(
            segment,
            audio_data=audio,
            session_avg_rms=0.5,  # Much higher than segment
        )

        assert metrics.quality_flag == AudioQualityFlag.HOT_MIC
        assert metrics.exclude_from_extraction

    def test_analyze_overlapping_voices_segment(self):
        """Test analyzing segment with overlapping voices (BC-8)."""
        analyzer = AudioQualityAnalyzer()

        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=3.0,
            text="Mr. Speaker [inaudible] point of order",
            confidence=0.4,
        )

        metrics = analyzer.analyze_segment(segment)

        assert metrics.quality_flag == AudioQualityFlag.OVERLAPPING_VOICES
        # Overlapping voices don't automatically exclude
        # (unless also low quality)

    def test_analyze_microphone_cut_segment(self):
        """Test analyzing microphone cut segment (BC-8)."""
        analyzer = AudioQualityAnalyzer()

        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=8.0,
            text="",
            confidence=0.0,
        )

        metrics = analyzer.analyze_segment(segment)

        assert metrics.quality_flag == AudioQualityFlag.MICROPHONE_CUT

    def test_analyze_segment_without_audio(self):
        """Test analyzing segment without audio data."""
        analyzer = AudioQualityAnalyzer()

        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=5.0,
            text="Mr. Speaker, I rise to speak",
            confidence=0.9,
        )

        metrics = analyzer.analyze_segment(segment, audio_data=None)

        # Without audio, can't calculate SNR
        assert metrics.snr_db is None
        assert metrics.rms_energy is None
        # Should still analyze other aspects
        assert metrics.quality_flag in [
            AudioQualityFlag.OK,
            AudioQualityFlag.MICROPHONE_CUT,
            AudioQualityFlag.OVERLAPPING_VOICES,
        ]


class TestSessionAnalysis:
    """Test session-wide analysis."""

    def test_analyze_session_basic(self):
        """Test analyzing multiple segments."""
        analyzer = AudioQualityAnalyzer()

        segments = [
            TranscriptSegment(
                speaker_label="SPEAKER_00",
                start_time=0.0,
                end_time=5.0,
                text="First segment with good quality",
                confidence=0.95,
            ),
            TranscriptSegment(
                speaker_label="SPEAKER_01",
                start_time=5.0,
                end_time=10.0,
                text="Second segment also good",
                confidence=0.92,
            ),
        ]

        metrics_list = analyzer.analyze_session(segments)

        assert len(metrics_list) == 2
        assert all(isinstance(m, AudioQualityMetrics) for m in metrics_list)

    def test_analyze_session_mixed_quality(self):
        """Test session with mixed quality segments."""
        analyzer = AudioQualityAnalyzer()

        segments = [
            TranscriptSegment(
                speaker_label="SPEAKER_00",
                start_time=0.0,
                end_time=5.0,
                text="Good quality segment",
                confidence=0.95,
            ),
            TranscriptSegment(
                speaker_label="SPEAKER_01",
                start_time=5.0,
                end_time=10.0,
                text="",  # Microphone cut
                confidence=0.0,
            ),
            TranscriptSegment(
                speaker_label="SPEAKER_00",
                start_time=10.0,
                end_time=12.0,
                text="[inaudible] [crosstalk]",  # Overlapping
                confidence=0.3,
            ),
        ]

        metrics_list = analyzer.analyze_session(segments)

        assert len(metrics_list) == 3
        assert metrics_list[0].quality_flag == AudioQualityFlag.OK
        assert metrics_list[1].quality_flag == AudioQualityFlag.MICROPHONE_CUT
        assert metrics_list[2].quality_flag == AudioQualityFlag.OVERLAPPING_VOICES


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_session_avg_rms(self):
        """Test hot mic detection with zero session average."""
        analyzer = AudioQualityAnalyzer()

        # Should not crash with division by zero
        is_hot_mic = analyzer.detect_hot_mic(
            segment_text="Test",
            segment_rms=0.01,
            session_avg_rms=0.0,
            segment_confidence=0.9,
        )

        assert isinstance(is_hot_mic, bool)

    def test_very_short_segment(self):
        """Test analysis of very short segment."""
        analyzer = AudioQualityAnalyzer()

        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=0.1,
            text="Hi",
            confidence=0.8,
        )

        metrics = analyzer.analyze_segment(segment)
        assert isinstance(metrics, AudioQualityMetrics)

    def test_very_long_segment(self):
        """Test analysis of very long segment."""
        analyzer = AudioQualityAnalyzer()

        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=300.0,  # 5 minutes
            text="A " * 1000,  # Long text
            confidence=0.9,
        )

        metrics = analyzer.analyze_segment(segment)
        assert isinstance(metrics, AudioQualityMetrics)
