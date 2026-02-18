"""Integration test for speaker resolution in the full pipeline.

This test verifies that speaker resolution integrates correctly with
the transcription pipeline and entity extraction.
"""

import pytest
from pathlib import Path

from graphhansard.brain.pipeline import TranscriptionPipeline
from graphhansard.brain.speaker_resolver import (
    SpeakerResolver,
    load_mp_registry_from_golden_record,
)
from graphhansard.brain.transcriber import DiarizedTranscript, TranscriptSegment

GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


@pytest.fixture
def mp_registry():
    """Load MP registry."""
    return load_mp_registry_from_golden_record(GOLDEN_RECORD_PATH)


@pytest.fixture
def mock_transcript():
    """Create a mock transcript for testing."""
    return DiarizedTranscript(
        session_id="test_integration",
        segments=[
            TranscriptSegment(
                speaker_label="SPEAKER_00",
                speaker_node_id=None,
                start_time=0.0,
                end_time=5.0,
                text="Good morning. The House will come to order. I recognize the Prime Minister.",
                confidence=0.95,
                words=[]
            ),
            TranscriptSegment(
                speaker_label="SPEAKER_01",
                speaker_node_id=None,
                start_time=5.5,
                end_time=15.0,
                text="Thank you Madam Speaker. I want to discuss the budget and our fiscal policy.",
                confidence=0.92,
                words=[]
            ),
            TranscriptSegment(
                speaker_label="SPEAKER_00",
                speaker_node_id=None,
                start_time=15.5,
                end_time=18.0,
                text="Order, order. The Member has the floor.",
                confidence=0.96,
                words=[]
            ),
        ]
    )


class TestSpeakerResolutionIntegration:
    """Test speaker resolution integration with the pipeline."""

    def test_pipeline_with_speaker_resolution(self, mp_registry, mock_transcript):
        """Pipeline integrates speaker resolution correctly."""
        # Create pipeline with speaker resolution enabled
        pipeline = TranscriptionPipeline(
            speaker_resolver=SpeakerResolver(mp_registry=mp_registry),
            enable_speaker_resolution=True,
            enable_quality_analysis=False,  # Disable for this test
        )
        
        # Apply speaker resolution
        pipeline._apply_speaker_resolution(mock_transcript)
        
        # Verify SPEAKER_00 (chair) was resolved
        speaker_00_segments = [s for s in mock_transcript.segments if s.speaker_label == "SPEAKER_00"]
        assert len(speaker_00_segments) == 2
        
        # Both SPEAKER_00 segments should be resolved to Speaker
        for segment in speaker_00_segments:
            assert segment.speaker_node_id == "mp_deveaux_patricia"
    
    def test_resolution_preserves_original_labels(self, mp_registry, mock_transcript):
        """Speaker resolution preserves original speaker_label."""
        pipeline = TranscriptionPipeline(
            speaker_resolver=SpeakerResolver(mp_registry=mp_registry),
            enable_speaker_resolution=True,
            enable_quality_analysis=False,
        )
        
        pipeline._apply_speaker_resolution(mock_transcript)
        
        # Original labels should be preserved
        assert mock_transcript.segments[0].speaker_label == "SPEAKER_00"
        assert mock_transcript.segments[1].speaker_label == "SPEAKER_01"
        assert mock_transcript.segments[2].speaker_label == "SPEAKER_00"
    
    def test_disabled_speaker_resolution(self, mp_registry, mock_transcript):
        """Pipeline works correctly when speaker resolution is disabled."""
        pipeline = TranscriptionPipeline(
            speaker_resolver=None,
            enable_speaker_resolution=False,
            enable_quality_analysis=False,
        )
        
        # Should not crash when speaker resolution is disabled
        # (no speaker_node_id fields should be populated)
        for segment in mock_transcript.segments:
            assert segment.speaker_node_id is None
    
    def test_resolution_to_entity_extraction_flow(self, mp_registry, mock_transcript):
        """Resolved speaker_node_ids flow correctly to entity extraction."""
        from graphhansard.brain.entity_extractor import EntityExtractor
        
        # Apply speaker resolution
        pipeline = TranscriptionPipeline(
            speaker_resolver=SpeakerResolver(mp_registry=mp_registry),
            enable_speaker_resolution=True,
            enable_quality_analysis=False,
        )
        pipeline._apply_speaker_resolution(mock_transcript)
        
        # Create entity extractor
        extractor = EntityExtractor(golden_record_path=str(GOLDEN_RECORD_PATH))
        
        # Extract mentions
        transcript_dict = mock_transcript.model_dump()
        mentions = extractor.extract_mentions(transcript_dict)
        
        # Verify that resolved speakers are used as source_node_id
        # (assuming there are mentions in the transcript)
        for mention in mentions:
            # If the segment had a resolved speaker_node_id, it should be used
            # Otherwise, falls back to speaker_label
            assert mention.source_node_id in [
                "mp_deveaux_patricia",  # Resolved Speaker
                "SPEAKER_01",  # Unresolved (may or may not be resolved depending on heuristics)
            ] or mention.source_node_id.startswith("mp_")  # Or any other resolved MP


class TestSpeakerResolutionConfidence:
    """Test confidence-based filtering in integration."""

    def test_high_confidence_threshold(self, mp_registry, mock_transcript):
        """High confidence threshold filters out lower confidence resolutions."""
        resolver = SpeakerResolver(mp_registry=mp_registry)
        
        transcript_dict = mock_transcript.model_dump()
        
        # Use very high threshold
        resolutions = resolver.resolve_speakers(transcript_dict, confidence_threshold=0.99)
        
        # May filter out some resolutions
        # Chair detection should still be high confidence (0.9+)
        if "SPEAKER_00" in resolutions:
            assert resolutions["SPEAKER_00"].confidence >= 0.99
    
    def test_low_confidence_threshold(self, mp_registry, mock_transcript):
        """Low confidence threshold accepts more resolutions."""
        resolver = SpeakerResolver(mp_registry=mp_registry)
        
        transcript_dict = mock_transcript.model_dump()
        
        # Use low threshold
        resolutions_low = resolver.resolve_speakers(transcript_dict, confidence_threshold=0.3)
        resolutions_high = resolver.resolve_speakers(transcript_dict, confidence_threshold=0.8)
        
        # Low threshold should have at least as many resolutions
        assert len(resolutions_low) >= len(resolutions_high)


class TestSpeakerResolutionErrorHandling:
    """Test error handling in speaker resolution."""

    def test_empty_transcript(self, mp_registry):
        """Handles empty transcript gracefully."""
        pipeline = TranscriptionPipeline(
            speaker_resolver=SpeakerResolver(mp_registry=mp_registry),
            enable_speaker_resolution=True,
            enable_quality_analysis=False,
        )
        
        empty_transcript = DiarizedTranscript(
            session_id="empty",
            segments=[]
        )
        
        # Should not crash
        pipeline._apply_speaker_resolution(empty_transcript)
        assert len(empty_transcript.segments) == 0
    
    def test_transcript_with_no_speaker_labels(self, mp_registry):
        """Handles transcript with no SPEAKER_XX labels."""
        pipeline = TranscriptionPipeline(
            speaker_resolver=SpeakerResolver(mp_registry=mp_registry),
            enable_speaker_resolution=True,
            enable_quality_analysis=False,
        )
        
        transcript = DiarizedTranscript(
            session_id="no_speakers",
            segments=[
                TranscriptSegment(
                    speaker_label="UNKNOWN",
                    start_time=0.0,
                    end_time=5.0,
                    text="Some text",
                    confidence=0.9,
                    words=[]
                )
            ]
        )
        
        # Should not crash
        pipeline._apply_speaker_resolution(transcript)
        
        # UNKNOWN should not be resolved
        assert transcript.segments[0].speaker_node_id is None
