"""Pydantic v2 data models for the Golden Record.

Schemas defined per SRD §6.3 and §10.1.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


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


class PortfolioTenure(BaseModel):
    """A single portfolio held by an MP over a specific time period."""

    title: str = Field(description="Full official title")
    short_title: str = Field(description="Commonly used abbreviation")
    start_date: date | str
    end_date: date | str | None = Field(
        default=None, description="null = currently active"
    )


class MPNode(BaseModel):
    """Canonical profile for a single Member of Parliament."""

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
    portfolios: list[PortfolioTenure] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    special_roles: list[str] = Field(default_factory=list)
    entity_notes: str | None = None


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
