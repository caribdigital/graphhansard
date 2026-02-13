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
    """Edge semantic categories per BC-4, BC-5, and GR-7.

    Speaker-related edge semantics (procedural,
    excluded from political graph by default):
    - RECOGNIZING: Speaker recognizes an MP to speak
    - ADMONISHING: Speaker warns or rebukes an MP
    - CUTTING_OFF: Speaker interrupts or cuts off an MP
    - RULING: Speaker makes a ruling on a point of order
    - PROCEDURAL_CONFLICT: Point of Order raised by MP (BC-5)

    Standard political interaction (included in political graph):
    - MENTION: Standard reference between MPs
    """
    RECOGNIZING = "recognizing"
    ADMONISHING = "admonishing"
    CUTTING_OFF = "cutting_off"
    RULING = "ruling"
    PROCEDURAL_CONFLICT = "procedural_conflict"
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
        description="Edge semantic category per BC-4 and GR-7"
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
    
    Structural role thresholds (configurable):
    - Force Multiplier: eigenvector centrality > 75th percentile
    - Bridge: betweenness centrality > 75th percentile
    - Hub: in-degree > 75th percentile
    - Isolated: total degree == 0
    """

    def __init__(
        self,
        force_multiplier_threshold: float = 0.75,
        bridge_threshold: float = 0.75,
        hub_threshold: float = 0.75,
    ):
        """Initialize GraphBuilder with configurable role thresholds.
        
        Args:
            force_multiplier_threshold: Percentile for eigenvector centrality (0-1)
            bridge_threshold: Percentile for betweenness centrality (0-1)
            hub_threshold: Percentile for in-degree centrality (0-1)
        """
        self.force_multiplier_threshold = force_multiplier_threshold
        self.bridge_threshold = bridge_threshold
        self.hub_threshold = hub_threshold

    def build_session_graph(
        self,
        mentions: list[dict],
        session_id: str,
        date: str,
        mp_registry: dict[str, tuple[str, str]] | None = None,
    ) -> SessionGraph:
        """Build a directed weighted graph from mention records.
        
        Args:
            mentions: List of MentionRecord dicts with keys: source_node_id,
                     target_node_id, raw_mention, context_window, etc.
            session_id: Parliamentary session identifier
            date: Session date (ISO format)
            mp_registry: Optional dict mapping node_id to (common_name, party)
            
        Returns:
            SessionGraph with computed metrics and edges
        """
        import networkx as nx
        
        # Filter out unresolved mentions and self-references
        valid_mentions = [
            m for m in mentions
            if m.get("target_node_id") is not None 
            and not m.get("is_self_reference", False)
        ]
        
        # Aggregate edges by (source, target) pair
        edge_aggregations = {}
        for mention in valid_mentions:
            source = mention["source_node_id"]
            target = mention["target_node_id"]
            key = (source, target)
            
            if key not in edge_aggregations:
                edge_aggregations[key] = {
                    "total_mentions": 0,
                    "positive_count": 0,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "contexts": [],
                }
            
            edge_aggregations[key]["total_mentions"] += 1
            edge_aggregations[key]["contexts"].append(mention.get("context_window", ""))
            
            # If sentiment is provided, aggregate it
            if "sentiment_label" in mention:
                label = mention["sentiment_label"]
                if label == "positive":
                    edge_aggregations[key]["positive_count"] += 1
                elif label == "negative":
                    edge_aggregations[key]["negative_count"] += 1
                else:
                    edge_aggregations[key]["neutral_count"] += 1
        
        # Build NetworkX directed graph
        G = nx.DiGraph()
        
        # Add all nodes (all MPs who were sources or targets)
        all_node_ids = set()
        for source, target in edge_aggregations.keys():
            all_node_ids.add(source)
            all_node_ids.add(target)
        
        for node_id in all_node_ids:
            G.add_node(node_id)
        
        # Add edges with attributes
        edges = []
        for (source, target), agg in edge_aggregations.items():
            total = agg["total_mentions"]
            pos = agg["positive_count"]
            neg = agg["negative_count"]
            neu = agg["neutral_count"]
            
            # Calculate net sentiment (BR-23)
            net_sentiment = self._calculate_net_sentiment(pos, neg, total)
            
            edge_record = EdgeRecord(
                source_node_id=source,
                target_node_id=target,
                total_mentions=total,
                positive_count=pos,
                neutral_count=neu,
                negative_count=neg,
                net_sentiment=net_sentiment,
            )
            edges.append(edge_record)
            
            # Add edge to NetworkX graph with weight
            G.add_edge(
                source,
                target,
                weight=total,
                positive_count=pos,
                neutral_count=neu,
                negative_count=neg,
                net_sentiment=net_sentiment,
            )
        
        # Compute centrality metrics
        node_metrics = self.compute_centrality(G, mp_registry)
        
        # Assign structural roles
        node_metrics = self._assign_structural_roles(node_metrics)
        
        # Build SessionGraph
        graph_file = f"graphs/sessions/{session_id}.graphml"
        session_graph = SessionGraph(
            session_id=session_id,
            date=date,
            graph_file=graph_file,
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
            nodes=node_metrics,
            edges=edges,
        )
        
        return session_graph

    def compute_centrality(
        self,
        graph: "nx.DiGraph",
        mp_registry: dict[str, tuple[str, str]] | None = None,
    ) -> list[NodeMetrics]:
        """Compute degree, betweenness, eigenvector, closeness centrality.
        
        Args:
            graph: NetworkX directed graph
            mp_registry: Optional dict mapping node_id to (common_name, party)
            
        Returns:
            List of NodeMetrics for each node
        """
        import networkx as nx
        
        # Compute centrality metrics (BR-24)
        in_degree = dict(graph.in_degree())
        out_degree = dict(graph.out_degree())
        
        # Betweenness centrality
        try:
            betweenness = nx.betweenness_centrality(graph)
        except (nx.NetworkXError, ZeroDivisionError):
            # Handle disconnected graphs or empty graphs
            betweenness = {node: 0.0 for node in graph.nodes()}
        
        # Eigenvector centrality (may fail for disconnected graphs)
        try:
            eigenvector = nx.eigenvector_centrality(graph, max_iter=1000)
        except (nx.PowerIterationFailedConvergence, nx.NetworkXError):
            # Fallback: use PageRank as alternative for problematic graphs
            try:
                eigenvector = nx.pagerank(graph, max_iter=1000)
            except (nx.NetworkXError, ZeroDivisionError):
                eigenvector = {node: 0.0 for node in graph.nodes()}
        
        # Closeness centrality
        try:
            closeness = nx.closeness_centrality(graph)
        except (nx.NetworkXError, ZeroDivisionError):
            closeness = {node: 0.0 for node in graph.nodes()}
        
        # Build NodeMetrics list
        metrics = []
        for node in graph.nodes():
            # Get MP info from registry if available
            common_name = node
            party = "Unknown"
            if mp_registry and node in mp_registry:
                common_name, party = mp_registry[node]
            
            node_metric = NodeMetrics(
                node_id=node,
                common_name=common_name,
                party=party,
                degree_in=in_degree.get(node, 0),
                degree_out=out_degree.get(node, 0),
                betweenness=betweenness.get(node, 0.0),
                eigenvector=eigenvector.get(node, 0.0),
                closeness=closeness.get(node, 0.0),
            )
            metrics.append(node_metric)
        
        return metrics

    def _calculate_net_sentiment(
        self, positive_count: int, negative_count: int, total_count: int
    ) -> float:
        """Calculate net sentiment score (BR-23).
        
        Args:
            positive_count: Number of positive mentions
            negative_count: Number of negative mentions
            total_count: Total number of mentions
            
        Returns:
            Net sentiment: (positive - negative) / total
        """
        if total_count == 0:
            return 0.0
        return (positive_count - negative_count) / total_count

    def _assign_structural_roles(
        self, node_metrics: list[NodeMetrics]
    ) -> list[NodeMetrics]:
        """Assign structural roles based on centrality thresholds (BR-26).
        
        Args:
            node_metrics: List of NodeMetrics to label
            
        Returns:
            Updated list with structural_role labels assigned
        """
        import numpy as np
        
        # Extract metrics for percentile calculation
        if not node_metrics:
            return node_metrics
        
        eigenvector_values = [nm.eigenvector for nm in node_metrics]
        betweenness_values = [nm.betweenness for nm in node_metrics]
        in_degree_values = [nm.degree_in for nm in node_metrics]
        
        # Calculate thresholds
        eigenvector_threshold = np.percentile(
            eigenvector_values, self.force_multiplier_threshold * 100
        )
        betweenness_threshold = np.percentile(
            betweenness_values, self.bridge_threshold * 100
        )
        in_degree_threshold = np.percentile(
            in_degree_values, self.hub_threshold * 100
        )
        
        # Assign roles
        for nm in node_metrics:
            roles = []
            
            # Isolated: no connections
            if nm.degree_in == 0 and nm.degree_out == 0:
                roles.append(StructuralRole.ISOLATED.value)
            else:
                # Force Multiplier: high eigenvector centrality
                if nm.eigenvector > eigenvector_threshold:
                    roles.append(StructuralRole.FORCE_MULTIPLIER.value)
                
                # Bridge: high betweenness centrality
                if nm.betweenness > betweenness_threshold:
                    roles.append(StructuralRole.BRIDGE.value)
                
                # Hub: high in-degree
                if nm.degree_in > in_degree_threshold:
                    roles.append(StructuralRole.HUB.value)
            
            nm.structural_role = roles
        
        return node_metrics

    def build_cumulative_graph(
        self,
        session_graphs: list[SessionGraph],
        cumulative_id: str,
        date_range: tuple[str, str],
        mp_registry: dict[str, tuple[str, str]] | None = None,
    ) -> SessionGraph:
        """Build cumulative graph aggregating multiple sessions (BR-25).
        
        Args:
            session_graphs: List of SessionGraph objects to aggregate
            cumulative_id: Identifier for the cumulative graph
            date_range: Tuple of (start_date, end_date) in ISO format
            mp_registry: Optional dict mapping node_id to (common_name, party)
            
        Returns:
            Aggregated SessionGraph spanning the date range
        """
        import networkx as nx
        
        # Aggregate all edges across sessions
        edge_aggregations = {}
        
        for sg in session_graphs:
            for edge in sg.edges:
                key = (edge.source_node_id, edge.target_node_id)
                
                if key not in edge_aggregations:
                    edge_aggregations[key] = {
                        "total_mentions": 0,
                        "positive_count": 0,
                        "neutral_count": 0,
                        "negative_count": 0,
                    }
                
                edge_aggregations[key]["total_mentions"] += edge.total_mentions
                edge_aggregations[key]["positive_count"] += edge.positive_count
                edge_aggregations[key]["neutral_count"] += edge.neutral_count
                edge_aggregations[key]["negative_count"] += edge.negative_count
        
        # Build NetworkX graph
        G = nx.DiGraph()
        
        # Add all nodes
        all_node_ids = set()
        for source, target in edge_aggregations.keys():
            all_node_ids.add(source)
            all_node_ids.add(target)
        
        for node_id in all_node_ids:
            G.add_node(node_id)
        
        # Add edges
        edges = []
        for (source, target), agg in edge_aggregations.items():
            total = agg["total_mentions"]
            pos = agg["positive_count"]
            neg = agg["negative_count"]
            neu = agg["neutral_count"]
            
            net_sentiment = self._calculate_net_sentiment(pos, neg, total)
            
            edge_record = EdgeRecord(
                source_node_id=source,
                target_node_id=target,
                total_mentions=total,
                positive_count=pos,
                neutral_count=neu,
                negative_count=neg,
                net_sentiment=net_sentiment,
            )
            edges.append(edge_record)
            
            G.add_edge(
                source,
                target,
                weight=total,
                positive_count=pos,
                neutral_count=neu,
                negative_count=neg,
                net_sentiment=net_sentiment,
            )
        
        # Compute centrality metrics
        node_metrics = self.compute_centrality(G, mp_registry)
        node_metrics = self._assign_structural_roles(node_metrics)
        
        # Build cumulative SessionGraph
        start_date, end_date = date_range
        date_label = f"{start_date}_to_{end_date}"
        graph_file = f"graphs/cumulative/{cumulative_id}.graphml"
        
        cumulative_graph = SessionGraph(
            session_id=cumulative_id,
            date=date_label,
            graph_file=graph_file,
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
            nodes=node_metrics,
            edges=edges,
        )
        
        return cumulative_graph

    def detect_communities(self, graph: "nx.DiGraph") -> dict[str, int]:
        """Run Louvain community detection. Returns node_id → community_id.
        
        Args:
            graph: NetworkX directed graph
            
        Returns:
            Dictionary mapping node_id to community_id
        """
        try:
            import networkx.algorithms.community as nx_comm
            
            # Convert to undirected for community detection
            undirected = graph.to_undirected()
            
            # Run Louvain (greedy modularity)
            communities = nx_comm.louvain_communities(undirected)
            
            # Map node_id to community_id
            node_to_community = {}
            for community_id, community_nodes in enumerate(communities):
                for node in community_nodes:
                    node_to_community[node] = community_id
            
            return node_to_community
        except (ImportError, AttributeError, nx.NetworkXError):
            # Fallback: assign all to community 0 if Louvain not available
            return {node: 0 for node in graph.nodes()}

    def export_graphml(self, graph: "nx.DiGraph", output_path: str) -> None:
        """Export graph in GraphML format.
        
        Args:
            graph: NetworkX directed graph
            output_path: Path to output file
        """
        import networkx as nx
        from pathlib import Path
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        nx.write_graphml(graph, output_path)

    def export_gexf(self, graph: "nx.DiGraph", output_path: str) -> None:
        """Export graph in GEXF format.
        
        Args:
            graph: NetworkX directed graph
            output_path: Path to output file
        """
        import networkx as nx
        from pathlib import Path
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        nx.write_gexf(graph, output_path)

    def export_json(self, session_graph: SessionGraph, output_path: str) -> None:
        """Export graph metrics in JSON format.
        
        Args:
            session_graph: SessionGraph object
            output_path: Path to output JSON file
        """
        import json
        from pathlib import Path
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Export as JSON using Pydantic's model serialization
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                session_graph.model_dump(mode="json"),
                f,
                indent=2,
                ensure_ascii=False,
            )

    def export_csv(self, session_graph: SessionGraph, output_path: str) -> None:
        """Export edge list as CSV.
        
        Args:
            session_graph: SessionGraph object
            output_path: Path to output CSV file
        """
        import csv
        from pathlib import Path
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "source_node_id",
                "target_node_id",
                "total_mentions",
                "positive_count",
                "neutral_count",
                "negative_count",
                "net_sentiment",
            ])
            
            # Write edges
            for edge in session_graph.edges:
                writer.writerow([
                    edge.source_node_id,
                    edge.target_node_id,
                    edge.total_mentions,
                    edge.positive_count,
                    edge.neutral_count,
                    edge.negative_count,
                    edge.net_sentiment,
                ])
    
    def build_graph_from_session(
        self,
        session_graph: SessionGraph,
    ) -> "nx.DiGraph":
        """Reconstruct a NetworkX graph from a SessionGraph object.
        
        Args:
            session_graph: SessionGraph with edges and nodes
            
        Returns:
            NetworkX DiGraph
        """
        import networkx as nx
        
        G = nx.DiGraph()
        
        # Add nodes
        for node_metric in session_graph.nodes:
            G.add_node(node_metric.node_id)
        
        # Add edges
        for edge in session_graph.edges:
            G.add_edge(
                edge.source_node_id,
                edge.target_node_id,
                weight=edge.total_mentions,
                positive_count=edge.positive_count,
                neutral_count=edge.neutral_count,
                negative_count=edge.negative_count,
                net_sentiment=edge.net_sentiment,
            )
        
        return G
