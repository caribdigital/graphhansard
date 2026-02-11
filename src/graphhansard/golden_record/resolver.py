"""Alias Resolution API for the Golden Record.

Implements the resolution cascade defined in SRD §6.4:
1. Exact match (normalized, temporally-aware)
2. Fuzzy match (RapidFuzz, configurable threshold)
3. Unresolved (logged for human review)

Co-reference / anaphoric resolution (step 3 in SRD) is handled
by the brain.entity_extractor module, not here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResolutionResult:
    """Result of an alias resolution attempt."""

    node_id: str | None
    confidence: float
    method: str  # "exact" | "fuzzy" | "unresolved"
    collision_warning: str | None = None


class AliasResolver:
    """Resolves raw mention strings to canonical MP node IDs.

    See SRD §6.4 for the full resolution cascade specification.
    """

    def __init__(self, golden_record_path: str, fuzzy_threshold: int = 85):
        raise NotImplementedError("AliasResolver not yet implemented — see Issue #2")

    def resolve(
        self, mention: str, debate_date: str | None = None
    ) -> ResolutionResult:
        """Resolve a raw mention string to an MP node_id.

        Args:
            mention: Raw text mention (e.g., "da Memba for Cat Island")
            debate_date: Optional ISO date for temporal disambiguation

        Returns:
            ResolutionResult with node_id, confidence, and method.
        """
        raise NotImplementedError

    def build_inverted_index(self) -> dict[str, str]:
        """Build the alias → node_id inverted index from mps.json."""
        raise NotImplementedError
