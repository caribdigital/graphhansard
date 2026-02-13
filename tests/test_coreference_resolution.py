"""Tests for co-reference and anaphoric resolution (BR-11, BR-14, BR-15).

Tests deictic reference detection, context-based resolution, self-reference
detection, and unresolved mention logging.
See Issue caribdigital/graphhansard#5 (BR: Co-reference & Anaphoric Resolution).
"""

from pathlib import Path

import pytest

from graphhansard.brain.entity_extractor import (
    EntityExtractor,
    MentionRecord,
    ResolutionMethod,
)

GOLDEN_RECORD_PATH = Path(__file__).parent.parent / "golden_record" / "mps.json"


@pytest.fixture
def extractor():
    """Create an EntityExtractor instance for testing."""
    return EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=False)


class TestDeicticPatternDetection:
    """Test detection of deictic/anaphoric reference patterns (BR-11)."""

    def test_member_who_spoke_detected(self, extractor):
        """Detects 'the Member who just spoke' pattern."""
        text = "I agree with the Member who just spoke about the budget."
        mentions = extractor._extract_pattern_mentions(text)
        
        mention_texts = [m[0] for m in mentions]
        assert any("Member who just spoke" in m for m in mention_texts)

    def test_gentleman_who_spoke_detected(self, extractor):
        """Detects 'the gentleman who spoke' pattern."""
        text = "The gentleman who spoke raised an excellent point."
        mentions = extractor._extract_pattern_mentions(text)
        
        mention_texts = [m[0] for m in mentions]
        assert any("gentleman who spoke" in m for m in mention_texts)

    def test_member_opposite_detected(self, extractor):
        """Detects 'Member opposite' pattern."""
        text = "I must disagree with the Member opposite."
        mentions = extractor._extract_pattern_mentions(text)
        
        mention_texts = [m[0] for m in mentions]
        assert any("Member opposite" in m for m in mention_texts)

    def test_honourable_gentleman_opposite_detected(self, extractor):
        """Detects 'honourable gentleman opposite' pattern."""
        text = "The honourable gentleman opposite makes a valid point."
        mentions = extractor._extract_pattern_mentions(text)
        
        mention_texts = [m[0] for m in mentions]
        assert any("honourable gentleman opposite" in m for m in mention_texts)

    def test_my_honourable_friend_detected(self, extractor):
        """Detects 'my honourable friend' pattern."""
        text = "My honourable friend from Marathon has my support."
        mentions = extractor._extract_pattern_mentions(text)
        
        mention_texts = [m[0] for m in mentions]
        assert any("honourable friend" in m for m in mention_texts)

    def test_my_colleague_detected(self, extractor):
        """Detects 'my colleague' pattern."""
        text = "My colleague has done excellent work on this."
        mentions = extractor._extract_pattern_mentions(text)
        
        mention_texts = [m[0] for m in mentions]
        assert any("colleague" in m for m in mention_texts)

    def test_previous_speaker_detected(self, extractor):
        """Detects 'the previous speaker' pattern."""
        text = "The previous speaker made some valid points."
        mentions = extractor._extract_pattern_mentions(text)
        
        mention_texts = [m[0] for m in mentions]
        assert any("previous speaker" in m for m in mention_texts)


class TestDeicticReferenceClassification:
    """Test classification of mentions as deictic (BR-11)."""

    def test_is_deictic_member_who_spoke(self, extractor):
        """'Member who just spoke' is classified as deictic."""
        mention = "the Member who just spoke"
        assert extractor._is_deictic_reference(mention) is True

    def test_is_deictic_member_opposite(self, extractor):
        """'Member opposite' is classified as deictic."""
        mention = "the Member opposite"
        assert extractor._is_deictic_reference(mention) is True

    def test_is_deictic_honourable_friend(self, extractor):
        """'my honourable friend' is classified as deictic."""
        mention = "my honourable friend"
        assert extractor._is_deictic_reference(mention) is True

    def test_not_deictic_prime_minister(self, extractor):
        """'Prime Minister' is NOT deictic."""
        mention = "the Prime Minister"
        assert extractor._is_deictic_reference(mention) is False

    def test_not_deictic_named_person(self, extractor):
        """Named person mentions are NOT deictic."""
        mention = "Brave Davis"
        assert extractor._is_deictic_reference(mention) is False


class TestSpeakerHistoryBuilding:
    """Test speaker history construction for context window (BR-11)."""

    def test_build_speaker_history_basic(self, extractor):
        """Builds speaker history from previous segments."""
        segments = [
            {"speaker_node_id": "mp_davis_brave", "text": "First statement"},
            {"speaker_node_id": "mp_cooper_chester", "text": "Second statement"},
            {"speaker_node_id": "mp_mitchell_fred", "text": "Third statement"},
            {"speaker_node_id": "mp_thompson_iram", "text": "Current statement"},
        ]
        
        history = extractor._build_speaker_history(3, segments)
        
        # Should have 3 speakers (all except current)
        assert len(history) == 3
        assert history[0]["node_id"] == "mp_davis_brave"
        assert history[1]["node_id"] == "mp_cooper_chester"
        assert history[2]["node_id"] == "mp_mitchell_fred"

    def test_build_speaker_history_ordering(self, extractor):
        """Speaker history is ordered oldest-first."""
        segments = [
            {"speaker_node_id": "mp_davis_brave", "text": "First statement"},
            {"speaker_node_id": "mp_cooper_chester", "text": "Second statement"},
            {"speaker_node_id": "mp_mitchell_fred", "text": "Current statement"},
        ]

        history = extractor._build_speaker_history(2, segments)

        # Oldest speaker first, most recent last
        assert len(history) == 2
        assert history[0]["segment_index"] < history[1]["segment_index"]

    def test_build_speaker_history_limits_window(self, extractor):
        """Speaker history respects context window size."""
        segments = [
            {"speaker_node_id": f"mp_speaker_{i}", "text": f"Statement {i}"}
            for i in range(10)
        ]
        
        history = extractor._build_speaker_history(9, segments)
        
        # Default window size is 3, should only get 3 previous speakers
        assert len(history) <= extractor.context_window_size

    def test_build_speaker_history_skips_unknown(self, extractor):
        """Speaker history skips UNKNOWN speakers."""
        segments = [
            {"speaker_node_id": "mp_davis_brave", "text": "First statement"},
            {"speaker_node_id": "UNKNOWN", "text": "Unknown speaker"},
            {"speaker_node_id": "mp_cooper_chester", "text": "Current statement"},
        ]
        
        history = extractor._build_speaker_history(2, segments)
        
        # Should only have mp_davis_brave, not UNKNOWN
        assert len(history) == 1
        assert history[0]["node_id"] == "mp_davis_brave"


class TestCoreferenceResolution:
    """Test coreference resolution logic (BR-11)."""

    def test_resolve_member_who_just_spoke(self, extractor):
        """Resolves 'Member who just spoke' to most recent speaker."""
        speaker_history = [
            {"node_id": "mp_davis_brave", "segment_index": 0, "text": "First"},
            {"node_id": "mp_cooper_chester", "segment_index": 1, "text": "Second"},
        ]
        
        mention = "the Member who just spoke"
        source_id = "mp_mitchell_fred"
        
        resolved = extractor._resolve_coreference(mention, source_id, speaker_history, None)
        
        # Should resolve to most recent speaker
        assert resolved == "mp_cooper_chester"

    def test_resolve_previous_speaker(self, extractor):
        """Resolves 'previous speaker' to most recent speaker."""
        speaker_history = [
            {"node_id": "mp_davis_brave", "segment_index": 0, "text": "First"},
            {"node_id": "mp_cooper_chester", "segment_index": 1, "text": "Second"},
        ]
        
        mention = "the previous speaker"
        source_id = "mp_mitchell_fred"
        
        resolved = extractor._resolve_coreference(mention, source_id, speaker_history, None)
        
        assert resolved == "mp_cooper_chester"

    def test_resolve_honourable_friend_same_party(self, extractor):
        """Resolves 'my honourable friend' to same-party member."""
        speaker_history = [
            {"node_id": "mp_minnis_hubert", "segment_index": 0, "text": "FNM member"},
            {"node_id": "mp_cooper_chester", "segment_index": 1, "text": "PLP member"},
        ]
        
        mention = "my honourable friend"
        source_id = "mp_davis_brave"  # PLP
        
        resolved = extractor._resolve_coreference(mention, source_id, speaker_history, None)
        
        # Should resolve to same party (PLP)
        assert resolved == "mp_cooper_chester"

    def test_resolve_member_opposite_different_party(self, extractor):
        """Resolves 'Member opposite' to different-party member."""
        speaker_history = [
            {"node_id": "mp_cooper_chester", "segment_index": 0, "text": "PLP member"},
            {"node_id": "mp_minnis_hubert", "segment_index": 1, "text": "FNM member"},
        ]
        
        mention = "the Member opposite"
        source_id = "mp_davis_brave"  # PLP
        
        resolved = extractor._resolve_coreference(mention, source_id, speaker_history, None)
        
        # Should resolve to different party (FNM)
        assert resolved == "mp_minnis_hubert"

    def test_resolve_excludes_self_reference(self, extractor):
        """Coreference resolution excludes the source speaker."""
        speaker_history = [
            {"node_id": "mp_davis_brave", "segment_index": 0, "text": "Self"},
            {"node_id": "mp_cooper_chester", "segment_index": 1, "text": "Other"},
        ]
        
        mention = "the Member who just spoke"
        source_id = "mp_cooper_chester"  # The most recent speaker
        
        resolved = extractor._resolve_coreference(mention, source_id, speaker_history, None)
        
        # Should skip self and resolve to previous speaker
        assert resolved == "mp_davis_brave"

    def test_resolve_no_history_returns_none(self, extractor):
        """Returns None when speaker history is empty."""
        speaker_history = []
        
        mention = "the Member who just spoke"
        source_id = "mp_davis_brave"
        
        resolved = extractor._resolve_coreference(mention, source_id, speaker_history, None)
        
        assert resolved is None


class TestSelfReferenceDetection:
    """Test self-reference detection (BR-15)."""

    def test_self_reference_flagged(self, extractor):
        """Self-references are flagged in MentionRecord."""
        transcript = {
            "session_id": "test-session",
            "segments": [
                {
                    "text": "As Prime Minister, I must address this issue.",
                    "speaker_node_id": "mp_davis_brave",  # Prime Minister
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
        
        # Should detect "Prime Minister" and flag as self-reference
        self_refs = [m for m in mentions if m.is_self_reference]
        assert len(self_refs) > 0

    def test_non_self_reference_not_flagged(self, extractor):
        """Non-self-references are not flagged."""
        transcript = {
            "session_id": "test-session",
            "segments": [
                {
                    "text": "The Prime Minister has announced new policies.",
                    "speaker_node_id": "mp_cooper_chester",  # Not Prime Minister
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
        
        # Should detect "Prime Minister" but NOT flag as self-reference
        non_self_refs = [m for m in mentions if not m.is_self_reference]
        assert len(non_self_refs) > 0


class TestUnresolvedMentionLogging:
    """Test unresolved mention logging (BR-14)."""

    def test_unresolved_deictic_logged(self, extractor):
        """Unresolved deictic mentions are logged with context."""
        transcript = {
            "session_id": "test-session",
            "segments": [
                {
                    "text": "The Member who just spoke is absolutely right.",
                    "speaker_node_id": "mp_davis_brave",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }
        
        initial_count = len(extractor.unresolved_mentions)
        mentions = extractor.extract_mentions(transcript)
        
        # Should log unresolved deictic reference (no speaker history)
        assert len(extractor.unresolved_mentions) > initial_count
        
        # Check log structure
        last_log = extractor.unresolved_mentions[-1]
        assert "mention" in last_log
        assert "mention_type" in last_log
        assert last_log["mention_type"] == "deictic"
        assert "speaker_id" in last_log
        assert "context" in last_log

    def test_unresolved_standard_logged(self, extractor):
        """Unresolved standard mentions are logged."""
        transcript = {
            "session_id": "test-session",
            "segments": [
                {
                    "text": "The Member for NonExistent Constituency spoke well.",
                    "speaker_node_id": "mp_davis_brave",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }
        
        initial_count = len(extractor.unresolved_mentions)
        mentions = extractor.extract_mentions(transcript)
        
        # Should log unresolved mention
        assert len(extractor.unresolved_mentions) > initial_count
        
        last_log = extractor.unresolved_mentions[-1]
        assert last_log["mention_type"] == "standard"

    def test_save_unresolved_log_includes_metadata(self, extractor, tmp_path):
        """Saved unresolved log includes all required metadata."""
        # Create an unresolved mention
        transcript = {
            "session_id": "test-session",
            "segments": [
                {
                    "text": "The Member who just spoke is right.",
                    "speaker_node_id": "mp_davis_brave",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }
        
        extractor.extract_mentions(transcript)
        
        # Save log
        log_path = tmp_path / "unresolved.json"
        extractor.save_unresolved_log(str(log_path))
        
        assert log_path.exists()
        
        import json
        with open(log_path) as f:
            log = json.load(f)
        
        assert "total_unresolved" in log
        assert "mentions" in log
        assert len(log["mentions"]) > 0
        
        # Check first entry has required fields and correct values
        entry = log["mentions"][0]
        assert "mention" in entry
        assert "Member who just spoke" in entry["mention"]
        assert "mention_type" in entry
        assert entry["mention_type"] == "deictic"
        assert "speaker_id" in entry
        assert entry["speaker_id"] == "mp_davis_brave"
        assert "context" in entry


class TestCoreferenceResolutionIntegration:
    """Integration tests for full coreference resolution (BR-11)."""

    def test_full_extraction_with_deictic_resolution(self, extractor):
        """Full extraction resolves deictic references using context."""
        transcript = {
            "session_id": "test-session",
            "segments": [
                {
                    "text": "I support the budget proposal.",
                    "speaker_node_id": "mp_cooper_chester",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "text": "The Member who just spoke makes an excellent point.",
                    "speaker_node_id": "mp_mitchell_fred",
                    "start_time": 3.0,
                    "end_time": 6.0,
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript)
        
        # Should resolve "Member who just spoke" to mp_cooper_chester
        deictic_mentions = [
            m for m in mentions 
            if m.resolution_method == ResolutionMethod.COREFERENCE
        ]
        
        assert len(deictic_mentions) > 0
        assert deictic_mentions[0].target_node_id == "mp_cooper_chester"
        assert deictic_mentions[0].source_node_id == "mp_mitchell_fred"

    def test_party_based_filtering(self, extractor):
        """Resolves 'my honourable friend' using party affiliation."""
        transcript = {
            "session_id": "test-session",
            "segments": [
                {
                    "text": "We need reform.",
                    "speaker_node_id": "mp_minnis_hubert",  # FNM
                    "start_time": 0.0,
                    "end_time": 2.0,
                },
                {
                    "text": "I agree with that.",
                    "speaker_node_id": "mp_cooper_chester",  # PLP
                    "start_time": 2.0,
                    "end_time": 4.0,
                },
                {
                    "text": "My honourable friend is absolutely correct.",
                    "speaker_node_id": "mp_davis_brave",  # PLP
                    "start_time": 4.0,
                    "end_time": 6.0,
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript)
        
        # Should resolve to same party (Cooper, not Minnis)
        deictic_mentions = [
            m for m in mentions 
            if m.resolution_method == ResolutionMethod.COREFERENCE
        ]
        
        if deictic_mentions:
            # If resolved, should be to same-party member
            assert deictic_mentions[0].target_node_id == "mp_cooper_chester"


class TestResolutionMethodTracking:
    """Test that resolution methods are correctly tracked (BR-11)."""

    def test_coreference_method_tracked(self, extractor):
        """Coreference-resolved mentions have COREFERENCE method."""
        transcript = {
            "session_id": "test-session",
            "segments": [
                {
                    "text": "We need action.",
                    "speaker_node_id": "mp_cooper_chester",
                    "start_time": 0.0,
                    "end_time": 2.0,
                },
                {
                    "text": "The Member who just spoke is right.",
                    "speaker_node_id": "mp_mitchell_fred",
                    "start_time": 2.0,
                    "end_time": 5.0,
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript)
        
        coreference_mentions = [
            m for m in mentions 
            if m.resolution_method == ResolutionMethod.COREFERENCE
        ]
        
        assert len(coreference_mentions) > 0
        # Check confidence is set appropriately
        assert coreference_mentions[0].resolution_score > 0.0

    def test_exact_method_still_works(self, extractor):
        """Standard exact matches still work alongside coreference."""
        transcript = {
            "session_id": "test-session",
            "segments": [
                {
                    "text": "The Prime Minister announced the policy.",
                    "speaker_node_id": "mp_cooper_chester",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
        
        exact_mentions = [
            m for m in mentions 
            if m.resolution_method == ResolutionMethod.EXACT
        ]
        
        assert len(exact_mentions) > 0
        assert exact_mentions[0].target_node_id == "mp_davis_brave"
