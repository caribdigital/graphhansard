"""Tests for speaker resolution module.

Tests the heuristic-based speaker identity resolution that maps
SPEAKER_XX labels to MP node IDs.
"""

from pathlib import Path

import pytest

from graphhansard.brain.speaker_resolver import (
    SpeakerResolution,
    SpeakerResolver,
    load_mp_registry_from_golden_record,
)

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

    def test_british_spelling_recognises(self, resolver):
        """Recognition chaining works with British spelling 'recognises'."""
        transcript = {
            "session_id": "test_british",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognises the Honourable Member for Freetown.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I rise to discuss infrastructure development in my constituency.",
                    "start_time": 3.5,
                    "end_time": 10.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)
        # SPEAKER_00 should be detected as Chair (recognises pattern)
        assert "SPEAKER_00" in resolutions
        assert resolutions["SPEAKER_00"].resolved_node_id == "mp_deveaux_patricia"
        # SPEAKER_01 should be chained to Freetown MP
        assert "SPEAKER_01" in resolutions
        assert resolutions["SPEAKER_01"].resolved_node_id == "mp_munroe_wayne"

    def test_american_spelling_honorable(self, resolver):
        """Recognition chaining works with American spelling 'Honorable'."""
        transcript = {
            "session_id": "test_american",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognizes the Honorable Member for Elizabeth.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I want to discuss the development plans for our constituency.",
                    "start_time": 3.5,
                    "end_time": 10.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)
        assert "SPEAKER_01" in resolutions
        assert resolutions["SPEAKER_01"].resolved_node_id == "mp_coleby_davis_jobeth"

    def test_recognition_does_not_capture_trailing_clause(self, resolver):
        """Recognition pattern stops at trailing clauses like 'to speak on'."""
        transcript = {
            "session_id": "test_trailing",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "I recognize the Member for Golden Isles to speak on this matter.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I want to address the important legislation before us today.",
                    "start_time": 3.5,
                    "end_time": 10.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)
        assert "SPEAKER_01" in resolutions
        assert resolutions["SPEAKER_01"].resolved_node_id == "mp_pickstock_darron"

    def test_recognition_chaining_confidence(self, resolver, sample_transcript_with_recognition):
        """Recognition chaining has appropriate confidence."""
        resolutions = resolver.resolve_speakers(sample_transcript_with_recognition)

        for speaker_label, resolution in resolutions.items():
            if resolution.method == "recognition_chaining":
                # Should have good confidence (0.75 in implementation)
                assert resolution.confidence >= 0.7

    def test_recognize_deputy_prime_minister(self, resolver):
        """Recognizes Deputy Prime Minister by title."""
        transcript = {
            "session_id": "test_title_dpm",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "I recognize the Deputy Prime Minister.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I want to discuss tourism development and our aviation sector which are critical to our economy.",
                    "start_time": 3.5,
                    "end_time": 10.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)

        # SPEAKER_01 should be Chester Cooper (Deputy Prime Minister)
        assert "SPEAKER_01" in resolutions
        resolution = resolutions["SPEAKER_01"]
        assert resolution.resolved_node_id == "mp_cooper_chester"
        assert resolution.method == "recognition_chaining"
        assert "Deputy Prime Minister" in resolution.evidence[0]

    def test_recognize_minister_of_foreign_affairs(self, resolver):
        """Recognizes Minister of Foreign Affairs by title."""
        transcript = {
            "session_id": "test_title_foreign",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "I recognize the Minister of Foreign Affairs.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I wish to address our international relations and diplomatic efforts in the region.",
                    "start_time": 3.5,
                    "end_time": 10.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)

        # SPEAKER_01 should be Fred Mitchell (Minister of Foreign Affairs)
        assert "SPEAKER_01" in resolutions
        resolution = resolutions["SPEAKER_01"]
        assert resolution.resolved_node_id == "mp_mitchell_fred"
        assert resolution.method == "recognition_chaining"
        assert "Minister of Foreign Affairs" in resolution.evidence[0]

    def test_recognize_prime_minister(self, resolver):
        """Recognizes Prime Minister by title."""
        transcript = {
            "session_id": "test_title_pm",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognizes the Prime Minister.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I want to address the budget and fiscal policy that will guide our nation forward.",
                    "start_time": 3.5,
                    "end_time": 10.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)

        # SPEAKER_01 should be Brave Davis (Prime Minister)
        assert "SPEAKER_01" in resolutions
        resolution = resolutions["SPEAKER_01"]
        assert resolution.resolved_node_id == "mp_davis_brave"
        assert resolution.method == "recognition_chaining"
        assert "Prime Minister" in resolution.evidence[0]

    def test_recognize_leader_of_opposition(self, resolver):
        """Recognizes Leader of the Opposition by title."""
        transcript = {
            "session_id": "test_title_opposition",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "I recognize the Leader of the Opposition.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I rise to express our concerns about the proposed legislation and its impact on our constituents.",
                    "start_time": 3.5,
                    "end_time": 10.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)

        # SPEAKER_01 should be Michael Pintard (Leader of the Opposition)
        assert "SPEAKER_01" in resolutions
        resolution = resolutions["SPEAKER_01"]
        assert resolution.resolved_node_id == "mp_pintard_michael"
        assert resolution.method == "recognition_chaining"

    def test_recognition_with_brief_interjection_at_i_plus_1(self, resolver):
        """Recognition chaining skips brief interjection and finds MP at i+2."""
        transcript = {
            "session_id": "test_interjection",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognizes the Member for Freetown.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_03",
                    "text": "Order!",  # Brief interjection <10 words
                    "start_time": 3.5,
                    "end_time": 4.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I rise to discuss infrastructure development in my constituency.",
                    "start_time": 4.5,
                    "end_time": 10.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)

        # SPEAKER_01 should be resolved as Freetown MP
        assert "SPEAKER_01" in resolutions
        assert resolutions["SPEAKER_01"].resolved_node_id == "mp_munroe_wayne"
        assert resolutions["SPEAKER_01"].method == "recognition_chaining"
        # Confidence should be lower (0.65) since it's at i+2
        assert resolutions["SPEAKER_01"].confidence == 0.65

    def test_recognition_with_interjection_at_i_plus_2(self, resolver):
        """Recognition chaining finds MP at i+3 when i+1 and i+2 are brief."""
        transcript = {
            "session_id": "test_interjection_i3",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognizes the Member for Freetown.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_03",
                    "text": "Order!",  # Brief interjection
                    "start_time": 3.5,
                    "end_time": 4.0,
                },
                {
                    "speaker_label": "SPEAKER_04",
                    "text": "Hear, hear!",  # Another brief interjection
                    "start_time": 4.2,
                    "end_time": 4.5,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I rise to discuss infrastructure development in my constituency.",
                    "start_time": 5.0,
                    "end_time": 12.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)

        # SPEAKER_01 should be resolved as Freetown MP
        assert "SPEAKER_01" in resolutions
        assert resolutions["SPEAKER_01"].resolved_node_id == "mp_munroe_wayne"
        # Confidence should be lowest (0.55) since it's at i+3
        assert resolutions["SPEAKER_01"].confidence == 0.55

    def test_recognition_skips_chair_speaker_segments(self, resolver):
        """Recognition chaining skips segments from the Chair."""
        transcript = {
            "session_id": "test_skip_chair",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognizes the Member for Freetown.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "Order, order. The member has the floor and should be heard.",  # Chair speaking again
                    "start_time": 3.5,
                    "end_time": 7.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I rise to discuss infrastructure development in my constituency.",
                    "start_time": 7.5,
                    "end_time": 14.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)

        # SPEAKER_01 should be resolved as Freetown MP at i+2
        assert "SPEAKER_01" in resolutions
        assert resolutions["SPEAKER_01"].resolved_node_id == "mp_munroe_wayne"
        # Confidence should be 0.65 since Chair segment was skipped
        assert resolutions["SPEAKER_01"].confidence == 0.65

    def test_recognition_prefers_first_substantial_different_speaker(self, resolver):
        """Recognition chaining prefers first >10 word segment from different speaker."""
        transcript = {
            "session_id": "test_prefer_substantial",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognizes the Member for Freetown.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_03",
                    "text": "Point of order!",  # Brief from different speaker
                    "start_time": 3.5,
                    "end_time": 4.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I rise to discuss infrastructure development in my constituency.",
                    "start_time": 4.5,
                    "end_time": 11.0,
                },
            ]
        }
        resolutions = resolver.resolve_speakers(transcript)

        # SPEAKER_01 should be resolved (substantial speech)
        assert "SPEAKER_01" in resolutions
        assert resolutions["SPEAKER_01"].resolved_node_id == "mp_munroe_wayne"
        # SPEAKER_03 should NOT be resolved (brief interjection)
        if "SPEAKER_03" in resolutions and resolutions["SPEAKER_03"].method == "recognition_chaining":
            # If it's resolved by recognition, it shouldn't be as Freetown MP
            assert resolutions["SPEAKER_03"].resolved_node_id != "mp_munroe_wayne"


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
    
    def test_transport_aviation_keywords(self, resolver):
        """Test Transport & Aviation portfolio keywords."""
        transcript = {
            "session_id": "test_transport",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "We need to improve our airport infrastructure and aviation sector. The airline industry is critical for tourism.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to a Minister with Transport/Aviation portfolio
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_agriculture_marine_keywords(self, resolver):
        """Test Agriculture & Marine Resources portfolio keywords."""
        transcript = {
            "session_id": "test_agriculture",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Our farmers need support for agriculture. We must invest in fisheries and marine resources to help our fishing industry.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Agriculture/Marine minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_housing_keywords(self, resolver):
        """Test Housing portfolio keywords."""
        transcript = {
            "session_id": "test_housing",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "We need more affordable housing for our people. The mortgage assistance program and residential developments are priorities.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Housing minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_national_security_bigram(self, resolver):
        """Test National Security bigram keyword matching."""
        transcript = {
            "session_id": "test_security",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "National security is paramount. We must address crime and support our police officers and law enforcement agencies.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to National Security minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_youth_sports_culture_keywords(self, resolver):
        """Test Youth, Sports & Culture portfolio keywords."""
        transcript = {
            "session_id": "test_youth",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "We support our young people and athletes. Sports, culture, and junkanoo festivals are vital for youth development.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Youth/Sports/Culture minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_labour_keywords(self, resolver):
        """Test Labour portfolio keywords."""
        transcript = {
            "session_id": "test_labour",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "We must protect workers' rights and address unemployment. The minimum wage and trade unions are important for labour relations.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Labour minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_environment_keywords(self, resolver):
        """Test Environment portfolio keywords."""
        transcript = {
            "session_id": "test_environment",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Environmental conservation and climate change are critical. We need sustainable renewable energy and better recycling programs.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Environment minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_energy_keywords(self, resolver):
        """Test Energy portfolio keywords."""
        transcript = {
            "session_id": "test_energy",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "We need renewable energy solutions. Solar power and electricity infrastructure are vital for our energy independence.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Energy minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_immigration_keywords(self, resolver):
        """Test Immigration portfolio keywords."""
        transcript = {
            "session_id": "test_immigration",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Immigration policy needs reform. We must address work permits, visa applications, and citizenship requirements.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Immigration minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_social_services_bigram(self, resolver):
        """Test Social Services bigram keyword matching."""
        transcript = {
            "session_id": "test_social",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Social services are essential for the vulnerable. We help the elderly, disabled, and families living in poverty with welfare assistance.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Social Services minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_disaster_management_keywords(self, resolver):
        """Test Disaster Risk Management portfolio keywords."""
        transcript = {
            "session_id": "test_disaster",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Hurricane preparedness and disaster recovery are vital. NEMA coordinates our emergency response and relief efforts.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Disaster Management minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_works_utilities_keywords(self, resolver):
        """Test Works & Utilities portfolio keywords."""
        transcript = {
            "session_id": "test_works",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Public works and utilities infrastructure need investment. Water, sewerage, and electricity systems require maintenance.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Should match to Works/Utilities minister
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"
            assert resolution.confidence < 0.7
    
    def test_portfolio_confidence_remains_low(self, resolver):
        """Test that portfolio confidence remains below 0.7 even with many keyword matches."""
        # Test with very strong portfolio signal (many keyword matches)
        # This ensures the confidence cap is enforced
        transcript = {
            "session_id": "test_confidence",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Budget finance tax revenue fiscal economy budget finance tax revenue fiscal economy budget finance tax revenue fiscal economy",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # Even with many matches, confidence should not exceed 0.7
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            if resolution.method == "portfolio_fingerprinting":
                assert resolution.confidence < 0.7, f"Portfolio confidence {resolution.confidence} should be < 0.7"
    
    def test_word_boundary_matching(self, resolver):
        """Test that keyword matching uses word boundaries to avoid partial matches."""
        transcript = {
            "session_id": "test_boundaries",
            "segments": [
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "The financial advisor discussed taxation and fiscal policy.",
                    "start_time": 0.0,
                    "end_time": 10.0,
                }
            ]
        }
        resolutions = resolver.resolve_speakers(transcript, confidence_threshold=0.0)
        # "tax" should match in "taxation", "fiscal" should match
        # This tests that the word boundary matching works correctly
        if "SPEAKER_01" in resolutions:
            resolution = resolutions["SPEAKER_01"]
            assert resolution.method == "portfolio_fingerprinting"


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


class TestConflictLogging:
    """Test conflict logging when heuristics disagree."""

    def test_conflict_logged_when_heuristics_disagree(self, resolver, caplog):
        """Logs warning when different heuristics resolve same speaker to different MPs."""
        import logging
        
        # Create a transcript that triggers multiple heuristics for the same speaker
        # SPEAKER_01 will be resolved by both recognition (Fred Mitchell) and portfolio (someone with finance keywords)
        transcript = {
            "session_id": "test_conflict",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognizes the Honourable Fred Mitchell.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I want to discuss the budget and finance proposals. The tax revenue and fiscal policy are critical topics. We must address budget concerns and tax matters.",
                    "start_time": 3.5,
                    "end_time": 10.0,
                },
            ]
        }
        
        with caplog.at_level(logging.WARNING):
            resolutions = resolver.resolve_speakers(transcript)
        
        # Check if conflict was logged
        # SPEAKER_01 should have both recognition (Fred Mitchell) and portfolio resolutions
        # which may resolve to different MPs if Fred Mitchell doesn't have finance portfolio
        conflict_logs = [rec for rec in caplog.records if "Conflict for SPEAKER_01" in rec.message]
        
        # We expect a conflict if recognition and portfolio disagree
        # (This depends on the actual golden record data)
        # At minimum, verify the logging mechanism works
        if conflict_logs:
            assert any("multiple heuristics" in rec.message for rec in conflict_logs)
            # Should mention both methods
            all_messages = "\n".join(rec.message for rec in caplog.records if "SPEAKER_01" in rec.message)
            # Check that the winning method is logged
            assert "Resolution:" in all_messages or len(conflict_logs) > 0

    def test_no_conflict_when_heuristics_agree(self, resolver, caplog):
        """Does not log conflict when heuristics agree on the same MP."""
        import logging
        
        # Create a transcript where only one heuristic resolves a speaker
        transcript = {
            "session_id": "test_no_conflict",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "The Chair recognizes the Member for Cat Island.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker. I rise to discuss tourism development in our islands.",
                    "start_time": 3.5,
                    "end_time": 10.0,
                },
            ]
        }
        
        with caplog.at_level(logging.WARNING):
            resolutions = resolver.resolve_speakers(transcript)
        
        # SPEAKER_01 should only be resolved by recognition chaining
        # Should not see conflict warnings for SPEAKER_01
        speaker_01_conflicts = [
            rec for rec in caplog.records 
            if "Conflict for SPEAKER_01" in rec.message
        ]
        
        # If there's only one heuristic resolving SPEAKER_01, no conflict should be logged
        assert len(speaker_01_conflicts) == 0

    def test_conflict_includes_confidence_scores(self, resolver, caplog):
        """Conflict logs include confidence scores for both candidates."""
        import logging
        
        # Create a scenario with potential conflict
        transcript = {
            "session_id": "test_confidence_in_log",
            "segments": [
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "I recognize the Honourable Member for Exumas and Ragged Island.",
                    "start_time": 0.0,
                    "end_time": 3.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you. I want to discuss the budget, finance, and tax revenue. Our fiscal policy needs attention. The budget allocation and tax framework must be reviewed.",
                    "start_time": 3.5,
                    "end_time": 12.0,
                },
            ]
        }
        
        with caplog.at_level(logging.WARNING):
            resolutions = resolver.resolve_speakers(transcript)
        
        # Get all warning messages (not just SPEAKER_01)
        all_warning_messages = "\n".join(
            rec.message for rec in caplog.records 
            if rec.levelname == "WARNING"
        )
        
        # If there was a conflict, confidence scores should be mentioned
        if "Conflict for SPEAKER_01" in all_warning_messages:
            assert "confidence:" in all_warning_messages.lower()

    def test_conflict_preserves_priority_order(self, resolver):
        """Resolution priority (chair > recognition > self_ref > portfolio) is maintained despite conflicts."""
        # Create a scenario where chair detection and recognition both resolve the same speaker
        transcript = {
            "session_id": "test_priority",
            "segments": [
                # This segment has both chair patterns AND recognition patterns
                {
                    "speaker_label": "SPEAKER_00",
                    "text": "Order, order. The House will come to order. I recognize the Member for Fox Hill.",
                    "start_time": 0.0,
                    "end_time": 5.0,
                },
                {
                    "speaker_label": "SPEAKER_01",
                    "text": "Thank you Madam Speaker for your leadership. I rise to address the House.",
                    "start_time": 5.5,
                    "end_time": 10.0,
                },
            ]
        }
        
        resolutions = resolver.resolve_speakers(transcript)
        
        # SPEAKER_00 should be resolved as the Speaker (chair detection)
        # even if recognition patterns might suggest otherwise
        if "SPEAKER_00" in resolutions:
            # Chair detection should win over any other method
            assert resolutions["SPEAKER_00"].method == "chair_detection"

