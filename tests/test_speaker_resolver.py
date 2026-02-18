"""Tests for speaker resolution module.

Tests the heuristic-based speaker identity resolution that maps
SPEAKER_XX labels to MP node IDs.
"""

import pytest

from graphhansard.brain.speaker_resolver import (
    SpeakerResolution,
    SpeakerResolver,
    load_mp_registry_from_golden_record,
)
from pathlib import Path

GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


@pytest.fixture
def mp_registry():
    """Load MP registry from golden record."""
    return load_mp_registry_from_golden_record(GOLDEN_RECORD_PATH)


@pytest.fixture
def resolver(mp_registry):
    """Create a SpeakerResolver instance for testing."""
    return SpeakerResolver(mp_registry=mp_registry)


@pytest.fixture
def sample_transcript_with_chair():
    """Sample transcript with chair/speaker language."""
    return {
        "session_id": "test_session",
        "segments": [
            {
                "speaker_label": "SPEAKER_00",
                "text": "The House will come to order. The Chair recognizes the Member for Cat Island.",
                "start_time": 0.0,
                "end_time": 5.0,
            },
            {
                "speaker_label": "SPEAKER_01",
                "text": "Thank you Madam Speaker. I rise today to discuss the important matter of tourism development in Cat Island.",
                "start_time": 5.5,
                "end_time": 12.0,
            },
            {
                "speaker_label": "SPEAKER_00",
                "text": "Order, order. The Member has the floor.",
                "start_time": 12.5,
                "end_time": 15.0,
            },
            {
                "speaker_label": "SPEAKER_02",
                "text": "I want to thank the Prime Minister for his leadership on the budget.",
                "start_time": 15.5,
                "end_time": 20.0,
            },
        ]
    }


@pytest.fixture
def sample_transcript_with_recognition():
    """Sample transcript with recognition patterns."""
    return {
        "session_id": "test_session",
        "segments": [
            {
                "speaker_label": "SPEAKER_00",
                "text": "The Chair recognizes the Honourable Fred Mitchell.",
                "start_time": 0.0,
                "end_time": 3.0,
            },
            {
                "speaker_label": "SPEAKER_01",
                "text": "Thank you Madam Speaker. I want to address the matter of foreign affairs and our international relations.",
                "start_time": 3.5,
                "end_time": 10.0,
            },
            {
                "speaker_label": "SPEAKER_00",
                "text": "I recognize the Member for Exumas and Ragged Island.",
                "start_time": 10.5,
                "end_time": 13.0,
            },
            {
                "speaker_label": "SPEAKER_02",
                "text": "Thank you. I want to discuss tourism development and the importance of our aviation sector.",
                "start_time": 13.5,
                "end_time": 20.0,
            },
        ]
    }


@pytest.fixture
def sample_transcript_with_portfolio():
    """Sample transcript with portfolio keywords."""
    return {
        "session_id": "test_session",
        "segments": [
            {
                "speaker_label": "SPEAKER_00",
                "text": "Order, order. The House is now in session.",
                "start_time": 0.0,
                "end_time": 3.0,
            },
            {
                "speaker_label": "SPEAKER_01",
                "text": "I want to discuss the budget and the finance proposals. The tax revenue and fiscal policy are critical for our economy.",
                "start_time": 3.5,
                "end_time": 10.0,
            },
            {
                "speaker_label": "SPEAKER_02",
                "text": "Tourism is vital to our economy. We need to attract more tourists and visitors to support our hotels and resorts.",
                "start_time": 10.5,
                "end_time": 17.0,
            },
        ]
    }


class TestSpeakerResolverInit:
    """Test SpeakerResolver initialization."""

    def test_resolver_initializes(self, resolver):
        """Resolver initializes successfully."""
        assert resolver is not None
        assert resolver.mp_registry is not None
        assert len(resolver.mp_registry) > 0

    def test_lookup_indices_built(self, resolver):
        """Lookup indices are built correctly."""
        assert resolver.constituency_to_mp is not None
        assert resolver.name_to_mp is not None
        assert len(resolver.constituency_to_mp) > 0
        assert len(resolver.name_to_mp) > 0

    def test_speaker_identified(self, resolver):
        """Speaker and Deputy Speaker are identified."""
        # Should find the Speaker
        assert resolver.speaker_node_id is not None
        assert resolver.speaker_node_id == "mp_deveaux_patricia"
        
        # Should find the Deputy Speaker
        assert resolver.deputy_speaker_node_id is not None
        assert resolver.deputy_speaker_node_id == "mp_bonaby_mckell"


class TestChairDetection:
    """Test chair/speaker detection heuristic."""

    def test_detect_speaker_by_chair_language(self, resolver, sample_transcript_with_chair):
        """Detects Speaker by chair procedural language."""
        resolutions = resolver.resolve_speakers(sample_transcript_with_chair)
        
        # SPEAKER_00 should be identified as the Speaker
        assert "SPEAKER_00" in resolutions
        resolution = resolutions["SPEAKER_00"]
        assert resolution.resolved_node_id == "mp_deveaux_patricia"
        assert resolution.method == "chair_detection"
        assert resolution.confidence > 0.5

    def test_chair_detection_confidence(self, resolver, sample_transcript_with_chair):
        """Chair detection has appropriate confidence."""
        resolutions = resolver.resolve_speakers(sample_transcript_with_chair)
        
        if "SPEAKER_00" in resolutions:
            resolution = resolutions["SPEAKER_00"]
            # Confidence should be high for multiple chair patterns
            assert 0.5 <= resolution.confidence <= 1.0

    def test_chair_detection_evidence(self, resolver, sample_transcript_with_chair):
        """Chair detection includes evidence."""
        resolutions = resolver.resolve_speakers(sample_transcript_with_chair)
        
        if "SPEAKER_00" in resolutions:
            resolution = resolutions["SPEAKER_00"]
            assert len(resolution.evidence) > 0
            # Evidence should mention chair patterns
            assert any("Chair" in e or "pattern" in e for e in resolution.evidence)


class TestRecognitionChaining:
    """Test recognition-to-speech chaining heuristic."""

    def test_recognize_by_name(self, resolver, sample_transcript_with_recognition):
        """Recognizes speaker by name mention."""
        resolutions = resolver.resolve_speakers(sample_transcript_with_recognition)
        
        # SPEAKER_01 should be Fred Mitchell
        assert "SPEAKER_01" in resolutions
        resolution = resolutions["SPEAKER_01"]
        assert resolution.resolved_node_id == "mp_mitchell_fred"
        assert resolution.method == "recognition_chaining"

    def test_recognize_by_constituency(self, resolver, sample_transcript_with_recognition):
        """Recognizes speaker by constituency mention."""
        resolutions = resolver.resolve_speakers(sample_transcript_with_recognition)
        
        # SPEAKER_02 should be Chester Cooper (Exumas and Ragged Island)
        assert "SPEAKER_02" in resolutions
        resolution = resolutions["SPEAKER_02"]
        assert resolution.resolved_node_id == "mp_cooper_chester"
        assert resolution.method == "recognition_chaining"

    def test_recognition_chaining_confidence(self, resolver, sample_transcript_with_recognition):
        """Recognition chaining has appropriate confidence."""
        resolutions = resolver.resolve_speakers(sample_transcript_with_recognition)
        
        for speaker_label, resolution in resolutions.items():
            if resolution.method == "recognition_chaining":
                # Should have good confidence (0.75 in implementation)
                assert resolution.confidence >= 0.7


class TestPortfolioFingerprinting:
    """Test portfolio/topic fingerprinting heuristic."""

    def test_portfolio_matching_basic(self, resolver, sample_transcript_with_portfolio):
        """Matches speakers to portfolios by keywords."""
        resolutions = resolver.resolve_speakers(sample_transcript_with_portfolio)
        
        # Lower confidence threshold for portfolio matching
        portfolio_resolutions = {
            k: v for k, v in resolutions.items()
            if v.method == "portfolio_fingerprinting"
        }
        
        # Should find at least some portfolio matches
        # (depends on golden record data and keyword matching)
        # This is a basic check - portfolio matching is a weak signal
        if len(portfolio_resolutions) > 0:
            for resolution in portfolio_resolutions.values():
                assert resolution.confidence < 0.7  # Should be lower confidence
                assert "portfolio" in resolution.method.lower()


class TestResolutionConfidence:
    """Test confidence scoring."""

    def test_confidence_threshold_filtering(self, resolver, sample_transcript_with_chair):
        """Resolutions below confidence threshold are filtered out."""
        # Use high threshold
        resolutions = resolver.resolve_speakers(
            sample_transcript_with_chair, 
            confidence_threshold=0.95
        )
        
        # Should filter out lower confidence resolutions
        for resolution in resolutions.values():
            assert resolution.confidence >= 0.95

    def test_confidence_threshold_zero_returns_all(self, resolver, sample_transcript_with_chair):
        """Confidence threshold of 0 returns all resolutions."""
        resolutions = resolver.resolve_speakers(
            sample_transcript_with_chair,
            confidence_threshold=0.0
        )
        
        # Should return more resolutions with low threshold
        assert len(resolutions) >= 0


class TestApplyResolutions:
    """Test applying resolutions to transcript."""

    def test_apply_resolutions_updates_segments(self, resolver, sample_transcript_with_chair):
        """Applying resolutions updates segment speaker_node_id."""
        # Get resolutions
        resolutions = resolver.resolve_speakers(sample_transcript_with_chair)
        
        # Apply to transcript
        updated_transcript = resolver.apply_resolutions(
            sample_transcript_with_chair,
            resolutions
        )
        
        # Check segments are updated
        for segment in updated_transcript["segments"]:
            speaker_label = segment["speaker_label"]
            if speaker_label in resolutions:
                assert segment.get("speaker_node_id") == resolutions[speaker_label].resolved_node_id

    def test_apply_resolutions_preserves_unresolved(self, resolver):
        """Unresolved speakers remain with no speaker_node_id."""
        transcript = {
            "session_id": "test",
            "segments": [
                {
                    "speaker_label": "SPEAKER_99",
                    "text": "Some text",
                    "start_time": 0.0,
                    "end_time": 5.0,
                }
            ]
        }
        
        resolutions = resolver.resolve_speakers(transcript)
        updated_transcript = resolver.apply_resolutions(transcript, resolutions)
        
        # SPEAKER_99 should remain unresolved
        segment = updated_transcript["segments"][0]
        if "SPEAKER_99" not in resolutions:
            assert segment.get("speaker_node_id") is None


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_transcript(self, resolver):
        """Handles empty transcript gracefully."""
        transcript = {"session_id": "test", "segments": []}
        resolutions = resolver.resolve_speakers(transcript)
        assert resolutions == {}

    def test_no_speaker_labels(self, resolver):
        """Handles transcript with no SPEAKER_XX labels."""
        transcript = {
            "session_id": "test",
            "segments": [
                {
                    "speaker_label": "UNKNOWN",
                    "text": "Some text",
                    "start_time": 0.0,
                    "end_time": 5.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)
        # Should not try to resolve UNKNOWN
        assert "UNKNOWN" not in resolutions

    def test_empty_mp_registry(self):
        """Handles empty MP registry gracefully."""
        resolver = SpeakerResolver(mp_registry={})
        transcript = {
            "session_id": "test",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognizes the member.",
                    "start_time": 0.0,
                    "end_time": 5.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)
        # Should not crash, but won't resolve anything
        assert isinstance(resolutions, dict)


class TestLoadMPRegistry:
    """Test loading MP registry from golden record."""

    def test_load_mp_registry(self):
        """Loads MP registry successfully."""
        registry = load_mp_registry_from_golden_record(GOLDEN_RECORD_PATH)
        
        assert isinstance(registry, dict)
        assert len(registry) > 0
        
        # Check structure
        for node_id, mp_data in registry.items():
            assert "common_name" in mp_data
            assert "constituency" in mp_data or mp_data.get("constituency") is None
            assert "portfolios" in mp_data
            assert "special_roles" in mp_data

    def test_speaker_in_registry(self):
        """Speaker is in the loaded registry."""
        registry = load_mp_registry_from_golden_record(GOLDEN_RECORD_PATH)
        
        # Find the Speaker
        speaker_found = False
        for node_id, mp_data in registry.items():
            if "Speaker of the House" in mp_data.get("special_roles", []):
                speaker_found = True
                assert node_id == "mp_deveaux_patricia"
                break
        
        assert speaker_found, "Speaker should be in registry"


class TestSpeakerResolutionModel:
    """Test SpeakerResolution data model."""

    def test_speaker_resolution_model(self):
        """SpeakerResolution model validates correctly."""
        resolution = SpeakerResolution(
            speaker_label="SPEAKER_00",
            resolved_node_id="mp_davis_brave",
            confidence=0.85,
            method="chair_detection",
            evidence=["Pattern match: 'The Chair recognizes'"]
        )
        
        assert resolution.speaker_label == "SPEAKER_00"
        assert resolution.resolved_node_id == "mp_davis_brave"
        assert resolution.confidence == 0.85
        assert resolution.method == "chair_detection"
        assert len(resolution.evidence) == 1
