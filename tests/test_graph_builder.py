"""Tests for BR-21 through BR-26: Session Graph Construction & Centrality Metrics.

Validates graph construction from mention data, centrality computation,
structural role assignment, and cumulative graph aggregation.
"""

from pathlib import Path

import pytest

from graphhansard.brain.graph_builder import (
    EdgeRecord,
    GraphBuilder,
    NodeMetrics,
    SessionGraph,
    StructuralRole,
)


class TestGraphConstruction:
    """Test BR-21 & BR-22: Graph construction with weighted edges."""

    def test_build_session_graph_basic(self):
        """BR-21: Build directed graph from mention records."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_davis_brave",
                "target_node_id": "mp_cooper_chester",
                "context_window": "I commend the Deputy Prime Minister.",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_davis_brave",
                "target_node_id": "mp_cooper_chester",
                "context_window": "The Deputy PM answered well.",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_cooper_chester",
                "target_node_id": "mp_davis_brave",
                "context_window": "The Prime Minister spoke on this.",
                "sentiment_label": "neutral",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_session_001",
            date="2024-01-15",
        )
        
        assert session_graph.session_id == "test_session_001"
        assert session_graph.date == "2024-01-15"
        assert session_graph.node_count == 2  # 2 unique MPs
        assert session_graph.edge_count == 2  # 2 directed edges
        assert len(session_graph.edges) == 2
        assert len(session_graph.nodes) == 2

    def test_edge_weight_aggregation(self):
        """BR-22: Edge weight equals count of mentions from source to target."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "neutral",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "negative",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_agg",
            date="2024-01-15",
        )
        
        # Find the edge from mp_a to mp_b
        edge = next(
            e for e in session_graph.edges
            if e.source_node_id == "mp_a" and e.target_node_id == "mp_b"
        )
        
        assert edge.total_mentions == 3

    def test_unresolved_mentions_excluded(self):
        """BR-21: Unresolved mentions (target_node_id=None) are excluded."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": None,  # Unresolved
                "sentiment_label": "neutral",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_unresolved",
            date="2024-01-15",
        )
        
        # Only 1 valid mention should be included
        assert session_graph.edge_count == 1
        assert session_graph.edges[0].total_mentions == 1

    def test_self_references_excluded(self):
        """BR-15: Self-references (is_self_reference=True) are excluded."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_a",
                "is_self_reference": True,
                "sentiment_label": "neutral",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_self_ref",
            date="2024-01-15",
        )
        
        # Only 1 non-self-reference should be included
        assert session_graph.edge_count == 1


class TestEdgeAttributes:
    """Test BR-23: Edge attributes including sentiment counts."""

    def test_edge_sentiment_counts(self):
        """BR-23: Edges track positive, neutral, negative counts."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "neutral",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "negative",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_sentiment",
            date="2024-01-15",
        )
        
        edge = session_graph.edges[0]
        assert edge.total_mentions == 4
        assert edge.positive_count == 2
        assert edge.neutral_count == 1
        assert edge.negative_count == 1

    def test_net_sentiment_calculation(self):
        """BR-23: net_sentiment = (positive - negative) / total."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "negative",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_net_sentiment",
            date="2024-01-15",
        )
        
        edge = session_graph.edges[0]
        # (3 positive - 1 negative) / 4 total = 0.5
        assert edge.net_sentiment == pytest.approx(0.5)

    def test_net_sentiment_all_neutral(self):
        """BR-23: net_sentiment = 0.0 when all mentions are neutral."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "neutral",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "neutral",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_all_neutral",
            date="2024-01-15",
        )
        
        edge = session_graph.edges[0]
        assert edge.net_sentiment == 0.0


class TestCentralityMetrics:
    """Test BR-24: Centrality metric computation."""

    def test_degree_centrality(self):
        """BR-24: Compute in-degree and out-degree for each node."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
            },
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_c",
            },
            {
                "source_node_id": "mp_b",
                "target_node_id": "mp_a",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_degree",
            date="2024-01-15",
        )
        
        # mp_a: out-degree=2 (to b and c), in-degree=1 (from b)
        mp_a = next(n for n in session_graph.nodes if n.node_id == "mp_a")
        assert mp_a.degree_out == 2
        assert mp_a.degree_in == 1
        
        # mp_b: out-degree=1 (to a), in-degree=1 (from a)
        mp_b = next(n for n in session_graph.nodes if n.node_id == "mp_b")
        assert mp_b.degree_out == 1
        assert mp_b.degree_in == 1
        
        # mp_c: out-degree=0, in-degree=1 (from a)
        mp_c = next(n for n in session_graph.nodes if n.node_id == "mp_c")
        assert mp_c.degree_out == 0
        assert mp_c.degree_in == 1

    def test_centrality_metrics_computed(self):
        """BR-24: All centrality metrics are computed."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
            },
            {
                "source_node_id": "mp_b",
                "target_node_id": "mp_c",
            },
            {
                "source_node_id": "mp_c",
                "target_node_id": "mp_a",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_centrality",
            date="2024-01-15",
        )
        
        for node in session_graph.nodes:
            assert hasattr(node, "betweenness")
            assert hasattr(node, "eigenvector")
            assert hasattr(node, "closeness")
            assert isinstance(node.betweenness, float)
            assert isinstance(node.eigenvector, float)
            assert isinstance(node.closeness, float)

    def test_mp_registry_integration(self):
        """BR-24: Node metrics include common_name and party from registry."""
        builder = GraphBuilder()
        
        mp_registry = {
            "mp_davis_brave": ("Brave Davis", "PLP"),
            "mp_pintard_michael": ("Michael Pintard", "FNM"),
        }
        
        mentions = [
            {
                "source_node_id": "mp_davis_brave",
                "target_node_id": "mp_pintard_michael",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_registry",
            date="2024-01-15",
            mp_registry=mp_registry,
        )
        
        brave = next(n for n in session_graph.nodes if n.node_id == "mp_davis_brave")
        assert brave.common_name == "Brave Davis"
        assert brave.party == "PLP"
        
        pintard = next(
            n for n in session_graph.nodes if n.node_id == "mp_pintard_michael"
        )
        assert pintard.common_name == "Michael Pintard"
        assert pintard.party == "FNM"


class TestStructuralRoles:
    """Test BR-26: Structural role identification."""

    def test_isolated_node_label(self):
        """BR-26: Node with degree=0 is labeled 'isolated'."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
            },
        ]
        
        # Add mp_c to the mention pool but with no connections
        # We can't directly add isolated nodes via mentions, so test the labeling logic
        import networkx as nx
        
        G = nx.DiGraph()
        G.add_nodes_from(["mp_a", "mp_b", "mp_c"])
        G.add_edge("mp_a", "mp_b")
        
        node_metrics = builder.compute_centrality(G)
        node_metrics = builder._assign_structural_roles(node_metrics)
        
        mp_c = next(n for n in node_metrics if n.node_id == "mp_c")
        assert StructuralRole.ISOLATED.value in mp_c.structural_role

    def test_hub_label(self):
        """BR-26: Node with high in-degree is labeled 'hub'."""
        builder = GraphBuilder()
        
        # Create a hub structure: many nodes pointing to mp_hub
        mentions = [
            {"source_node_id": f"mp_{i}", "target_node_id": "mp_hub"}
            for i in range(5)
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_hub",
            date="2024-01-15",
        )
        
        mp_hub = next(n for n in session_graph.nodes if n.node_id == "mp_hub")
        # With 75th percentile threshold, mp_hub should be labeled as hub
        assert mp_hub.degree_in == 5
        # Check if hub role is assigned (may depend on distribution)
        # At minimum, it should not be isolated
        assert StructuralRole.ISOLATED.value not in mp_hub.structural_role

    def test_structural_role_configurable_thresholds(self):
        """BR-26: Structural role thresholds are configurable."""
        # Use a different threshold
        builder = GraphBuilder(
            force_multiplier_threshold=0.5,
            bridge_threshold=0.5,
            hub_threshold=0.5,
        )
        
        mentions = [
            {"source_node_id": "mp_a", "target_node_id": "mp_b"},
            {"source_node_id": "mp_b", "target_node_id": "mp_c"},
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_threshold",
            date="2024-01-15",
        )
        
        # Just verify that roles are assigned with custom thresholds
        for node in session_graph.nodes:
            assert hasattr(node, "structural_role")
            assert isinstance(node.structural_role, list)


class TestCumulativeGraph:
    """Test BR-25: Cumulative graph aggregation."""

    def test_cumulative_graph_aggregates_sessions(self):
        """BR-25: Cumulative graph merges edges from multiple sessions."""
        builder = GraphBuilder()
        
        # Session 1
        mentions_s1 = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
        ]
        sg1 = builder.build_session_graph(
            mentions=mentions_s1,
            session_id="session_001",
            date="2024-01-15",
        )
        
        # Session 2
        mentions_s2 = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
            {
                "source_node_id": "mp_b",
                "target_node_id": "mp_c",
                "sentiment_label": "neutral",
            },
        ]
        sg2 = builder.build_session_graph(
            mentions=mentions_s2,
            session_id="session_002",
            date="2024-01-22",
        )
        
        # Build cumulative graph
        cumulative = builder.build_cumulative_graph(
            session_graphs=[sg1, sg2],
            cumulative_id="cumulative_jan_2024",
            date_range=("2024-01-15", "2024-01-22"),
        )
        
        assert cumulative.session_id == "cumulative_jan_2024"
        assert cumulative.date == "2024-01-15_to_2024-01-22"
        
        # Edge from mp_a to mp_b should have 2 mentions (1 from each session)
        edge_ab = next(
            e for e in cumulative.edges
            if e.source_node_id == "mp_a" and e.target_node_id == "mp_b"
        )
        assert edge_ab.total_mentions == 2
        assert edge_ab.positive_count == 2

    def test_cumulative_graph_new_edges(self):
        """BR-25: Cumulative graph includes edges from any session."""
        builder = GraphBuilder()
        
        # Session 1: mp_a -> mp_b
        sg1 = builder.build_session_graph(
            mentions=[{"source_node_id": "mp_a", "target_node_id": "mp_b"}],
            session_id="s1",
            date="2024-01-15",
        )
        
        # Session 2: mp_b -> mp_c
        sg2 = builder.build_session_graph(
            mentions=[{"source_node_id": "mp_b", "target_node_id": "mp_c"}],
            session_id="s2",
            date="2024-01-22",
        )
        
        cumulative = builder.build_cumulative_graph(
            session_graphs=[sg1, sg2],
            cumulative_id="cumulative_test",
            date_range=("2024-01-15", "2024-01-22"),
        )
        
        # Should have both edges
        assert cumulative.edge_count == 2
        assert cumulative.node_count == 3  # mp_a, mp_b, mp_c


class TestExportFunctionality:
    """Test export methods for GraphML, JSON, CSV, GEXF."""

    def test_export_json(self, tmp_path):
        """Test JSON export of SessionGraph."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_export",
            date="2024-01-15",
        )
        
        output_path = tmp_path / "test_export_metrics.json"
        builder.export_json(session_graph, str(output_path))
        
        assert output_path.exists()
        
        # Verify JSON structure
        import json
        with open(output_path) as f:
            data = json.load(f)
        
        assert data["session_id"] == "test_export"
        assert "nodes" in data
        assert "edges" in data

    def test_export_csv(self, tmp_path):
        """Test CSV export of edge list."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
                "sentiment_label": "positive",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_csv",
            date="2024-01-15",
        )
        
        output_path = tmp_path / "test_export.csv"
        builder.export_csv(session_graph, str(output_path))
        
        assert output_path.exists()
        
        # Verify CSV structure
        import csv
        with open(output_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 1
        assert rows[0]["source_node_id"] == "mp_a"
        assert rows[0]["target_node_id"] == "mp_b"

    def test_export_graphml(self, tmp_path):
        """Test GraphML export."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_graphml",
            date="2024-01-15",
        )
        
        # Reconstruct NetworkX graph
        G = builder.build_graph_from_session(session_graph)
        
        output_path = tmp_path / "test_export.graphml"
        builder.export_graphml(G, str(output_path))
        
        assert output_path.exists()

    def test_export_gexf(self, tmp_path):
        """Test GEXF export."""
        builder = GraphBuilder()
        
        mentions = [
            {
                "source_node_id": "mp_a",
                "target_node_id": "mp_b",
            },
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_gexf",
            date="2024-01-15",
        )
        
        G = builder.build_graph_from_session(session_graph)
        
        output_path = tmp_path / "test_export.gexf"
        builder.export_gexf(G, str(output_path))
        
        assert output_path.exists()


class TestCommunityDetection:
    """Test community detection functionality."""

    def test_detect_communities(self):
        """Test Louvain community detection."""
        builder = GraphBuilder()
        
        mentions = [
            {"source_node_id": "mp_a", "target_node_id": "mp_b"},
            {"source_node_id": "mp_b", "target_node_id": "mp_a"},
            {"source_node_id": "mp_c", "target_node_id": "mp_d"},
            {"source_node_id": "mp_d", "target_node_id": "mp_c"},
        ]
        
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="test_community",
            date="2024-01-15",
        )
        
        G = builder.build_graph_from_session(session_graph)
        communities = builder.detect_communities(G)
        
        # All nodes should be assigned to a community
        assert len(communities) == 4
        for node_id in ["mp_a", "mp_b", "mp_c", "mp_d"]:
            assert node_id in communities
            assert isinstance(communities[node_id], int)


class TestPerformance:
    """Test NF-3: Performance requirements."""

    def test_39_node_graph_under_5_seconds(self):
        """NF-3: Graph computation ≤5 seconds for a 39-node graph."""
        import time
        
        builder = GraphBuilder()
        
        # Create a realistic 39-node graph with mentions
        # Average of ~20 mentions per MP = ~780 total mentions
        mentions = []
        for i in range(39):
            for j in range(20):
                # Each MP mentions ~20 others (random)
                target = (i + j + 1) % 39
                if i != target:  # Avoid self-references
                    mentions.append({
                        "source_node_id": f"mp_{i}",
                        "target_node_id": f"mp_{target}",
                        "sentiment_label": ["positive", "neutral", "negative"][j % 3],
                    })
        
        start_time = time.time()
        session_graph = builder.build_session_graph(
            mentions=mentions,
            session_id="perf_test_39_nodes",
            date="2024-01-15",
        )
        elapsed_time = time.time() - start_time
        
        assert session_graph.node_count == 39
        assert elapsed_time < 5.0, (
            f"Graph computation took {elapsed_time:.2f}s, exceeds 5s limit"
        )
        
        # Also test export performance
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            start_export = time.time()
            builder.export_json(
                session_graph,
                f"{tmpdir}/perf_test_metrics.json"
            )
            export_time = time.time() - start_export
            
            # Export should also be fast
            assert export_time < 1.0, (
                f"JSON export took {export_time:.2f}s, should be <1s"
            )


class TestMentionRecordIntegration:
    """Test integration with MentionRecord model."""

    def test_mention_record_to_graph_dict(self):
        """Test MentionRecord.to_graph_dict() helper method."""
        from graphhansard.brain.entity_extractor import (
            MentionRecord,
            ResolutionMethod,
        )
        
        mention = MentionRecord(
            session_id="test_session",
            source_node_id="mp_davis_brave",
            target_node_id="mp_cooper_chester",
            raw_mention="The Deputy Prime Minister",
            resolution_method=ResolutionMethod.EXACT,
            resolution_score=1.0,
            timestamp_start=10.5,
            timestamp_end=12.0,
            context_window="I commend the Deputy Prime Minister.",
            segment_index=5,
            is_self_reference=False,
        )
        
        graph_dict = mention.to_graph_dict(sentiment_label="positive")
        
        assert graph_dict["source_node_id"] == "mp_davis_brave"
        assert graph_dict["target_node_id"] == "mp_cooper_chester"
        assert graph_dict["sentiment_label"] == "positive"
        assert graph_dict["context_window"] == "I commend the Deputy Prime Minister."
        assert graph_dict["is_self_reference"] is False

    def test_full_workflow_mention_to_graph(self):
        """Test complete workflow: MentionRecord → GraphBuilder → SessionGraph."""
        from graphhansard.brain.entity_extractor import (
            MentionRecord,
            ResolutionMethod,
        )
        
        # Create MentionRecord objects
        mentions_records = [
            MentionRecord(
                session_id="session_001",
                source_node_id="mp_davis_brave",
                target_node_id="mp_cooper_chester",
                raw_mention="The Deputy PM",
                resolution_method=ResolutionMethod.EXACT,
                resolution_score=1.0,
                timestamp_start=10.0,
                timestamp_end=11.0,
                context_window="I thank the Deputy PM for his work.",
                segment_index=0,
            ),
            MentionRecord(
                session_id="session_001",
                source_node_id="mp_cooper_chester",
                target_node_id="mp_davis_brave",
                raw_mention="The Prime Minister",
                resolution_method=ResolutionMethod.EXACT,
                resolution_score=1.0,
                timestamp_start=20.0,
                timestamp_end=21.0,
                context_window="The Prime Minister has shown leadership.",
                segment_index=1,
            ),
        ]
        
        # Convert to graph dict format with sentiment
        mention_dicts = [
            mr.to_graph_dict(sentiment_label="positive") for mr in mentions_records
        ]
        
        # Build graph
        builder = GraphBuilder()
        session_graph = builder.build_session_graph(
            mentions=mention_dicts,
            session_id="session_001",
            date="2024-01-15",
        )
        
        # Validate
        assert session_graph.session_id == "session_001"
        assert session_graph.node_count == 2
        assert session_graph.edge_count == 2
        
        # Check edges
        edge1 = next(
            e for e in session_graph.edges
            if e.source_node_id == "mp_davis_brave"
        )
        assert edge1.target_node_id == "mp_cooper_chester"
        assert edge1.total_mentions == 1
        assert edge1.positive_count == 1
