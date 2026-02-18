"""Tests for Layer 2 — Entity Extraction.

Tests pattern matching, NER, mention resolution, and validation corpus metrics.
See Issue #10 (BR-9 through BR-13).
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


@pytest.fixture
def extractor_with_spacy():
    """Create an EntityExtractor with spaCy enabled (if available)."""
    try:
        return EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=True)
    except Exception:
        pytest.skip("spaCy not available")


class TestEntityExtractorInit:
    """Test EntityExtractor initialization."""

    def test_extractor_initializes(self, extractor):
        """Extractor loads successfully."""
        assert extractor is not None
        assert extractor.resolver is not None
        assert len(extractor.PATTERNS) > 0

    def test_extractor_with_spacy_initializes(self):
        """Extractor with spaCy initializes (if spaCy available)."""
        try:
            ext = EntityExtractor(str(GOLDEN_RECORD_PATH), use_spacy=True)
            # If spaCy is available, nlp should be set
            if ext.use_spacy:
                assert ext.nlp is not None
        except ImportError:
            pytest.skip("spaCy not installed")


class TestPatternMatching:
    """Test pattern matching layer (BR-9)."""

    def test_member_for_pattern(self, extractor):
        """Detects 'The Member for [constituency]' pattern."""
        text = "The Member for Cat Island spoke about the budget."
        mentions = extractor._extract_pattern_mentions(text)

        assert len(mentions) > 0
        # Should find "The Member for Cat Island"
        mention_texts = [m[0] for m in mentions]
        assert any("Member for Cat Island" in m for m in mention_texts)

    def test_minister_of_pattern(self, extractor):
        """Detects 'The Minister of [portfolio]' pattern."""
        text = "The Minister of Finance presented the report."
        mentions = extractor._extract_pattern_mentions(text)

        assert len(mentions) > 0
        mention_texts = [m[0] for m in mentions]
        assert any("Minister of Finance" in m for m in mention_texts)

    def test_honourable_pattern(self, extractor):
        """Detects 'The Honourable [name]' pattern."""
        text = "The Honourable Fred Mitchell raised a point."
        mentions = extractor._extract_pattern_mentions(text)

        assert len(mentions) > 0
        mention_texts = [m[0] for m in mentions]
        assert any("Honourable Fred Mitchell" in m for m in mention_texts)

    def test_prime_minister_pattern(self, extractor):
        """Detects 'Prime Minister' pattern."""
        text = "The Prime Minister announced new policies."
        mentions = extractor._extract_pattern_mentions(text)

        assert len(mentions) > 0
        mention_texts = [m[0] for m in mentions]
        assert any("Prime Minister" in m for m in mention_texts)

    def test_deputy_pm_pattern(self, extractor):
        """Detects 'Deputy Prime Minister' pattern."""
        text = "The Deputy Prime Minister addressed the House."
        mentions = extractor._extract_pattern_mentions(text)

        assert len(mentions) > 0
        mention_texts = [m[0] for m in mentions]
        assert any("Deputy Prime Minister" in m for m in mention_texts)

    def test_multiple_patterns_in_text(self, extractor):
        """Detects multiple different patterns in same text."""
        text = "The Prime Minister and the Minister of Health discussed the issue with the Member for Nassau."
        mentions = extractor._extract_pattern_mentions(text)

        # Should find at least 2-3 mentions
        assert len(mentions) >= 2


class TestForeignLeaderDetection:
    """Test foreign leader detection and exclusion (Issue: Foreign leader mentions)."""

    def test_canadian_prime_minister_not_detected(self, extractor):
        """Foreign leader 'Canadian prime minister' should NOT be detected as a mention."""
        text = "The address by the Canadian prime minister was discussed."
        mentions = extractor._extract_pattern_mentions(text)

        # Should not detect 'prime minister' when qualified as Canadian
        mention_texts = [m[0].lower() for m in mentions]
        assert not any("prime minister" in m for m in mention_texts)

    def test_british_prime_minister_not_detected(self, extractor):
        """Foreign leader 'British Prime Minister' should NOT be detected."""
        text = "The British Prime Minister visited the islands."
        mentions = extractor._extract_pattern_mentions(text)

        mention_texts = [m[0].lower() for m in mentions]
        assert not any("prime minister" in m for m in mention_texts)

    def test_american_president_not_detected(self, extractor):
        """Foreign leader 'American President' should NOT be detected."""
        text = "The American President sent a delegation."
        mentions = extractor._extract_pattern_mentions(text)

        mention_texts = [m[0].lower() for m in mentions]
        assert not any("president" in m for m in mention_texts)

    def test_jamaican_prime_minister_not_detected(self, extractor):
        """Foreign leader 'Jamaican Prime Minister' should NOT be detected."""
        text = "The Jamaican Prime Minister attended the CARICOM summit."
        mentions = extractor._extract_pattern_mentions(text)

        mention_texts = [m[0].lower() for m in mentions]
        assert not any("prime minister" in m for m in mention_texts)

    def test_unqualified_prime_minister_still_detected(self, extractor):
        """Unqualified 'Prime Minister' should still be detected."""
        text = "The Prime Minister announced new policies."
        mentions = extractor._extract_pattern_mentions(text)

        # Should find "The Prime Minister"
        assert len(mentions) > 0
        mention_texts = [m[0] for m in mentions]
        assert any("Prime Minister" in m for m in mention_texts)

    def test_unqualified_prime_minister_resolves_correctly(self, extractor):
        """Unqualified 'Prime Minister' should resolve to Bahamian PM."""
        segment = {
            "text": "The Prime Minister made an announcement.",
            "speaker_node_id": "mp_thompson_iram",
            "start_time": 10.0,
            "end_time": 15.0,
        }
        segments = [segment]

        mentions = extractor._extract_from_segment(
            segment, 0, "test_session", segments, None
        )

        # Should find and resolve "The Prime Minister" to Brave Davis
        assert len(mentions) > 0
        pm_mentions = [m for m in mentions if "Prime Minister" in m.raw_mention]
        assert len(pm_mentions) > 0
        assert pm_mentions[0].target_node_id == "mp_davis_brave"

    def test_french_president_not_detected(self, extractor):
        """Foreign leader 'French President' should NOT be detected."""
        text = "The French President spoke at the climate summit."
        mentions = extractor._extract_pattern_mentions(text)

        mention_texts = [m[0].lower() for m in mentions]
        assert not any("president" in m for m in mention_texts)

    def test_cuban_president_not_detected(self, extractor):
        """Foreign leader 'Cuban President' should NOT be detected."""
        text = "The Cuban President discussed trade relations."
        mentions = extractor._extract_pattern_mentions(text)

        mention_texts = [m[0].lower() for m in mentions]
        assert not any("president" in m for m in mention_texts)

    def test_mixed_foreign_and_local_leaders(self, extractor):
        """Text with both foreign and local leaders handles correctly."""
        text = "The Prime Minister met with the Canadian prime minister and the British Prime Minister."
        mentions = extractor._extract_pattern_mentions(text)

        # Should only find the first "The Prime Minister" (Bahamian)
        # but NOT the Canadian or British ones
        assert len(mentions) == 1
        mention_texts = [m[0] for m in mentions]
        assert "The Prime Minister" in mention_texts[0]

    def test_haitian_president_not_detected(self, extractor):
        """Foreign leader 'Haitian President' should NOT be detected."""
        text = "The Haitian President requested assistance."
        mentions = extractor._extract_pattern_mentions(text)

        mention_texts = [m[0].lower() for m in mentions]
        assert not any("president" in m for m in mention_texts)

    def test_trinidadian_prime_minister_not_detected(self, extractor):
        """Foreign leader 'Trinidadian Prime Minister' should NOT be detected."""
        text = "The Trinidadian Prime Minister addressed the conference."
        mentions = extractor._extract_pattern_mentions(text)

        mention_texts = [m[0].lower() for m in mentions]
        assert not any("prime minister" in m for m in mention_texts)

    def test_generic_nationality_suffix_pattern(self, extractor):
        """Generic nationality suffixes (e.g., -ian, -ese) are detected."""
        text = "The Norwegian Prime Minister visited. The Chinese President spoke."
        mentions = extractor._extract_pattern_mentions(text)

        # Should NOT detect either foreign leader
        assert len(mentions) == 0

    def test_lowercase_foreign_leader(self, extractor):
        """Foreign leaders with lowercase qualifiers should also be excluded."""
        text = "The statement from the canadian prime minister was noted."
        mentions = extractor._extract_pattern_mentions(text)

        mention_texts = [m[0].lower() for m in mentions]
        assert not any("prime minister" in m for m in mention_texts)

    def test_bahamian_prime_minister_not_filtered(self, extractor):
        """'Bahamian Prime Minister' should NOT be filtered — it's the local PM."""
        text = "The Bahamian Prime Minister met with the Canadian Prime Minister."
        mentions = extractor._extract_pattern_mentions(text)

        # Should detect the Bahamian PM but NOT the Canadian PM
        mention_texts = [m[0] for m in mentions]
        assert len(mentions) >= 1
        assert any("Prime Minister" in m for m in mention_texts)

    def test_bahamian_minister_not_filtered(self, extractor):
        """'Bahamian Minister of Finance' should NOT be filtered."""
        text = "The Bahamian Minister of Finance presented the budget."
        mentions = extractor._extract_pattern_mentions(text)

        mention_texts = [m[0] for m in mentions]
        assert any("Minister" in m for m in mention_texts)


class TestMentionDeduplication:
    """Test mention deduplication logic."""

    def test_deduplicate_overlapping_mentions(self, extractor):
        """Removes overlapping mentions, keeping longest."""
        mentions = [
            ("Prime Minister", 0, 15),
            ("The Prime Minister", 0, 19),
            ("Minister", 10, 18),
        ]

        deduplicated = extractor._deduplicate_mentions(mentions)

        # Should keep only "The Prime Minister" (longest)
        assert len(deduplicated) == 1
        assert deduplicated[0][0] == "The Prime Minister"

    def test_deduplicate_preserves_non_overlapping(self, extractor):
        """Preserves non-overlapping mentions."""
        mentions = [
            ("Prime Minister", 0, 15),
            ("Minister of Health", 20, 38),
        ]

        deduplicated = extractor._deduplicate_mentions(mentions)

        assert len(deduplicated) == 2


class TestContextWindowExtraction:
    """Test context window extraction (±1 sentence) (BR-12)."""

    def test_extract_context_single_sentence(self, extractor):
        """Extracts context from single sentence."""
        segments = [
            {"text": "The Prime Minister announced new policies today."}
        ]

        context = extractor._extract_context_window(0, segments, 4, 18)

        # Should return the full sentence
        assert "Prime Minister" in context
        assert "announced" in context

    def test_extract_context_multiple_sentences(self, extractor):
        """Extracts ±1 sentence context."""
        text = "This is the first sentence. The Prime Minister spoke today. This is the third sentence."
        segments = [{"text": text}]

        # Mention is in second sentence
        char_start = text.index("Prime Minister")
        char_end = char_start + len("Prime Minister")

        context = extractor._extract_context_window(0, segments, char_start, char_end)

        # Should include surrounding sentences
        assert "Prime Minister" in context


class TestTimestampEstimation:
    """Test mention timestamp estimation."""

    def test_estimate_timestamps_proportional(self, extractor):
        """Estimates timestamps proportionally to character position."""
        text = "The Prime Minister spoke today."
        segment_start = 10.0
        segment_end = 15.0  # 5 second segment

        # "Prime Minister" is roughly at 4-18 chars out of 31 total
        char_start = 4
        char_end = 18

        mention_start, mention_end = extractor._estimate_mention_timestamps(
            text, char_start, char_end, segment_start, segment_end
        )

        # Should be somewhere in the first half of the segment
        assert segment_start <= mention_start < segment_end
        assert mention_start < mention_end <= segment_end


class TestMentionExtraction:
    """Test full mention extraction from transcript segments."""

    def test_extract_from_segment_basic(self, extractor):
        """Extracts mentions from a basic segment."""
        segment = {
            "text": "The Prime Minister spoke about the budget.",
            "speaker_node_id": "mp_thompson_iram",
            "start_time": 10.0,
            "end_time": 15.0,
        }
        segments = [segment]

        mentions = extractor._extract_from_segment(
            segment, 0, "test_session", segments, debate_date=None
        )

        # Should find at least one mention (Prime Minister)
        assert len(mentions) > 0

        # Check mention structure
        mention = mentions[0]
        assert isinstance(mention, MentionRecord)
        assert mention.source_node_id == "mp_thompson_iram"
        assert mention.session_id == "test_session"
        assert "Prime Minister" in mention.raw_mention

    def test_extract_resolves_to_golden_record(self, extractor):
        """Mentions are resolved to canonical MP node IDs via Golden Record."""
        segment = {
            "text": "The Prime Minister made an announcement.",
            "speaker_node_id": "mp_thompson_iram",
            "start_time": 10.0,
            "end_time": 15.0,
        }
        segments = [segment]

        mentions = extractor._extract_from_segment(
            segment, 0, "test_session", segments, debate_date=None
        )

        # Should find "The Prime Minister" and resolve it
        assert len(mentions) > 0
        pm_mentions = [m for m in mentions if "Prime Minister" in m.raw_mention]
        assert len(pm_mentions) > 0

        # Should resolve to Brave Davis (current PM)
        assert pm_mentions[0].target_node_id == "mp_davis_brave"
        assert pm_mentions[0].resolution_method in (
            ResolutionMethod.EXACT, ResolutionMethod.FUZZY
        )

    def test_extract_skips_empty_text(self, extractor):
        """Skips segments with no text."""
        segment_no_text = {
            "text": "",
            "speaker_node_id": "mp_thompson_iram",
            "start_time": 10.0,
            "end_time": 15.0,
        }

        mentions = extractor._extract_from_segment(
            segment_no_text, 0, "test_session", [segment_no_text], None
        )

        assert len(mentions) == 0

    def test_extract_falls_back_to_speaker_label(self, extractor):
        """Falls back to speaker_label when speaker_node_id is absent."""
        segment = {
            "text": "The Prime Minister spoke.",
            "speaker_node_id": None,
            "speaker_label": "SPEAKER_00",
            "start_time": 10.0,
            "end_time": 15.0,
        }

        mentions = extractor._extract_from_segment(
            segment, 0, "test_session", [segment], None
        )

        assert len(mentions) > 0
        assert mentions[0].source_node_id == "SPEAKER_00"

    def test_extract_falls_back_to_unknown(self, extractor):
        """Falls back to UNKNOWN when both speaker fields are absent."""
        segment = {
            "text": "The Prime Minister spoke.",
            "start_time": 10.0,
            "end_time": 15.0,
        }

        mentions = extractor._extract_from_segment(
            segment, 0, "test_session", [segment], None
        )

        assert len(mentions) > 0
        assert mentions[0].source_node_id == "UNKNOWN"


class TestFullTranscriptExtraction:
    """Test extraction from complete transcript."""

    def test_extract_mentions_full_transcript(self, extractor):
        """Extracts mentions from a full transcript."""
        transcript = {
            "session_id": "2023-11-15-debate",
            "segments": [
                {
                    "text": "The Prime Minister opened the debate.",
                    "speaker_node_id": "mp_thompson_iram",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
                {
                    "text": "The Member for Cat Island responded to the statement.",
                    "speaker_node_id": "mp_cooper_chester",
                    "start_time": 5.0,
                    "end_time": 10.0,
                },
            ],
        }

        mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")

        # Should find mentions in both segments
        assert len(mentions) >= 2

        # Check session_id is preserved
        for mention in mentions:
            assert mention.session_id == "2023-11-15-debate"

    def test_extract_mentions_with_temporal_disambiguation(self, extractor):
        """Uses debate_date for temporal resolution."""
        transcript = {
            "session_id": "2023-11-15-debate",
            "segments": [
                {
                    "text": "The Minister of Works announced the project.",
                    "speaker_node_id": "mp_thompson_iram",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }

        # Minister of Works changed after Sept 2023 reshuffle
        mentions_before = extractor.extract_mentions(
            transcript, debate_date="2023-08-01"
        )
        mentions_after = extractor.extract_mentions(
            transcript, debate_date="2023-11-15"
        )

        # Both should find mentions, but might resolve to different MPs
        assert len(mentions_before) > 0
        assert len(mentions_after) > 0

    def test_extract_mentions_skips_excluded_segments(self, extractor):
        """Segments with exclude_from_extraction=True produce no mentions (BC-9, BC-10)."""
        transcript = {
            "session_id": "2023-11-15-debate",
            "segments": [
                {
                    "text": "The Prime Minister opened the debate.",
                    "speaker_node_id": "mp_thompson_iram",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "exclude_from_extraction": True,  # This segment should be skipped
                },
                {
                    "text": "The Member for Cat Island responded to the statement.",
                    "speaker_node_id": "mp_cooper_chester",
                    "start_time": 5.0,
                    "end_time": 10.0,
                    "exclude_from_extraction": False,  # This segment should process
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
        
        # Should only find mentions from the second segment
        # First segment is excluded, so "Prime Minister" should not appear
        assert len(mentions) >= 1  # At least one from second segment
        
        # Verify no mentions from first segment (Prime Minister)
        pm_mentions = [m for m in mentions if "Prime Minister" in m.raw_mention]
        assert len(pm_mentions) == 0
        
        # Verify mentions from second segment exist (Member for Cat Island)
        member_mentions = [m for m in mentions if "Member for Cat Island" in m.raw_mention]
        assert len(member_mentions) > 0

    def test_extract_mentions_processes_when_flag_false(self, extractor):
        """Segments with exclude_from_extraction=False process normally."""
        transcript = {
            "session_id": "2023-11-15-debate",
            "segments": [
                {
                    "text": "The Prime Minister opened the debate.",
                    "speaker_node_id": "mp_thompson_iram",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    "exclude_from_extraction": False,
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
        
        # Should find mentions normally
        assert len(mentions) > 0
        pm_mentions = [m for m in mentions if "Prime Minister" in m.raw_mention]
        assert len(pm_mentions) > 0

    def test_extract_mentions_processes_when_flag_missing(self, extractor):
        """Segments without exclude_from_extraction flag process normally."""
        transcript = {
            "session_id": "2023-11-15-debate",
            "segments": [
                {
                    "text": "The Prime Minister opened the debate.",
                    "speaker_node_id": "mp_thompson_iram",
                    "start_time": 0.0,
                    "end_time": 5.0,
                    # No exclude_from_extraction flag
                },
            ],
        }
        
        mentions = extractor.extract_mentions(transcript, debate_date="2023-11-15")
        
        # Should find mentions normally when flag is absent
        assert len(mentions) > 0
        pm_mentions = [m for m in mentions if "Prime Minister" in m.raw_mention]
        assert len(pm_mentions) > 0


class TestResolutionMethods:
    """Test resolution method tracking."""

    def test_exact_match_resolution(self, extractor):
        """Exact matches are tracked correctly."""
        segment = {
            "text": "The Prime Minister spoke today.",
            "speaker_node_id": "mp_thompson_iram",
            "start_time": 0.0,
            "end_time": 5.0,
        }

        mentions = extractor._extract_from_segment(
            segment, 0, "test_session", [segment], None
        )

        if len(mentions) > 0:
            # "Prime Minister" should resolve exactly
            pm_mentions = [m for m in mentions if "Prime Minister" in m.raw_mention]
            if pm_mentions:
                assert pm_mentions[0].resolution_method in (
                    ResolutionMethod.EXACT,
                    ResolutionMethod.FUZZY,
                )

    def test_unresolved_mention_tracking(self, extractor):
        """Unresolved mentions are tracked."""
        segment = {
            "text": "The unknown person spoke today.",
            "speaker_node_id": "mp_thompson_iram",
            "start_time": 0.0,
            "end_time": 5.0,
        }

        mentions = extractor._extract_from_segment(
            segment, 0, "test_session", [segment], None
        )

        # Pattern matching won't catch this, so no mentions expected
        # This test verifies we don't crash on unresolvable text


class TestCoreferenceResolution:
    """Test coreference resolution (future implementation)."""

    def test_resolve_coreference_placeholder(self, extractor):
        """Coreference resolution returns None (not yet implemented)."""
        result = extractor.resolve_coreference(
            "the gentleman who just spoke", []
        )

        # Currently returns None (placeholder)
        assert result is None


class TestSentenceSplitting:
    """Test sentence splitting helper."""

    def test_split_sentences_basic(self, extractor):
        """Splits sentences on .!? correctly."""
        text = "First sentence. Second sentence! Third sentence?"
        sentences = extractor._split_sentences(text)

        assert len(sentences) == 3
        assert "First sentence" in sentences[0]
        assert "Second sentence" in sentences[1]
        assert "Third sentence" in sentences[2]

    def test_split_sentences_single(self, extractor):
        """Returns single sentence if no splits."""
        text = "This is one long sentence with no punctuation breaks"
        sentences = extractor._split_sentences(text)

        assert len(sentences) == 1
        assert sentences[0] == text


class TestUnresolvedLogging:
    """Test unresolved mention logging (BR-12)."""

    def test_unresolved_mentions_are_logged(self, extractor):
        """Unresolved mentions are logged for human review."""
        segment = {
            "text": "The unknown person spoke today.",
            "speaker_node_id": "mp_thompson_iram",
            "start_time": 0.0,
            "end_time": 5.0,
        }

        # Clear any existing log
        extractor.clear_unresolved_log()

        mentions = extractor._extract_from_segment(
            segment, 0, "test_session", [segment], None
        )

        # No pattern matches expected for "unknown person"
        # So unresolved count should be 0 (nothing detected to resolve)
        initial_count = extractor.get_unresolved_count()
        assert initial_count == 0

    def test_unresolved_count_tracked(self, extractor):
        """Unresolved mention count is tracked."""
        extractor.clear_unresolved_log()

        transcript = {
            "session_id": "test_session",
            "segments": [
                {
                    "text": "The Member for Unknown Place spoke.",
                    "speaker_node_id": "mp_thompson_iram",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }

        mentions = extractor.extract_mentions(transcript)

        # "Member for Unknown Place" should be detected but unresolved
        unresolved = [m for m in mentions if m.target_node_id is None]
        assert len(unresolved) > 0
        assert extractor.get_unresolved_count() == len(unresolved)

    def test_save_unresolved_log(self, extractor, tmp_path):
        """Unresolved log can be saved to file."""
        import json

        extractor.clear_unresolved_log()

        transcript = {
            "session_id": "test_session",
            "segments": [
                {
                    "text": "The Member for Atlantis spoke.",
                    "speaker_node_id": "mp_thompson_iram",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }

        mentions = extractor.extract_mentions(transcript)

        # Save log
        log_path = tmp_path / "unresolved.json"
        extractor.save_unresolved_log(str(log_path))

        # Verify file exists and is valid JSON
        assert log_path.exists()

        with open(log_path) as f:
            log_data = json.load(f)

        assert "total_unresolved" in log_data
        assert "mentions" in log_data
        assert isinstance(log_data["mentions"], list)

    def test_clear_unresolved_log(self, extractor):
        """Unresolved log can be cleared."""
        extractor.clear_unresolved_log()
        assert extractor.get_unresolved_count() == 0

        # Add some unresolved
        transcript = {
            "session_id": "test_session",
            "segments": [
                {
                    "text": "The Member for Narnia spoke.",
                    "speaker_node_id": "mp_thompson_iram",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
            ],
        }

        extractor.extract_mentions(transcript)

        # Should have some unresolved now
        initial_count = extractor.get_unresolved_count()
        assert initial_count > 0

        # Clear and verify
        extractor.clear_unresolved_log()
        assert extractor.get_unresolved_count() == 0
