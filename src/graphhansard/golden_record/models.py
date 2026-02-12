"""Pydantic v2 data models for the Golden Record.

Schemas defined per SRD §6.3 and §10.1.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

# ---------------------------------------------------------------------------
# Date coercion: JSON stores ISO-8601 strings; we want datetime.date objects
# ---------------------------------------------------------------------------

def _parse_date(v: date | str) -> date:
    if isinstance(v, date):
        return v
    return date.fromisoformat(v)


StrictDate = Annotated[date, BeforeValidator(_parse_date)]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Party(str, Enum):
    PLP = "PLP"
    FNM = "FNM"
    COI = "COI"
    IND = "IND"
    DNA = "DNA"


class Gender(str, Enum):
    M = "M"
    F = "F"
    X = "X"


class NodeType(str, Enum):
    DEBATER = "debater"
    CONTROL = "control"


class SeatStatus(str, Enum):
    ACTIVE = "active"
    RESIGNED = "resigned"
    DECEASED = "deceased"
    SUSPENDED = "suspended"


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

class PortfolioTenure(BaseModel):
    """A single portfolio held by an MP over a specific time period."""

    title: str = Field(description="Full official title")
    short_title: str = Field(description="Commonly used abbreviation")
    start_date: StrictDate
    end_date: StrictDate | None = Field(
        default=None, description="null = currently active"
    )

    def is_active_on(self, query_date: date) -> bool:
        """Return True if this portfolio tenure was active on the given date."""
        if query_date < self.start_date:
            return False
        if self.end_date is None:
            return True
        return query_date <= self.end_date


class MPNode(BaseModel):
    """Canonical profile for a single Member of Parliament.
    
    Per GR-8: Supports versioning by parliamentary term. The node_id is stable 
    across terms (e.g., 'mp_davis_brave'), allowing tracking of MPs who serve 
    in multiple parliaments.
    """

    node_id: str = Field(description="Unique ID, e.g. 'mp_davis_brave'")
    full_name: str = Field(description="Legal full name")
    common_name: str = Field(description="Name in common usage")
    party: Party
    constituency: str = Field(description="Official constituency name")
    is_cabinet: bool
    is_opposition_frontbench: bool
    gender: Gender
    node_type: NodeType
    seat_status: SeatStatus
    first_elected: str | None = None
    election_notes: str | None = None
    parliament_terms: list[str] = Field(
        default_factory=list, 
        description="Parliamentary terms served (e.g., ['14th Parliament', '13th Parliament']). Per GR-8."
    )
    portfolios: list[PortfolioTenure] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    special_roles: list[str] = Field(default_factory=list)
    entity_notes: str | None = None

    # -- Computed alias properties (GR-2) -----------------------------------

    @property
    def constituency_aliases(self) -> list[str]:
        """Constituency-based aliases per BC-6."""
        return [
            f"Member for {self.constituency}",
            f"The Member for {self.constituency}",
        ]

    @property
    def portfolio_aliases(self) -> list[str]:
        """Portfolio-based aliases from all tenures (all time)."""
        result: list[str] = []
        for p in self.portfolios:
            result.append(p.short_title)
            result.append(f"The {p.short_title}")
            if p.short_title != p.title:
                result.append(p.title)
        return result

    @property
    def honorific_aliases(self) -> list[str]:
        """Honorific variants per BC-7."""
        return [
            f"Hon. {self.common_name}",
            f"The Honourable {self.common_name}",
        ]

    @property
    def formal_name_aliases(self) -> list[str]:
        """Full legal name as alias."""
        return [self.full_name]

    @property
    def all_aliases(self) -> list[str]:
        """Complete deduplicated alias set: manual + generated."""
        seen: set[str] = set()
        result: list[str] = []
        for alias in (
            self.aliases
            + self.constituency_aliases
            + self.portfolio_aliases
            + self.honorific_aliases
            + self.formal_name_aliases
        ):
            normalized = alias.strip()
            if normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    # -- Temporal alias methods (GR-3) --------------------------------------

    def portfolio_aliases_on(self, query_date: date) -> list[str]:
        """Return only portfolio aliases valid on the given date."""
        result: list[str] = []
        for p in self.portfolios:
            if p.is_active_on(query_date):
                result.append(p.short_title)
                result.append(f"The {p.short_title}")
                if p.short_title != p.title:
                    result.append(p.title)
        return result

    def aliases_on(self, query_date: date) -> list[str]:
        """All aliases valid on a given date (temporal filtering for portfolios)."""
        seen: set[str] = set()
        result: list[str] = []
        for alias in (
            self.aliases
            + self.constituency_aliases
            + self.portfolio_aliases_on(query_date)
            + self.honorific_aliases
            + self.formal_name_aliases
        ):
            normalized = alias.strip()
            if normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result


class DeceasedMP(BaseModel):
    """Record for an MP who died during the parliamentary term."""

    node_id: str
    full_name: str
    common_name: str
    party: Party
    constituency: str
    gender: Gender
    date_of_death: str
    role_at_death: str
    replaced_by: str | None = None
    aliases: list[str] = Field(default_factory=list)
    entity_notes: str | None = None

    @property
    def all_aliases(self) -> list[str]:
        """Complete alias set for deceased MP (manual only)."""
        return list(self.aliases)


class SenateCabinetMember(BaseModel):
    """Cabinet member who sits in the Senate, not the House."""

    name: str
    portfolio: str
    notes: str | None = None


class AliasCollision(BaseModel):
    """Record of an alias shared by multiple MPs."""

    alias: str
    claimants: list[str] = Field(description="List of node_ids sharing this alias")
    resolution_strategy: str


class ParliamentComposition(BaseModel):
    PLP: int
    FNM: int
    COI: int


class GoldenRecordMetadata(BaseModel):
    """Metadata wrapper for the Golden Record."""

    version: str
    parliament: str
    parliament_start: str
    total_seats: int
    composition: ParliamentComposition
    last_updated: str
    compiled_by: str
    source_document: str
    notes: str | None = None


class ConstituencyGeographicIndex(BaseModel):
    new_providence: list[str] = Field(default_factory=list)
    grand_bahama: list[str] = Field(default_factory=list)
    family_islands: list[str] = Field(default_factory=list)


class GoldenRecord(BaseModel):
    """Top-level Golden Record: the complete entity knowledge base."""

    metadata: GoldenRecordMetadata
    mps: list[MPNode]
    deceased_mps: list[DeceasedMP] = Field(default_factory=list)
    senate_cabinet_members: list[SenateCabinetMember] = Field(default_factory=list)
    alias_collisions: list[AliasCollision] = Field(default_factory=list)
    constituency_geographic_index: ConstituencyGeographicIndex | None = None

    # -- Temporal query methods (GR-3) --------------------------------------

    def who_held_portfolio(
        self, short_title: str, query_date: date
    ) -> list[MPNode]:
        """Return all MPs who held the given portfolio on query_date."""
        result: list[MPNode] = []
        for mp in self.mps:
            for p in mp.portfolios:
                if p.short_title == short_title and p.is_active_on(query_date):
                    result.append(mp)
                    break
        return result

    def resolve_alias_candidates(
        self, alias: str, query_date: date | None = None
    ) -> list[MPNode]:
        """Return all MPs for whom the given alias matches (case-insensitive).

        If query_date is provided, only temporally valid aliases are checked.
        The full resolution cascade (fuzzy matching, etc.) is in resolver.py.
        """
        normalized = alias.strip().lower()
        result: list[MPNode] = []
        for mp in self.mps:
            alias_set = mp.aliases_on(query_date) if query_date else mp.all_aliases
            if any(a.lower() == normalized for a in alias_set):
                result.append(mp)
        return result
