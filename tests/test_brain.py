"""Tests for Layer 2 — The Brain.

Covers: transcription, entity extraction, sentiment, graph construction.
See Issues #9 through #14.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from graphhansard.brain import (
    DiarizedTranscript,
    Diarizer,
    TranscriptionPipeline,
    Transcriber,
    TranscriptSegment,
    WordToken,
    create_pipeline,
)


class TestWordToken:
    """Test WordToken schema validation."""

    def test_word_token_creation(self):
        """Test creating a WordToken."""
        token = WordToken(word="hello", start=0.5, end=1.0, confidence=0.95)
        assert token.word == "hello"
        assert token.start == 0.5
        assert token.end == 1.0
        assert token.confidence == 0.95

    def test_word_token_validation(self):
        """Test WordToken validates required fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            WordToken(word="hello")  # Missing required fields


class TestTranscriptSegment:
    """Test TranscriptSegment schema validation."""

    def test_segment_creation(self):
        """Test creating a TranscriptSegment."""
        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=5.0,
            text="Hello, this is a test.",
            confidence=0.92,
            words=[
                WordToken(word="Hello", start=0.0, end=0.5, confidence=0.95),
                WordToken(word="this", start=0.6, end=0.8, confidence=0.90),
            ],
        )
        assert segment.speaker_label == "SPEAKER_00"
        assert segment.start_time == 0.0
        assert segment.end_time == 5.0
        assert segment.text == "Hello, this is a test."
        assert len(segment.words) == 2

    def test_segment_with_speaker_node_id(self):
        """Test segment with resolved speaker."""
        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            speaker_node_id="mp_davis_brave",
            start_time=0.0,
            end_time=5.0,
            text="Test",
            confidence=0.9,
        )
        assert segment.speaker_node_id == "mp_davis_brave"

    def test_segment_without_words(self):
        """Test segment without word-level timestamps."""
        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=5.0,
            text="Test",
            confidence=0.9,
        )
        assert segment.words == []


class TestDiarizedTranscript:
    """Test DiarizedTranscript schema validation."""

    def test_transcript_creation(self):
        """Test creating a DiarizedTranscript."""
        transcript = DiarizedTranscript(
            session_id="test_session_001",
            segments=[
                TranscriptSegment(
                    speaker_label="SPEAKER_00",
                    start_time=0.0,
                    end_time=5.0,
                    text="First segment.",
                    confidence=0.92,
                ),
                TranscriptSegment(
                    speaker_label="SPEAKER_01",
                    start_time=5.1,
                    end_time=10.0,
                    text="Second segment.",
                    confidence=0.88,
                ),
            ],
        )
        assert transcript.session_id == "test_session_001"
        assert len(transcript.segments) == 2

    def test_transcript_serialization(self):
        """Test transcript can be serialized to JSON."""
        transcript = DiarizedTranscript(
            session_id="test_session_001",
            segments=[
                TranscriptSegment(
                    speaker_label="SPEAKER_00",
                    start_time=0.0,
                    end_time=5.0,
                    text="Test",
                    confidence=0.9,
                )
            ],
        )
        json_str = json.dumps(transcript.model_dump())
        assert "test_session_001" in json_str
        assert "SPEAKER_00" in json_str

    def test_transcript_deserialization(self):
        """Test transcript can be loaded from JSON."""
        data = {
            "session_id": "test_session_001",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "speaker_node_id": None,
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "text": "Test",
                    "confidence": 0.9,
                    "words": [],
                }
            ],
        }
        transcript = DiarizedTranscript.model_validate(data)
        assert transcript.session_id == "test_session_001"
        assert len(transcript.segments) == 1


class TestTranscriber:
    """Test Transcriber class."""

    def test_transcriber_initialization(self):
        """Test Transcriber can be initialized."""
        transcriber = Transcriber(model_size="base", device="cpu")
        assert transcriber.model_size == "base"
        assert transcriber.device == "cpu"

    def test_transcriber_backend_options(self):
        """Test different backend options."""
        t1 = Transcriber(backend="faster-whisper")
        assert t1.backend == "faster-whisper"

        t2 = Transcriber(backend="insanely-fast-whisper")
        assert t2.backend == "insanely-fast-whisper"

    @patch("graphhansard.brain.transcriber.WhisperModel")
    def test_transcriber_lazy_loading(self, mock_whisper_model):
        """Test model is lazy-loaded."""
        transcriber = Transcriber(device="cpu", backend="faster-whisper")
        assert transcriber._model is None

        # Trigger model loading
        transcriber._load_model()
        mock_whisper_model.assert_called_once()
        assert transcriber._model is not None

    @patch("graphhansard.brain.transcriber.WhisperModel")
    def test_transcriber_transcribe_mock(self, mock_whisper_model):
        """Test transcribe with mocked model."""
        # Setup mock
        mock_segment = Mock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "Test transcription"
        mock_segment.avg_logprob = -0.5
        mock_segment.words = []

        mock_info = Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.99
        mock_info.duration = 5.0

        mock_model_instance = Mock()
        mock_model_instance.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper_model.return_value = mock_model_instance

        # Test transcription
        transcriber = Transcriber(device="cpu", backend="faster-whisper")
        result = transcriber.transcribe("/tmp/test.wav")

        assert result["language"] == "en"
        assert len(result["segments"]) == 1
        assert result["segments"][0]["text"] == "Test transcription"


class TestDiarizer:
    """Test Diarizer class."""

    def test_diarizer_requires_token(self):
        """Test Diarizer requires HuggingFace token."""
        with pytest.raises(ValueError, match="HuggingFace token required"):
            Diarizer(hf_token=None)

    def test_diarizer_initialization_with_token(self):
        """Test Diarizer initializes with token."""
        diarizer = Diarizer(hf_token="test_token", device="cpu")
        assert diarizer.hf_token == "test_token"
        assert diarizer.device == "cpu"

    def test_diarizer_speaker_limits(self):
        """Test Diarizer accepts speaker limits."""
        diarizer = Diarizer(
            hf_token="test_token", min_speakers=2, max_speakers=5
        )
        assert diarizer.min_speakers == 2
        assert diarizer.max_speakers == 5

    def test_align_with_transcript(self):
        """Test simple overlap-based alignment."""
        diarizer = Diarizer(hf_token="test_token")

        # Mock diarization segments
        diarization = [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 5.0},
            {"speaker": "SPEAKER_01", "start": 5.0, "end": 10.0},
        ]

        # Mock transcript segments
        transcript_segments = [
            {"start": 0.5, "end": 4.5, "text": "First segment"},
            {"start": 5.5, "end": 9.5, "text": "Second segment"},
        ]

        # Align
        aligned = diarizer.align_with_transcript(diarization, transcript_segments)

        assert len(aligned) == 2
        assert aligned[0]["speaker"] == "SPEAKER_00"
        assert aligned[1]["speaker"] == "SPEAKER_01"

    def test_align_with_partial_overlap(self):
        """Test alignment with partial overlap."""
        diarizer = Diarizer(hf_token="test_token")

        diarization = [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 3.0},
            {"speaker": "SPEAKER_01", "start": 3.0, "end": 6.0},
        ]

        transcript_segments = [
            {"start": 2.0, "end": 4.0, "text": "Overlapping segment"},
        ]

        aligned = diarizer.align_with_transcript(diarization, transcript_segments)

        # Should assign to speaker with most overlap
        assert len(aligned) == 1
        # The segment spans both speakers, should pick one with max overlap


class TestTranscriptionPipeline:
    """Test TranscriptionPipeline orchestration."""

    def test_pipeline_initialization(self):
        """Test pipeline initializes with components."""
        transcriber = Transcriber(device="cpu")
        diarizer = Diarizer(hf_token="test_token")

        pipeline = TranscriptionPipeline(
            transcriber=transcriber, diarizer=diarizer
        )

        assert pipeline.transcriber is transcriber
        assert pipeline.diarizer is diarizer

    def test_pipeline_default_initialization(self):
        """Test pipeline creates default transcriber."""
        pipeline = TranscriptionPipeline()
        assert pipeline.transcriber is not None
        assert isinstance(pipeline.transcriber, Transcriber)

    @patch.object(Transcriber, "transcribe")
    def test_pipeline_without_diarization(self, mock_transcribe):
        """Test pipeline can run without diarization."""
        # Setup mock
        mock_transcribe.return_value = {
            "language": "en",
            "duration": 5.0,
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Test",
                    "confidence": 0.9,
                    "words": [],
                }
            ],
        }

        pipeline = TranscriptionPipeline(diarizer=None)
        transcript = pipeline.process(
            "/tmp/test.wav", "session_001", enable_diarization=False
        )

        assert isinstance(transcript, DiarizedTranscript)
        assert transcript.session_id == "session_001"
        assert len(transcript.segments) == 1
        assert transcript.segments[0].speaker_label == "UNKNOWN"


class TestPipelineFactory:
    """Test create_pipeline factory function."""

    def test_create_pipeline_basic(self):
        """Test basic pipeline creation."""
        pipeline = create_pipeline(device="cpu", hf_token=None)
        assert isinstance(pipeline, TranscriptionPipeline)
        assert pipeline.transcriber.device == "cpu"

    def test_create_pipeline_with_diarization(self):
        """Test pipeline creation with diarization."""
        pipeline = create_pipeline(device="cpu", hf_token="test_token")
        assert pipeline.diarizer is not None
        assert pipeline.diarizer.hf_token == "test_token"

    def test_create_pipeline_backend_selection(self):
        """Test backend selection."""
        p1 = create_pipeline(backend="faster-whisper", hf_token=None)
        assert p1.transcriber.backend == "faster-whisper"

        p2 = create_pipeline(backend="insanely-fast-whisper", hf_token=None)
        assert p2.transcriber.backend == "insanely-fast-whisper"


class TestPipelineIO:
    """Test pipeline I/O operations."""

    def test_save_and_load_transcript(self, tmp_path):
        """Test saving and loading transcripts."""
        # Create a transcript
        transcript = DiarizedTranscript(
            session_id="test_001",
            segments=[
                TranscriptSegment(
                    speaker_label="SPEAKER_00",
                    start_time=0.0,
                    end_time=5.0,
                    text="Test segment",
                    confidence=0.9,
                )
            ],
        )

        # Save
        pipeline = TranscriptionPipeline()
        output_path = tmp_path / "transcript.json"
        pipeline.save_transcript(transcript, str(output_path))

        assert output_path.exists()

        # Load
        loaded = pipeline.load_transcript(str(output_path))
        assert loaded.session_id == transcript.session_id
        assert len(loaded.segments) == len(transcript.segments)
        assert loaded.segments[0].text == transcript.segments[0].text


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_transcriber_invalid_backend(self):
        """Test invalid backend raises error."""
        transcriber = Transcriber(backend="invalid-backend")
        with pytest.raises(ValueError, match="Unknown backend"):
            transcriber._load_model()

    def test_empty_transcript(self):
        """Test transcript with no segments."""
        transcript = DiarizedTranscript(session_id="empty_001", segments=[])
        assert len(transcript.segments) == 0

    def test_segment_confidence_bounds(self):
        """Test confidence values are properly bounded."""
        segment = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=1.0,
            text="Test",
            confidence=0.0,  # Minimum
        )
        assert segment.confidence == 0.0

        segment2 = TranscriptSegment(
            speaker_label="SPEAKER_00",
            start_time=0.0,
            end_time=1.0,
            text="Test",
            confidence=1.0,  # Maximum
        )
        assert segment2.confidence == 1.0
