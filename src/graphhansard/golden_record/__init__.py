"""Layer 0 — The Golden Record: Entity Knowledge Base.

Canonical, versioned, machine-readable knowledge base mapping every sitting MP
to the complete set of identities by which they may be referenced in debate.
"""

from .models import GoldenRecord, MPNode, PortfolioTenure
from .resolver import AliasResolver, ResolutionResult

__all__ = [
    "GoldenRecord",
    "MPNode",
    "PortfolioTenure",
    "AliasResolver",
    "ResolutionResult",
]
