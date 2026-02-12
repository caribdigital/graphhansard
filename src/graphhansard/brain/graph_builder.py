"""Stage 4 — Graph construction and centrality metric computation.

Builds directed, weighted interaction graphs from mention data and computes
network centrality metrics. See SRD §8.5 (BR-21 through BR-28).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class StructuralRole(str, Enum):
    FORCE_MULTIPLIER = "force_multiplier"
    BRIDGE = "bridge"
    HUB = "hub"
    ISOLATED = "isolated"


class EdgeSemanticType(str, Enum):
    """Edge semantic categories per BC-4 and GR-7.

    Speaker-related edge semantics (procedural,
    excluded from political graph by default):
    - RECOGNIZING: Speaker recognizes an MP to speak
    - ADMONISHING: Speaker warns or rebukes an MP
    - CUTTING_OFF: Speaker interrupts or cuts off an MP
    - RULING: Speaker makes a ruling on a point of order

    Standard political interaction (included in political graph):
    - MENTION: Standard reference between MPs
    """
    RECOGNIZING = "recognizing"
    ADMONISHING = "admonishing"
    CUTTING_OFF = "cutting_off"
    RULING = "ruling"
    MENTION = "mention"


class NodeMetrics(BaseModel):
    """Centrality metrics and structural role for a single MP node."""

    node_id: str
    common_name: str
    party: str
    degree_in: int = 0
    degree_out: int = 0
    betweenness: float = 0.0
    eigenvector: float = 0.0
    closeness: float = 0.0
    structural_role: list[str] = Field(default_factory=list)
    community_id: int | None = None


class EdgeRecord(BaseModel):
    """Aggregated mention interaction between two MPs.

    Per GR-7: Edges involving the Speaker (node_type: control) are
    tagged as procedural and excluded from the political interaction
    graph by default.
    """

    source_node_id: str
    target_node_id: str
    total_mentions: int = 0
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    net_sentiment: float = Field(
        default=0.0, description="(positive - negative) / total"
    )
    semantic_type: EdgeSemanticType = Field(
        default=EdgeSemanticType.MENTION,
        description="Edge semantic category per BC-4"
    )
    is_procedural: bool = Field(
        default=False,
        description=(
            "True if edge involves Speaker control node (GR-7); "
            "excluded from political graph by default"
        )
    )


class SessionGraph(BaseModel):
    """Complete graph data for a single parliamentary session.

    Per GR-7: Use political_edges() to get edges with Speaker
    interactions excluded.
    """

    session_id: str
    date: str
    graph_file: str = Field(description="Path to GraphML file")
    node_count: int = 0
    edge_count: int = 0
    nodes: list[NodeMetrics] = Field(default_factory=list)
    edges: list[EdgeRecord] = Field(default_factory=list)

    def political_edges(self) -> list[EdgeRecord]:
        """Return only non-procedural edges (Speaker excluded).

        Per GR-7: References to/from the Speaker are tagged as
        procedural and excluded from the political graph by default.
        """
        return [edge for edge in self.edges if not edge.is_procedural]

    def procedural_edges(self) -> list[EdgeRecord]:
        """Return only procedural edges (Speaker interactions).

        Per GR-7: For dashboard toggle or analysis of parliamentary
        procedure.
        """
        return [edge for edge in self.edges if edge.is_procedural]


class GraphBuilder:
    """Constructs interaction graphs and computes centrality metrics.

    See SRD §8.5 for specification. Uses NetworkX 3.x.
    """

    def __init__(self):
        raise NotImplementedError("GraphBuilder not yet implemented — see Issue #13")

    def build_session_graph(self, mentions: list[dict]) -> SessionGraph:
        """Build a directed weighted graph from mention records."""
        raise NotImplementedError

    def compute_centrality(self, graph: object) -> list[NodeMetrics]:
        """Compute degree, betweenness, eigenvector, closeness centrality."""
        raise NotImplementedError

    def detect_communities(self, graph: object) -> dict[str, int]:
        """Run Louvain community detection. Returns node_id → community_id."""
        raise NotImplementedError

    def export_graphml(self, graph: object, output_path: str) -> None:
        """Export graph in GraphML format."""
        raise NotImplementedError

    def export_gexf(self, graph: object, output_path: str) -> None:
        """Export graph in GEXF format."""
        raise NotImplementedError

    def export_json(self, session_graph: SessionGraph, output_path: str) -> None:
        """Export graph in JSON node-link format."""
        raise NotImplementedError

    def export_csv(self, session_graph: SessionGraph, output_path: str) -> None:
        """Export edge list as CSV."""
        raise NotImplementedError
