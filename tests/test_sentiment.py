"""Tests for Stage 3 — Sentiment Scoring.

Tests sentiment classification, parliamentary marker detection, and confidence scoring.
See Issue #12 (BR-16 through BR-20).
"""


import pytest

from graphhansard.brain.sentiment import (
    SentimentLabel,
    SentimentResult,
    SentimentScorer,
)


@pytest.fixture
def scorer():
    """Create a SentimentScorer instance for testing."""
    return SentimentScorer()


@pytest.fixture
def mock_pipeline():
    """Create a mock pipeline for testing without internet access."""
    def _mock_pipeline(text, candidate_labels, multi_label=False, batch_size=None):
        # Simple rule-based mock for testing
        # Handle both single text and batch processing
        def _classify_text(txt):
            txt_lower = txt.lower()

            positive_words = [
                "commend",
                "excellent",
                "support",
                "outstanding",
                "praise",
            ]
            negative_words = [
                "failed",
                "reckless",
                "misguided",
                "disaster",
                "critical",
            ]

            if any(word in txt_lower for word in positive_words):
                return {
                    "labels": [
                        "supportive reference",
                        "neutral or procedural reference",
                        "hostile or critical reference",
                    ],
                    "scores": [0.85, 0.10, 0.05],
                }
            elif any(word in txt_lower for word in negative_words):
                return {
                    "labels": [
                        "hostile or critical reference",
                        "neutral or procedural reference",
                        "supportive reference",
                    ],
                    "scores": [0.80, 0.15, 0.05],
                }
            else:
                return {
                    "labels": [
                        "neutral or procedural reference",
                        "supportive reference",
                        "hostile or critical reference",
                    ],
                    "scores": [0.75, 0.15, 0.10],
                }

        # Support batch processing (list input)
        if isinstance(text, list):
            return [_classify_text(t) for t in text]
        else:
            return _classify_text(text)

    return _mock_pipeline


@pytest.fixture
def scorer_with_mock(scorer, mock_pipeline):
    """Create a scorer with mocked pipeline."""
    scorer.pipeline = mock_pipeline
    return scorer


class TestSentimentScorerInit:
    """Test SentimentScorer initialization."""

    def test_scorer_initializes(self):
        """Scorer initializes without loading model immediately."""
        scorer = SentimentScorer()
        assert scorer is not None
        assert scorer.model_name == "facebook/bart-large-mnli"
        assert scorer.pipeline is None  # Lazy loading

    def test_scorer_custom_model(self):
        """Scorer accepts custom model name."""
        scorer = SentimentScorer(model_name="custom/model")
        assert scorer.model_name == "custom/model"

    def test_scorer_default_device_none(self):
        """Scorer initializes with device=None by default."""
        scorer = SentimentScorer()
        assert scorer._device is None

    def test_scorer_cpu_device(self):
        """Scorer accepts device='cpu' parameter."""
        scorer = SentimentScorer(device="cpu")
        assert scorer._device == "cpu"

    def test_scorer_gpu_device(self):
        """Scorer accepts device='gpu' parameter."""
        scorer = SentimentScorer(device="gpu")
        assert scorer._device == "gpu"

    def test_scorer_cuda_device(self):
        """Scorer accepts device='cuda' parameter."""
        scorer = SentimentScorer(device="cuda")
        assert scorer._device == "cuda"

    def test_scorer_numeric_device(self):
        """Scorer accepts numeric device ID as integer."""
        scorer = SentimentScorer(device=0)
        assert scorer._device == 0


class TestDeviceSelection:
    """Test device selection logic."""

    def test_device_parameter_stored(self):
        """Device parameter is stored correctly."""
        scorer_cpu = SentimentScorer(device="cpu")
        assert scorer_cpu._device == "cpu"

        scorer_gpu = SentimentScorer(device="gpu")
        assert scorer_gpu._device == "gpu"

        scorer_none = SentimentScorer(device=None)
        assert scorer_none._device is None

        scorer_numeric = SentimentScorer(device="1")
        assert scorer_numeric._device == "1"


class TestSentimentClassification:
    """Test sentiment classification (BR-16, BR-17, BR-20)."""

    def test_positive_sentiment(self, scorer_with_mock):
        """Classifies supportive/praising references as POSITIVE."""
        context = (
            "I commend the Prime Minister for his excellent work on this bill. "
            "His leadership has been exemplary and I fully support his position."
        )
        result = scorer_with_mock.score(context)

        assert isinstance(result, SentimentResult)
        assert result.label == SentimentLabel.POSITIVE
        assert 0.0 <= result.confidence <= 1.0

    def test_negative_sentiment(self, scorer_with_mock):
        """Classifies hostile/critical references as NEGATIVE."""
        context = (
            "The Member for Cat Island has completely misunderstood the issue. "
            "His proposal is reckless and would be disastrous for our country."
        )
        result = scorer_with_mock.score(context)

        assert isinstance(result, SentimentResult)
        assert result.label == SentimentLabel.NEGATIVE
        assert 0.0 <= result.confidence <= 1.0

    def test_neutral_sentiment(self, scorer_with_mock):
        """Classifies procedural/factual references as NEUTRAL."""
        context = (
            "The Minister of Finance tabled the report yesterday. "
            "The Member for Fox Hill asked three questions about the budget."
        )
        result = scorer_with_mock.score(context)

        assert isinstance(result, SentimentResult)
        assert result.label == SentimentLabel.NEUTRAL
        assert 0.0 <= result.confidence <= 1.0

    def test_confidence_score_range(self, scorer_with_mock):
        """Confidence scores are always between 0.0 and 1.0."""
        contexts = [
            "I strongly support the Member's position.",
            "The Minister presented the data.",
            "This is an outrageous proposal from the Member.",
        ]

        for context in contexts:
            result = scorer_with_mock.score(context)
            assert 0.0 <= result.confidence <= 1.0


class TestParliamentaryMarkers:
    """Test parliamentary marker detection (BR-19)."""

    def test_point_of_order_detection(self, scorer_with_mock):
        """Detects 'point of order' markers."""
        context = (
            "On a point of order, Mr. Speaker! "
            "The Member has misstated the facts."
        )
        result = scorer_with_mock.score(context)

        assert "point_of_order" in result.parliamentary_markers

    def test_direct_challenge_detection(self, scorer_with_mock):
        """Detects direct challenges like 'Will the Member yield?'"""
        context = "Will the Member yield to a question about his proposal?"
        result = scorer_with_mock.score(context)

        assert "direct_challenge" in result.parliamentary_markers

    def test_heckling_detection(self, scorer_with_mock):
        """Detects heckling indicators."""
        context = "Sit down! Order! Order! The Member must withdraw that statement."
        result = scorer_with_mock.score(context)

        assert "heckling" in result.parliamentary_markers

    def test_multiple_markers(self, scorer_with_mock):
        """Detects multiple parliamentary markers in one context."""
        context = (
            "On a point of order! Will the Member yield? Sit down! "
            "The Speaker must restore order in this House."
        )
        result = scorer_with_mock.score(context)

        # Should detect multiple marker types
        assert len(result.parliamentary_markers) >= 2
        assert "point_of_order" in result.parliamentary_markers
        assert "direct_challenge" in result.parliamentary_markers
        assert "heckling" in result.parliamentary_markers

    def test_no_markers(self, scorer_with_mock):
        """Returns empty list when no markers present."""
        context = "The Minister spoke about economic policy yesterday."
        result = scorer_with_mock.score(context)

        assert result.parliamentary_markers == []

    def test_case_insensitive_markers(self, scorer_with_mock):
        """Marker detection is case-insensitive."""
        context = "ON A POINT OF ORDER, the member is out of line!"
        result = scorer_with_mock.score(context)

        assert "point_of_order" in result.parliamentary_markers


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_score_batch(self, scorer_with_mock):
        """Processes multiple contexts in batch."""
        contexts = [
            "I commend the Prime Minister for his leadership.",
            "The Minister of Finance tabled the report.",
            "The Member's proposal is completely misguided.",
        ]

        results = scorer_with_mock.score_batch(contexts)

        assert len(results) == 3
        assert all(isinstance(r, SentimentResult) for r in results)
        # Should get different sentiments
        assert results[0].label == SentimentLabel.POSITIVE
        assert results[1].label == SentimentLabel.NEUTRAL
        assert results[2].label == SentimentLabel.NEGATIVE

    def test_empty_batch(self, scorer_with_mock):
        """Handles empty batch gracefully."""
        results = scorer_with_mock.score_batch([])
        assert results == []


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_context(self, scorer_with_mock):
        """Handles empty context string."""
        result = scorer_with_mock.score("")

        # Should still return a result (likely neutral)
        assert isinstance(result, SentimentResult)
        assert result.label in [
            SentimentLabel.POSITIVE,
            SentimentLabel.NEUTRAL,
            SentimentLabel.NEGATIVE,
        ]

    def test_very_short_context(self, scorer_with_mock):
        """Handles very short context."""
        result = scorer_with_mock.score("Good.")

        assert isinstance(result, SentimentResult)
        assert 0.0 <= result.confidence <= 1.0

    def test_very_long_context(self, scorer_with_mock):
        """Handles long context (multiple sentences)."""
        context = " ".join([
            "The Member for Cat Island has raised an important point.",
            "I appreciate his diligence in researching this matter.",
            "However, I must disagree with his conclusions.",
            "The data he presents does not support his argument.",
            "We must consider alternative approaches to this issue.",
        ])

        result = scorer_with_mock.score(context)

        assert isinstance(result, SentimentResult)
        assert 0.0 <= result.confidence <= 1.0


class TestIntegrationWithMentionRecords:
    """Test integration with entity extraction output."""

    def test_score_mention_context_window(self, scorer_with_mock):
        """Scores context from MentionRecord format."""
        # Simulating a context window from entity extraction
        context = (
            "Thank you, Mr. Speaker. I want to commend The Member for Fox Hill "
            "for his outstanding work on the education committee. "
            "His dedication to our students is truly commendable."
        )

        result = scorer_with_mock.score(context)

        assert result.label == SentimentLabel.POSITIVE
        assert result.confidence > 0.5  # Should be confident


class TestParliamentaryContext:
    """Test with realistic Bahamian parliamentary text."""

    def test_bahamian_parliamentary_positive(self, scorer_with_mock):
        """Handles positive Bahamian parliamentary speech."""
        context = (
            "Mr. Speaker, I rise to commend my colleague, "
            "the Member for Englerston, for his passionate advocacy "
            "on behalf of his constituents."
        )

        result = scorer_with_mock.score(context)
        assert result.label == SentimentLabel.POSITIVE

    def test_bahamian_parliamentary_negative(self, scorer_with_mock):
        """Handles critical Bahamian parliamentary speech."""
        context = (
            "Mr. Speaker, the Minister has failed to answer the question. "
            "This is yet another example of this government's lack of transparency."
        )

        result = scorer_with_mock.score(context)
        assert result.label == SentimentLabel.NEGATIVE

    def test_bahamian_parliamentary_neutral(self, scorer_with_mock):
        """Handles procedural Bahamian parliamentary speech."""
        context = (
            "Mr. Speaker, the Attorney General tabled the bill yesterday. "
            "It will be debated in committee next Tuesday."
        )

        result = scorer_with_mock.score(context)
        assert result.label == SentimentLabel.NEUTRAL


class TestModelLazyLoading:
    """Test lazy loading behavior."""

    def test_model_not_loaded_on_init(self):
        """Model is not loaded until first use."""
        scorer = SentimentScorer()
        assert scorer.pipeline is None

    @pytest.mark.skip(reason="Requires internet access to download model")
    def test_model_loaded_on_first_score(self, scorer):
        """Model loads on first score() call."""
        assert scorer.pipeline is None
        scorer.score("Test context")
        assert scorer.pipeline is not None

    @pytest.mark.skip(reason="Requires internet access to download model")
    def test_model_reused_after_loading(self, scorer):
        """Model is reused for subsequent calls."""
        scorer.score("First call")
        pipeline_ref = scorer.pipeline
        scorer.score("Second call")
        assert scorer.pipeline is pipeline_ref  # Same object


class TestProceduralPatternDetection:
    """Test procedural pattern detection (Issue #55 - GR-7).

    Chair/Speaker recognition phrases should be classified as neutral,
    not positive, to avoid false positives in sentiment analysis.
    """

    def test_chair_recognizes_pattern(self, scorer):
        """Detects 'The Chair recognizes' as procedural."""
        context = "The Chair recognizes the Honourable Member for Freetown."
        result = scorer.score(context)
        
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 1.0  # Pattern-based classification

    def test_speaker_recognizes_pattern(self, scorer):
        """Detects 'The Speaker recognizes' as procedural."""
        context = "The Speaker recognizes the Member for Marco City."
        result = scorer.score(context)
        
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 1.0

    def test_i_recognize_pattern(self, scorer):
        """Detects 'I recognize the member' as procedural."""
        context = "I recognize the member for Golden Isles to speak on this matter."
        result = scorer.score(context)
        
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 1.0

    def test_deputy_speaker_recognizes(self, scorer):
        """Detects 'The Deputy Speaker recognizes' as procedural."""
        context = "The Deputy Speaker recognizes the Honourable Member."
        result = scorer.score(context)
        
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 1.0

    def test_madam_speaker_recognizes(self, scorer):
        """Detects 'Madam Speaker recognizes' as procedural."""
        context = "Madam Speaker recognizes the Member for Cat Island."
        result = scorer.score(context)
        
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 1.0

    def test_mr_speaker_recognizes(self, scorer):
        """Detects 'Mr Speaker recognizes' as procedural."""
        context = "Mr Speaker recognizes the Honourable Member for Nassau."
        result = scorer.score(context)
        
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 1.0

    def test_could_you_recognize(self, scorer):
        """Detects 'could you recognize the' as procedural."""
        context = "Could you recognize the Member for his point of order?"
        result = scorer.score(context)
        
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 1.0

    def test_case_insensitive_detection(self, scorer):
        """Procedural pattern detection is case-insensitive."""
        contexts = [
            "THE CHAIR RECOGNIZES THE MEMBER FOR FREETOWN.",
            "the chair recognizes the member for freetown.",
            "The Chair Recognizes The Member For Freetown.",
        ]
        
        for context in contexts:
            result = scorer.score(context)
            assert result.label == SentimentLabel.NEUTRAL
            assert result.confidence == 1.0

    def test_non_procedural_with_recognize_word(self, scorer_with_mock):
        """'recognize' in non-procedural context is still scored normally."""
        # Using 'acknowledge' to test sentiment scoring without pattern match.
        # Note: "I recognize the Member's work" would match pattern,
        # which is acceptable since it's ambiguous (procedural vs. praise).
        context = "I acknowledge the Member's excellent work on this committee."
        result = scorer_with_mock.score(context)
        
        # Should be scored by model (positive in this case)
        assert result.label == SentimentLabel.POSITIVE

    def test_procedural_pattern_no_model_call(self, scorer):
        """Procedural patterns skip model loading."""
        # Pipeline should remain None since we skip model call
        assert scorer.pipeline is None
        
        context = "The Chair recognizes the Honourable Member for Freetown."
        result = scorer.score(context)
        
        assert result.label == SentimentLabel.NEUTRAL
        # Pipeline should still be None - no model loading occurred
        assert scorer.pipeline is None

    def test_mixed_procedural_and_sentiment(self, scorer_with_mock):
        """Context with both procedural and sentiment content."""
        # This has procedural pattern, so entire context treated as procedural
        context = "The Chair recognizes the Member. His work has been excellent."
        result = scorer_with_mock.score(context)

        # Procedural pattern takes precedence
        assert result.label == SentimentLabel.NEUTRAL
        assert result.confidence == 1.0

    def test_british_spelling_recognises(self, scorer):
        """Detects British spelling 'recognises' as procedural."""
        contexts = [
            "The Chair recognises the Honourable Member for Cat Island.",
            "The Speaker recognises the Member for Elizabeth.",
            "The Deputy Speaker recognises the Honourable Member.",
            "Madam Speaker recognises the Member for Freetown.",
        ]

        for context in contexts:
            result = scorer.score(context)
            assert result.label == SentimentLabel.NEUTRAL, (
                f"British spelling not detected as procedural: {context}"
            )
            assert result.confidence == 1.0

    def test_is_procedural_directly(self, scorer):
        """Test _is_procedural() method directly for edge cases."""
        assert scorer._is_procedural("The Chair recognizes the member.") is True
        assert scorer._is_procedural("The Chair recognises the member.") is True
        assert scorer._is_procedural("") is False
        assert scorer._is_procedural("No procedural content here.") is False
        assert scorer._is_procedural("I RECOGNIZE THE MEMBER for Fox Hill.") is True

    def test_batch_with_procedural_mix(self, scorer_with_mock):
        """score_batch() correctly handles mix of procedural and non-procedural."""
        contexts = [
            "The Chair recognizes the Honourable Member for Freetown.",
            "I commend the Prime Minister for his excellent leadership.",
            "The Speaker recognises the Member for Marco City.",
        ]

        results = scorer_with_mock.score_batch(contexts)

        assert len(results) == 3
        assert results[0].label == SentimentLabel.NEUTRAL  # procedural
        assert results[0].confidence == 1.0
        assert results[1].label == SentimentLabel.POSITIVE  # model-scored
        assert results[2].label == SentimentLabel.NEUTRAL  # procedural (British)
        assert results[2].confidence == 1.0
