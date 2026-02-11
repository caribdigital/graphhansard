"""Stage 2 — Entity extraction, co-reference resolution, and mention logging.

Scans transcripts for MP references using pattern matching and NER,
resolves via the Golden Record, and handles anaphoric references.
See SRD §8.3 (BR-9 through BR-15).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ResolutionMethod(str, Enum):
    EXACT = "exact"
    FUZZY = "fuzzy"
    COREFERENCE = "coreference"
    LLM = "llm"
    UNRESOLVED = "unresolved"


class MentionRecord(BaseModel):
    """A single MP-to-MP mention extracted from a transcript."""

    session_id: str
    source_node_id: str = Field(description="MP who made the mention (the speaker)")
    target_node_id: str | None = Field(
        description="MP who was mentioned (resolved)"
    )
    raw_mention: str = Field(description="Exact text as spoken/transcribed")
    resolution_method: ResolutionMethod
    resolution_score: float = Field(description="Confidence 0.0-1.0")
    timestamp_start: float
    timestamp_end: float
    context_window: str = Field(description="Surrounding text for verification")
    segment_index: int


class EntityExtractor:
    """Extracts and resolves MP mentions from diarized transcripts.

    See SRD §8.3 for specification.
    """

    def __init__(self, golden_record_path: str):
        raise NotImplementedError("EntityExtractor not yet implemented — see Issue #10")

    def extract_mentions(self, transcript: dict) -> list[MentionRecord]:
        """Extract all MP mentions from a diarized transcript."""
        raise NotImplementedError

    def resolve_coreference(
        self, mention: str, speaker_history: list[dict]
    ) -> str | None:
        """Resolve anaphoric/deictic references using speaker turn context."""
        raise NotImplementedError
