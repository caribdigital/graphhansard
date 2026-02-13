"""Tests for Layer 3 — The Map (Dashboard).

Covers: Streamlit dashboard, graph visualization, filters.
See Issues #15 through #19.
"""

import json
from pathlib import Path

import pytest

from graphhansard.brain.graph_builder import SessionGraph
from graphhansard.dashboard.app import load_sample_graph
from graphhansard.dashboard.graph_viz import build_force_directed_graph


class TestDashboardDataLoading:
    """Test dashboard data loading functionality."""
    
    def test_load_sample_graph_when_exists(self, tmp_path, monkeypatch):
        """Should load sample graph if file exists."""
        # Create a sample graph file
        sample_data = {
            "session_id": "test_session",
            "date": "2024-01-15",
            "graph_file": "test.graphml",
            "node_count": 2,
            "edge_count": 1,
            "nodes": [
                {
                    "node_id": "mp_test1",
                    "common_name": "Test MP 1",
                    "party": "PLP",
                    "degree_in": 1,
                    "degree_out": 0,
                    "betweenness": 0.0,
                    "eigenvector": 0.5,
                    "closeness": 0.5,
                    "structural_role": [],
                },
                {
                    "node_id": "mp_test2",
                    "common_name": "Test MP 2",
                    "party": "FNM",
                    "degree_in": 0,
                    "degree_out": 1,
                    "betweenness": 0.0,
                    "eigenvector": 0.5,
                    "closeness": 0.5,
                    "structural_role": [],
                },
            ],
            "edges": [
                {
                    "source_node_id": "mp_test2",
                    "target_node_id": "mp_test1",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "net_sentiment": 1.0,
                }
            ],
        }
        
        # Create the output directory and file
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        sample_file = output_dir / "sample_session_metrics.json"
        with open(sample_file, "w") as f:
            json.dump(sample_data, f)
        
        # Monkeypatch Path to point to our tmp_path
        monkeypatch.setattr("graphhansard.dashboard.app.Path", lambda p: tmp_path / p)
        
        # Load the graph
        graph = load_sample_graph()
        
        assert graph is not None
        assert isinstance(graph, SessionGraph)
        assert graph.session_id == "test_session"
        assert graph.node_count == 2
        assert graph.edge_count == 1
    
    def test_load_sample_graph_when_missing(self, tmp_path, monkeypatch):
        """Should return None if sample graph file doesn't exist."""
        # Monkeypatch Path to point to a directory without the sample file
        monkeypatch.setattr("graphhansard.dashboard.app.Path", lambda p: tmp_path / p)
        
        graph = load_sample_graph()
        assert graph is None


class TestDashboardIntegration:
    """Test integration between dashboard and visualization."""
    
    def test_can_build_graph_from_loaded_data(self):
        """Dashboard should be able to build graphs from loaded SessionGraph."""
        # Check if sample data exists
        sample_path = Path("output/sample_session_metrics.json")
        if not sample_path.exists():
            pytest.skip("Sample graph data not available")
        
        # Load sample graph
        with open(sample_path, "r") as f:
            data = json.load(f)
            session_graph = SessionGraph(**data)
        
        # Build visualization
        net = build_force_directed_graph(session_graph)
        
        # Verify graph was built
        assert net is not None
        assert len(net.nodes) == session_graph.node_count
        assert len(net.edges) == session_graph.edge_count
    
    def test_all_metrics_work(self):
        """All metric options should work for node sizing."""
        sample_path = Path("output/sample_session_metrics.json")
        if not sample_path.exists():
            pytest.skip("Sample graph data not available")
        
        with open(sample_path, "r") as f:
            data = json.load(f)
            session_graph = SessionGraph(**data)
        
        # Test each metric option
        metrics = ["degree", "betweenness", "eigenvector", "total_mentions"]
        for metric in metrics:
            net = build_force_directed_graph(session_graph, metric=metric)
            assert len(net.nodes) == session_graph.node_count, f"Failed for metric: {metric}"

