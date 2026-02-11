"""Stage 3 — Sentiment scoring for MP-to-MP mentions.

Classifies each mention as positive, neutral, or negative using the
context window. See SRD §8.4 (BR-16 through BR-20).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SentimentResult(BaseModel):
    """Sentiment classification for a single mention."""

    label: SentimentLabel
    confidence: float = Field(description="Classification confidence 0.0-1.0")
    parliamentary_markers: list[str] = Field(
        default_factory=list,
        description="Detected markers: point_of_order, direct_challenge, heckling",
    )


class SentimentScorer:
    """Scores MP mention context for sentiment.

    v1.0: Zero-shot classification via facebook/bart-large-mnli
    v1.1: Fine-tuned cardiffnlp/twitter-roberta-base-sentiment-latest

    See SRD §8.4 for specification.
    """

    def __init__(self, model_name: str = "facebook/bart-large-mnli"):
        raise NotImplementedError("SentimentScorer not yet implemented — see Issue #12")

    def score(self, context_window: str) -> SentimentResult:
        """Classify the sentiment of a mention context window."""
        raise NotImplementedError

    def score_batch(self, contexts: list[str]) -> list[SentimentResult]:
        """Classify sentiment for a batch of context windows."""
        raise NotImplementedError
