"""Alias Resolution API for the Golden Record.

Implements the resolution cascade defined in SRD §6.4:
1. Exact match (normalized, temporally-aware)
2. Fuzzy match (RapidFuzz, configurable threshold)
3. Unresolved (logged for human review)

Co-reference / anaphoric resolution (step 3 in SRD) is handled
by the brain.entity_extractor module, not here.

Includes Bahamian Creole normalization (BC-1, BC-2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from rapidfuzz import fuzz

from .models import GoldenRecord


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
    Includes Bahamian Creole normalization (BC-1, BC-2).
    """

    def __init__(
        self, 
        golden_record_path: str, 
        fuzzy_threshold: int = 85,
        normalize_creole: bool = True,
    ):
        """Initialize the AliasResolver.

        Args:
            golden_record_path: Path to mps.json
            fuzzy_threshold: Minimum score for fuzzy matches (0-100), default 85
            normalize_creole: Whether to apply Bahamian Creole normalization (default: True)
        """
        self.golden_record_path = Path(golden_record_path)
        self.fuzzy_threshold = fuzzy_threshold
        self.normalize_creole = normalize_creole
        self.unresolved_log: list[dict] = []

        # Load the golden record
        data = self.golden_record_path.read_text(encoding="utf-8")
        self.golden_record = GoldenRecord.model_validate_json(data)

        # Build the inverted index
        self._alias_index = self.build_inverted_index()

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
        # Apply Bahamian Creole normalization if enabled (BC-1, BC-2)
        if self.normalize_creole:
            # Import here to avoid circular dependency
            from ..brain.creole_utils import normalize_bahamian_creole
            mention = normalize_bahamian_creole(mention)
        
        # Normalize the mention
        normalized = self._normalize(mention)

        # Parse debate_date if provided
        query_date = date.fromisoformat(debate_date) if debate_date else None

        # Step 1: Exact match
        result = self._exact_match(normalized, query_date)
        if result:
            return result

        # Step 2: Fuzzy match
        result = self._fuzzy_match(normalized, query_date)
        if result:
            return result

        # Step 3: Unresolved
        self._log_unresolved(mention, debate_date)
        return ResolutionResult(
            node_id=None, confidence=0.0, method="unresolved", collision_warning=None
        )

    def build_inverted_index(self) -> dict[str, list[str]]:
        """Build the alias → node_ids inverted index from mps.json.

        Returns a dictionary mapping normalized aliases to lists of node_ids.
        Multiple node_ids indicate a collision.
        """
        index: dict[str, list[str]] = {}

        for mp in self.golden_record.mps:
            for alias in mp.all_aliases:
                normalized = self._normalize(alias)
                if normalized not in index:
                    index[normalized] = []
                if mp.node_id not in index[normalized]:
                    index[normalized].append(mp.node_id)

        return index

    def _normalize(self, text: str) -> str:
        """Normalize text for matching: lowercase, strip whitespace."""
        return text.strip().lower()

    def _exact_match(
        self, normalized: str, query_date: date | None
    ) -> ResolutionResult | None:
        """Attempt exact match against the inverted index.

        Args:
            normalized: Normalized mention string
            query_date: Optional date for temporal filtering

        Returns:
            ResolutionResult if match found, None otherwise
        """
        # Check if alias exists in index
        if normalized not in self._alias_index:
            return None

        candidates = self._alias_index[normalized]

        # If temporal filtering is requested, filter by date
        if query_date:
            temporal_candidates = []
            for node_id in candidates:
                mp = next(mp for mp in self.golden_record.mps if mp.node_id == node_id)
                # Check if this alias is valid on the query date
                valid_aliases = [self._normalize(a) for a in mp.aliases_on(query_date)]
                if normalized in valid_aliases:
                    temporal_candidates.append(node_id)

            candidates = temporal_candidates

        if not candidates:
            return None

        # Check for collision
        collision_warning = None
        if len(candidates) > 1:
            # Check if this is a known collision
            known_collision = next(
                (
                    c
                    for c in self.golden_record.alias_collisions
                    if self._normalize(c.alias) == normalized
                ),
                None,
            )
            if known_collision:
                collision_warning = (
                    f"Alias collision: {known_collision.resolution_strategy}"
                )
            else:
                collision_warning = (
                    f"Unexpected alias collision: {', '.join(candidates)}"
                )

        # If only one candidate after temporal filtering, return it
        if len(candidates) == 1:
            return ResolutionResult(
                node_id=candidates[0],
                confidence=1.0,
                method="exact",
                collision_warning=collision_warning,
            )

        # Multiple candidates - return first with collision warning
        return ResolutionResult(
            node_id=candidates[0],
            confidence=1.0,
            method="exact",
            collision_warning=collision_warning,
        )

    def _fuzzy_match(
        self, normalized: str, query_date: date | None
    ) -> ResolutionResult | None:
        """Attempt fuzzy match using RapidFuzz.

        Args:
            normalized: Normalized mention string
            query_date: Optional date for temporal filtering

        Returns:
            ResolutionResult if match found above threshold, None otherwise
        """
        best_score = 0
        best_node_id = None
        found_perfect = False

        # Get all candidate aliases
        for mp in self.golden_record.mps:
            # Get aliases based on temporal context
            if query_date:
                aliases = mp.aliases_on(query_date)
            else:
                aliases = mp.all_aliases

            # Try fuzzy matching against each alias
            for alias in aliases:
                normalized_alias = self._normalize(alias)
                score = fuzz.token_sort_ratio(normalized, normalized_alias)

                if score > best_score:
                    best_score = score
                    best_node_id = mp.node_id
                    if best_score == 100:
                        found_perfect = True
                        break
            if found_perfect:
                break

        # Check if best match exceeds threshold
        if best_score >= self.fuzzy_threshold:
            # Normalize confidence to 0-1 range
            confidence = best_score / 100.0

            return ResolutionResult(
                node_id=best_node_id,
                confidence=confidence,
                method="fuzzy",
                collision_warning=None,
            )

        return None

    def _log_unresolved(self, mention: str, debate_date: str | None) -> None:
        """Log an unresolved mention for human review.

        Args:
            mention: The raw mention that could not be resolved
            debate_date: Optional date context
        """
        self.unresolved_log.append(
            {
                "mention": mention,
                "debate_date": debate_date,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def save_unresolved_log(self, output_path: str) -> None:
        """Save the unresolved mentions log to a JSON file.

        Args:
            output_path: Path to save the log file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.unresolved_log, f, indent=2, ensure_ascii=False)

    def save_index(self, output_path: str) -> None:
        """Save the inverted alias index to a JSON file.

        Args:
            output_path: Path to save the index file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self._alias_index, f, indent=2, ensure_ascii=False)
