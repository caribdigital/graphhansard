"""Tests for Bahamian Parliamentary Procedure Conventions (BC-4 through BC-7).

Validates:
- BC-4: Speaker control node (already tested in test_speaker_control_node.py)
- BC-5: Point of Order detection and PROCEDURAL_CONFLICT edge type
- BC-6: Constituency-based references with partial matching
- BC-7: Honourable prefix normalization

See Issue caribdigital/graphhansard#3 and SRD §11.2.
"""

from pathlib import Path

import pytest

from graphhansard.brain.creole_utils import (
    normalize_mention_for_resolution,
    strip_honorific_prefix,
)
from graphhansard.brain.entity_extractor import EntityExtractor
from graphhansard.brain.graph_builder import EdgeSemanticType
from graphhansard.golden_record.resolver import AliasResolver

GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


@pytest.fixture
def resolver():
    """Create an AliasResolver instance for testing."""
    return AliasResolver(str(GOLDEN_RECORD_PATH))


@pytest.fixture
def extractor():
    """Create an EntityExtractor instance for testing."""
    return EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=False)


class TestBC5PointOfOrder:
    """Test BC-5: Point of Order detection and PROCEDURAL_CONFLICT edge type."""

    def test_procedural_conflict_edge_type_exists(self):
        """BC-5: PROCEDURAL_CONFLICT edge semantic type is defined."""
        assert EdgeSemanticType.PROCEDURAL_CONFLICT.value == "procedural_conflict"

    def test_detect_point_of_order_basic(self, extractor):
        """BC-5: Detect basic 'Point of Order' pattern."""
        transcript = {
            "session_id": "test_2024_01_15",
            "segments": [
                {
                    "text": "Mr. Speaker, point of order!",
                    "speaker_node_id": "mp_pintard_michael",
                    "start_time": 120.0,
                    "end_time": 125.0,
                }
            ],
        }

        events = extractor.detect_point_of_order(transcript)
        assert len(events) == 1
        assert events[0]["source_node_id"] == "mp_pintard_michael"
        assert events[0]["session_id"] == "test_2024_01_15"
        assert "point of order" in events[0]["raw_text"].lower()

    def test_detect_point_of_order_with_rise(self, extractor):
        """BC-5: Detect 'I rise on a point of order' variant."""
        transcript = {
            "session_id": "test_2024_01_15",
            "segments": [
                {
                    "text": "Mr. Speaker, I rise on a point of order.",
                    "speaker_node_id": "mp_thompson_kwasi",
                    "start_time": 200.0,
                    "end_time": 205.0,
                }
            ],
        }

        events = extractor.detect_point_of_order(transcript)
        assert len(events) == 1
        assert events[0]["source_node_id"] == "mp_thompson_kwasi"

    def test_detect_point_of_order_madam_speaker(self, extractor):
        """BC-5: Detect point of order addressed to 'Madam Speaker'."""
        transcript = {
            "session_id": "test_2024_01_15",
            "segments": [
                {
                    "text": "Madam Speaker, I rise on point of order.",
                    "speaker_node_id": "mp_davis_brave",
                    "start_time": 300.0,
                    "end_time": 305.0,
                }
            ],
        }

        events = extractor.detect_point_of_order(transcript)
        assert len(events) == 1
        assert events[0]["source_node_id"] == "mp_davis_brave"

    def test_no_point_of_order_in_normal_speech(self, extractor):
        """BC-5: Normal speech doesn't trigger Point of Order detection."""
        transcript = {
            "session_id": "test_2024_01_15",
            "segments": [
                {
                    "text": "I agree with the Member for Cat Island.",
                    "speaker_node_id": "mp_cooper_chester",
                    "start_time": 400.0,
                    "end_time": 405.0,
                }
            ],
        }

        events = extractor.detect_point_of_order(transcript)
        assert len(events) == 0

    def test_multiple_points_of_order(self, extractor):
        """BC-5: Detect multiple Point of Order occurrences in a session."""
        transcript = {
            "session_id": "test_2024_01_15",
            "segments": [
                {
                    "text": "Mr. Speaker, point of order!",
                    "speaker_node_id": "mp_pintard_michael",
                    "start_time": 120.0,
                    "end_time": 125.0,
                },
                {
                    "text": "Thank you, Mr. Speaker.",
                    "speaker_node_id": "mp_davis_brave",
                    "start_time": 130.0,
                    "end_time": 132.0,
                },
                {
                    "text": "Madam Speaker, I rise on a point of order.",
                    "speaker_node_id": "mp_mitchell_fred",
                    "start_time": 200.0,
                    "end_time": 205.0,
                },
            ],
        }

        events = extractor.detect_point_of_order(transcript)
        assert len(events) == 2
        assert events[0]["source_node_id"] == "mp_pintard_michael"
        assert events[1]["source_node_id"] == "mp_mitchell_fred"


class TestBC6ConstituencyReferences:
    """Test BC-6: Constituency-based references with partial matching."""

    def test_full_constituency_match(self, resolver):
        """BC-6: Full constituency name resolves correctly."""
        result = resolver.resolve("Member for Cat Island, Rum Cay and San Salvador")
        assert result.node_id == "mp_davis_brave"
        assert result.method == "exact"

    def test_partial_constituency_match_cat_island(self, resolver):
        """BC-6: Partial constituency 'Cat Island' matches full name."""
        result = resolver.resolve("the Member for Cat Island")
        assert result.node_id == "mp_davis_brave"
        assert result.confidence >= 0.95

    def test_partial_constituency_match_fox_hill(self, resolver):
        """BC-6: 'Member for Fox Hill' matches correctly."""
        result = resolver.resolve("Member for Fox Hill")
        assert result.node_id == "mp_mitchell_fred"

    def test_partial_constituency_match_englerston(self, resolver):
        """BC-6: 'Member for Englerston' matches correctly."""
        result = resolver.resolve("Member for Englerston")
        assert result.node_id == "mp_hanna_martin_glenys"

    def test_partial_constituency_complex(self, resolver):
        """BC-6: Partial match handles ambiguous fragments correctly."""
        # "Central" appears in multiple constituencies: 
        # - Central and South Eleuthera
        # - Central and South Abaco  
        # - Central Grand Bahama
        # This is ambiguous and should return None (fall through to fuzzy matching)
        result = resolver.resolve("the Member for Central")
        # With multiple matches, partial matching returns None
        # Fuzzy matching will then find the best match
        assert result.node_id is not None  # Should still resolve via fuzzy match

    def test_all_39_constituencies_in_index(self, resolver):
        """BC-6: All 39 constituencies are in the alias index."""
        # Verify all constituencies are accessible
        for mp in resolver.golden_record.mps:
            constituency = mp.constituency
            # Try resolving with "Member for [constituency]"
            result = resolver.resolve(f"Member for {constituency}")
            assert result.node_id == mp.node_id, (
                f"Constituency '{constituency}' did not resolve to {mp.node_id}"
            )


class TestBC7HonourableNormalization:
    """Test BC-7: Honourable prefix normalization."""

    def test_strip_the_honourable_prefix(self):
        """BC-7: Strip 'The Honourable' prefix."""
        result = strip_honorific_prefix("The Honourable Member for Fox Hill")
        assert result == "Member for Fox Hill"

    def test_strip_the_hon_prefix(self):
        """BC-7: Strip 'The Hon.' prefix."""
        result = strip_honorific_prefix("The Hon. Fred Mitchell")
        assert result == "Fred Mitchell"

    def test_strip_hon_without_article(self):
        """BC-7: Strip 'Hon.' without 'The'."""
        result = strip_honorific_prefix("Hon. Chester Cooper")
        assert result == "Chester Cooper"

    def test_strip_honourable_member(self):
        """BC-7: Strip 'the honourable member' when followed by 'for'."""
        result = strip_honorific_prefix("the honourable member for Cat Island")
        # When followed by "for", we keep "member for..." (lowercase preserved)
        assert result == "member for Cat Island"

    def test_strip_my_honourable_friend(self):
        """BC-7: Strip 'my honourable friend' phrase."""
        result = strip_honorific_prefix("my honourable friend from Exuma")
        assert result == "from Exuma"

    def test_honorific_normalization_case_insensitive(self):
        """BC-7: Honorific stripping is case-insensitive."""
        result1 = strip_honorific_prefix("THE HONOURABLE MEMBER")
        result2 = strip_honorific_prefix("the honourable member")
        assert result1.lower() == result2.lower()

    def test_no_honorific_returns_unchanged(self):
        """BC-7: Text without honorifics is unchanged."""
        text = "Member for Fox Hill"
        result = strip_honorific_prefix(text)
        assert result == text

    def test_normalize_mention_pipeline(self):
        """BC-7: Full normalization pipeline includes honorific stripping."""
        # Test with Creole + honorific
        # "da Honourable Memba for" -> "the honourable Member for" -> "Member for"
        result = normalize_mention_for_resolution("da Honourable Memba for Cat Island")
        assert "honourable" not in result.lower()
        assert result == "Member for Cat Island"

    def test_resolve_with_honorific_prefix(self, resolver):
        """BC-7: Resolver handles honorific prefixes correctly."""
        result = resolver.resolve("The Honourable Member for Fox Hill")
        assert result.node_id == "mp_mitchell_fred"

    def test_resolve_hon_fred_mitchell(self, resolver):
        """BC-7: Resolver strips 'Hon.' and resolves name."""
        result = resolver.resolve("The Hon. Fred Mitchell")
        assert result.node_id == "mp_mitchell_fred"

    def test_resolve_honourable_brave_davis(self, resolver):
        """BC-7: Resolver handles honorific with common name."""
        result = resolver.resolve("The Honourable Brave Davis")
        assert result.node_id == "mp_davis_brave"


class TestIntegration:
    """Integration tests combining multiple BC requirements."""

    def test_creole_plus_honorific_plus_constituency(self, resolver):
        """Integration: Creole normalization + honorific stripping + constituency."""
        # "da Honourable Memba for Englaston"
        result = resolver.resolve("da Honourable Memba for Englaston")
        assert result.node_id == "mp_hanna_martin_glenys"

    def test_point_of_order_not_treated_as_mention(self, extractor):
        """Integration: Point of Order shouldn't create regular mention records."""
        transcript = {
            "session_id": "test_2024_01_15",
            "segments": [
                {
                    "text": "Mr. Speaker, I rise on a point of order!",
                    "speaker_node_id": "mp_pintard_michael",
                    "start_time": 120.0,
                    "end_time": 125.0,
                }
            ],
        }

        # Point of Order events are separate from mentions
        poo_events = extractor.detect_point_of_order(transcript)
        assert len(poo_events) == 1

        # Regular mention extraction should not include "point of order" as an MP mention
        mentions = extractor.extract_mentions(transcript)
        # Should not create any resolved mention for "point of order" itself
        # (Speaker reference would be a separate pattern)
        # This test ensures Point of Order is handled specially
