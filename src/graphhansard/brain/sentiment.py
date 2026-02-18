"""Stage 3 — Sentiment scoring for MP-to-MP mentions.

Classifies each mention as positive, neutral, or negative using the
context window. See SRD §8.4 (BR-16 through BR-20).

Usage Example:
    >>> from graphhansard.brain.sentiment import SentimentScorer
    >>> scorer = SentimentScorer()
    >>> 
    >>> # Score a single context window
    >>> context = "I commend the Prime Minister for his excellent work on this bill."
    >>> result = scorer.score(context)
    >>> print(result.label)  # SentimentLabel.POSITIVE
    >>> print(result.confidence)  # 0.85
    >>> 
    >>> # Score multiple contexts in batch
    >>> contexts = [
    ...     "The Minister has failed to answer the question.",
    ...     "The Attorney General tabled the bill yesterday.",
    ... ]
    >>> results = scorer.score_batch(contexts)
    >>> 
    >>> # Check for parliamentary markers
    >>> context_with_markers = "On a point of order! The Member is out of line."
    >>> result = scorer.score(context_with_markers)
    >>> print(result.parliamentary_markers)  # ['point_of_order', 'heckling']
    >>> 
    >>> # Procedural Chair/Speaker recognition (Issue #55)
    >>> procedural = "The Chair recognizes the Honourable Member for Freetown."
    >>> result = scorer.score(procedural)
    >>> print(result.label)  # SentimentLabel.NEUTRAL (pattern-based, skips model)
    >>> print(result.confidence)  # 1.0

Integration with Entity Extraction:
    >>> from graphhansard.brain.entity_extractor import EntityExtractor
    >>> from graphhansard.brain.sentiment import SentimentScorer
    >>> 
    >>> # Extract mentions from transcript
    >>> extractor = EntityExtractor('path/to/mps.json')
    >>> mentions = extractor.extract_mentions(transcript)
    >>> 
    >>> # Score sentiment for each mention
    >>> scorer = SentimentScorer()
    >>> for mention in mentions:
    ...     sentiment = scorer.score(mention.context_window)
    ...     print(f"{mention.raw_mention}: {sentiment.label} ({sentiment.confidence:.2f})")

Notes:
    - Model is lazily loaded on first use to save memory
    - Procedural Chair/Speaker recognition patterns are detected first and assigned
      neutral sentiment without calling the model (Issue #55)
    - Zero-shot classification uses facebook/bart-large-mnli by default
    - Parliamentary markers are detected using pattern matching (case-insensitive)
    - Confidence scores range from 0.0 to 1.0
    - v1.0 achieves ~75% accuracy on test set (zero-shot approach)
    - v1.1 will use fine-tuned model on parliamentary data for improved accuracy
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

    # Parliamentary markers (BR-19)
    PARLIAMENTARY_MARKERS = {
        "point_of_order": [
            "on a point of order",
            "point of order",
            "i rise on a point",
            "i rise to a point",
        ],
        "direct_challenge": [
            "will the member yield",
            "will the honourable member",
            "does the member agree",
            "will my friend yield",
        ],
        "heckling": [
            "sit down",
            "order! order!",
            "shame!",
            "withdraw!",
        ],
    }

    # Procedural patterns (Issue #55 - GR-7)
    # These are neutral procedural statements that should not be scored as positive.
    # Both American ("recognize") and British ("recognise") spellings are included
    # because Whisper transcription may produce either form.
    PROCEDURAL_PATTERNS = [
        "the chair recognizes",
        "the chair recognises",
        "the speaker recognizes",
        "the speaker recognises",
        "the deputy speaker recognizes",
        "the deputy speaker recognises",
        "i recognize the member",
        "i recognise the member",
        "i recognize the honourable member",
        "i recognise the honourable member",
        "could you recognize the",
        "could you recognise the",
        "madam speaker recognizes",
        "madam speaker recognises",
        "mr speaker recognizes",
        "mr speaker recognises",
        "mr. speaker recognizes",
        "mr. speaker recognises",
    ]

    def __init__(
        self, model_name: str = "facebook/bart-large-mnli", device: str | None = None
    ):
        """Initialize the sentiment scorer.

        Args:
            model_name: HuggingFace model identifier for zero-shot classification.
                       Default is facebook/bart-large-mnli for v1.0.
            device: Device to use for inference. Options:
                   - None: Auto-detect (GPU if available, else CPU)
                   - "cpu": Force CPU
                   - "cuda" or "gpu": Force GPU
        """
        self.model_name = model_name
        self._device = device
        self.pipeline = None
        self._labels = [
            "supportive reference",
            "neutral or procedural reference",
            "hostile or critical reference",
        ]

    def _load_model(self):
        """Lazy load the model pipeline on first use."""
        if self.pipeline is None:
            try:
                from transformers import pipeline
                import torch
            except ImportError as e:
                raise ImportError(
                    "transformers library is required for SentimentScorer. "
                    "Install with: pip install transformers"
                ) from e

            # Determine device
            if self._device is None:
                # Auto-detect: GPU if available, else CPU
                device = 0 if torch.cuda.is_available() else -1
            elif self._device.lower() == "cpu":
                device = -1
            elif self._device.lower() in ("cuda", "gpu"):
                device = 0
            else:
                # Allow numeric device IDs (e.g., "0", "1")
                try:
                    device = int(self._device)
                except ValueError:
                    device = -1

            self.pipeline = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=device,
            )

    def score(self, context_window: str) -> SentimentResult:
        """Classify the sentiment of a mention context window.

        Args:
            context_window: Text containing the mention with surrounding context.

        Returns:
            SentimentResult with label, confidence, and parliamentary markers.
        """
        # Check for procedural patterns first (Issue #55)
        # Chair/Speaker recognition should be neutral, not positive
        if self._is_procedural(context_window):
            markers = self._detect_markers(context_window)
            return SentimentResult(
                label=SentimentLabel.NEUTRAL,
                confidence=1.0,  # High confidence for pattern-based classification
                parliamentary_markers=markers,
            )

        self._load_model()

        # Run zero-shot classification
        result = self.pipeline(
            context_window,
            candidate_labels=self._labels,
            multi_label=False,
        )

        return self._parse_result(result, context_window)

    def _parse_result(self, result: dict, context_window: str) -> SentimentResult:
        """Parse pipeline result into SentimentResult.

        Args:
            result: Output from pipeline (dict with 'labels' and 'scores').
            context_window: Original context text for marker detection.

        Returns:
            SentimentResult with label, confidence, and parliamentary markers.
        """
        # Map model output to our sentiment labels
        top_label = result["labels"][0]
        confidence = result["scores"][0]

        if "supportive" in top_label:
            sentiment_label = SentimentLabel.POSITIVE
        elif "hostile" in top_label or "critical" in top_label:
            sentiment_label = SentimentLabel.NEGATIVE
        else:
            sentiment_label = SentimentLabel.NEUTRAL

        # Detect parliamentary markers
        markers = self._detect_markers(context_window)

        return SentimentResult(
            label=sentiment_label,
            confidence=confidence,
            parliamentary_markers=markers,
        )

    def score_batch(
        self, contexts: list[str], batch_size: int = 32
    ) -> list[SentimentResult]:
        """Classify sentiment for a batch of context windows.

        Procedural patterns (Issue #55) are handled first without calling the
        model. Remaining contexts are sent through the pipeline in batches.

        Args:
            contexts: List of context window strings.
            batch_size: Number of samples to process in each batch (default: 32).
                       Larger batches are faster but use more memory.

        Returns:
            List of SentimentResult objects in the same order.
        """
        if not contexts:
            return []

        # Partition into procedural and non-procedural contexts
        results: list[SentimentResult | None] = [None] * len(contexts)
        non_procedural: list[tuple[int, str]] = []

        for i, ctx in enumerate(contexts):
            if self._is_procedural(ctx):
                markers = self._detect_markers(ctx)
                results[i] = SentimentResult(
                    label=SentimentLabel.NEUTRAL,
                    confidence=1.0,
                    parliamentary_markers=markers,
                )
            else:
                non_procedural.append((i, ctx))

        # Batch-process non-procedural contexts through the model
        if non_procedural:
            self._load_model()

            batch_texts = [ctx for _, ctx in non_procedural]
            pipeline_results = self.pipeline(
                batch_texts,
                candidate_labels=self._labels,
                multi_label=False,
                batch_size=batch_size,
            )

            for (i, ctx), r in zip(non_procedural, pipeline_results):
                results[i] = self._parse_result(r, ctx)

        return results  # type: ignore[return-value]

    def _is_procedural(self, text: str) -> bool:
        """Check if text contains procedural Chair/Speaker recognition patterns.

        These are neutral procedural statements that should not be scored as positive
        sentiment. See Issue #55 for context.

        Args:
            text: The context window text.

        Returns:
            True if text matches procedural patterns, False otherwise.
        """
        text_lower = text.lower()

        for pattern in self.PROCEDURAL_PATTERNS:
            if pattern in text_lower:
                return True

        return False

    def _detect_markers(self, text: str) -> list[str]:
        """Detect parliamentary-specific markers in text.

        Args:
            text: The context window text.

        Returns:
            List of detected marker types (e.g., ['point_of_order', 'heckling']).
        """
        text_lower = text.lower()
        detected = []

        for marker_type, patterns in self.PARLIAMENTARY_MARKERS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    detected.append(marker_type)
                    break  # Only add marker type once

        return detected
