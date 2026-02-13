"""Tests for dashboard filters and search.

Covers: MP-7, MP-8, MP-9 requirements.
"""

import json
import pytest
from pathlib import Path

from graphhansard.brain.graph_builder import SessionGraph, NodeMetrics, EdgeRecord
from graphhansard.dashboard.app import filter_graph_by_party, search_mp


@pytest.fixture
def sample_session_graph():
    """Create a sample SessionGraph for testing."""
    nodes = [
        NodeMetrics(
            node_id="mp_davis_brave",
            common_name="Brave Davis",
            party="PLP",
            degree_in=2,
            degree_out=2,
            betweenness=1.0,
            eigenvector=0.707,
            closeness=1.0,
            structural_role=["force_multiplier", "bridge", "hub"],
        ),
        NodeMetrics(
            node_id="mp_cooper_chester",
            common_name="Chester Cooper",
            party="PLP",
            degree_in=1,
            degree_out=1,
            betweenness=0.0,
            eigenvector=0.5,
            closeness=0.5,
            structural_role=[],
        ),
        NodeMetrics(
            node_id="mp_pintard_michael",
            common_name="Michael Pintard",
            party="FNM",
            degree_in=1,
            degree_out=1,
            betweenness=0.0,
            eigenvector=0.5,
            closeness=0.5,
            structural_role=[],
        ),
        NodeMetrics(
            node_id="mp_gray_khaalis",
            common_name="Khaalis Gray",
            party="COI",
            degree_in=0,
            degree_out=0,
            betweenness=0.0,
            eigenvector=0.0,
            closeness=0.0,
            structural_role=["isolated"],
        ),
    ]
    
    edges = [
        EdgeRecord(
            source_node_id="mp_davis_brave",
            target_node_id="mp_cooper_chester",
            total_mentions=5,
            positive_count=4,
            neutral_count=1,
            negative_count=0,
            net_sentiment=0.8,
        ),
        EdgeRecord(
            source_node_id="mp_davis_brave",
            target_node_id="mp_pintard_michael",
            total_mentions=3,
            positive_count=1,
            neutral_count=2,
            negative_count=0,
            net_sentiment=0.0,
        ),
        EdgeRecord(
            source_node_id="mp_pintard_michael",
            target_node_id="mp_davis_brave",
            total_mentions=2,
            positive_count=0,
            neutral_count=0,
            negative_count=2,
            net_sentiment=-1.0,
        ),
        EdgeRecord(
            source_node_id="mp_cooper_chester",
            target_node_id="mp_davis_brave",
            total_mentions=1,
            positive_count=1,
            neutral_count=0,
            negative_count=0,
            net_sentiment=1.0,
        ),
    ]
    
    return SessionGraph(
        session_id="test_session",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=4,
        edge_count=4,
        nodes=nodes,
        edges=edges,
    )


@pytest.fixture
def golden_record():
    """Create sample Golden Record data for testing."""
    return {
        "mps": [
            {
                "node_id": "mp_davis_brave",
                "common_name": "Brave Davis",
                "full_name": "Philip Edward Davis, K.C.",
                "party": "PLP",
                "constituency": "Cat Island, Rum Cay and San Salvador",
                "aliases": ["Brave", "Papa", "Philip Davis"],
            },
            {
                "node_id": "mp_cooper_chester",
                "common_name": "Chester Cooper",
                "full_name": "Isaac Chester Cooper",
                "party": "PLP",
                "constituency": "Exumas and Ragged Island",
                "aliases": ["Chester"],
            },
            {
                "node_id": "mp_pintard_michael",
                "common_name": "Michael Pintard",
                "full_name": "Michael Pintard",
                "party": "FNM",
                "constituency": "Marco City",
                "aliases": ["Pintard"],
            },
            {
                "node_id": "mp_gray_khaalis",
                "common_name": "Khaalis Gray",
                "full_name": "Khaalis Rolle-Gray",
                "party": "COI",
                "constituency": "MICAL",
                "aliases": ["Gray", "Rolle-Gray"],
            },
        ]
    }


class TestPartyFilter:
    """Test MP-8: Party filter functionality."""
    
    def test_filter_single_party(self, sample_session_graph):
        """Filter to show only one party."""
        filtered = filter_graph_by_party(
            sample_session_graph,
            selected_parties=["PLP"],
            cross_party_only=False
        )
        
        # Should only have PLP nodes
        assert filtered.node_count == 2
        assert all(n.party == "PLP" for n in filtered.nodes)
        
        # Should only have edges between PLP MPs
        assert filtered.edge_count == 2
        for edge in filtered.edges:
            source_party = next(n.party for n in filtered.nodes if n.node_id == edge.source_node_id)
            target_party = next(n.party for n in filtered.nodes if n.node_id == edge.target_node_id)
            assert source_party == "PLP"
            assert target_party == "PLP"
    
    def test_filter_multiple_parties(self, sample_session_graph):
        """Filter to show multiple parties."""
        filtered = filter_graph_by_party(
            sample_session_graph,
            selected_parties=["PLP", "FNM"],
            cross_party_only=False
        )
        
        # Should have PLP and FNM nodes only
        assert filtered.node_count == 3
        parties = {n.party for n in filtered.nodes}
        assert parties == {"PLP", "FNM"}
    
    def test_filter_all_parties(self, sample_session_graph):
        """Filtering to all parties should return full graph."""
        filtered = filter_graph_by_party(
            sample_session_graph,
            selected_parties=["PLP", "FNM", "COI"],
            cross_party_only=False
        )
        
        # Should have all nodes and edges
        assert filtered.node_count == sample_session_graph.node_count
        assert filtered.edge_count == sample_session_graph.edge_count
    
    def test_cross_party_only(self, sample_session_graph):
        """Cross-party only filter should exclude same-party edges."""
        filtered = filter_graph_by_party(
            sample_session_graph,
            selected_parties=["PLP", "FNM", "COI"],
            cross_party_only=True
        )
        
        # Should still have all nodes
        assert filtered.node_count == sample_session_graph.node_count
        
        # Should only have cross-party edges (PLP ↔ FNM)
        # In our sample: davis<->pintard are cross-party, davis<->cooper are same-party
        assert filtered.edge_count == 2
        
        for edge in filtered.edges:
            source_party = next(n.party for n in filtered.nodes if n.node_id == edge.source_node_id)
            target_party = next(n.party for n in filtered.nodes if n.node_id == edge.target_node_id)
            assert source_party != target_party
    
    def test_cross_party_with_single_party_selected(self, sample_session_graph):
        """Cross-party filter with single party should return empty."""
        filtered = filter_graph_by_party(
            sample_session_graph,
            selected_parties=["PLP"],
            cross_party_only=True
        )
        
        # Should have PLP nodes but no edges (no cross-party within single party)
        assert filtered.node_count == 2
        assert filtered.edge_count == 0


class TestSearchMP:
    """Test MP-9: Search functionality."""
    
    def test_search_by_common_name(self, golden_record, sample_session_graph):
        """Search should match common names."""
        matches = search_mp("Brave Davis", golden_record, sample_session_graph)
        
        assert len(matches) == 1
        assert "mp_davis_brave" in matches
    
    def test_search_by_alias(self, golden_record, sample_session_graph):
        """Search should match aliases."""
        matches = search_mp("Papa", golden_record, sample_session_graph)
        
        assert len(matches) == 1
        assert "mp_davis_brave" in matches
    
    def test_search_by_constituency(self, golden_record, sample_session_graph):
        """Search should match constituencies."""
        matches = search_mp("Exumas", golden_record, sample_session_graph)
        
        assert len(matches) == 1
        assert "mp_cooper_chester" in matches
    
    def test_search_fuzzy_matching(self, golden_record, sample_session_graph):
        """Search should use fuzzy matching."""
        # Typo in "Brave"
        matches = search_mp("Brav", golden_record, sample_session_graph)
        
        assert len(matches) >= 1
        assert "mp_davis_brave" in matches
    
    def test_search_case_insensitive(self, golden_record, sample_session_graph):
        """Search should be case-insensitive."""
        matches = search_mp("brave", golden_record, sample_session_graph)
        
        assert len(matches) == 1
        assert "mp_davis_brave" in matches
    
    def test_search_partial_name(self, golden_record, sample_session_graph):
        """Search should work with partial names."""
        matches = search_mp("Cooper", golden_record, sample_session_graph)
        
        assert len(matches) == 1
        assert "mp_cooper_chester" in matches
    
    def test_search_no_matches(self, golden_record, sample_session_graph):
        """Search with no matches should return empty list."""
        matches = search_mp("NonExistentMP", golden_record, sample_session_graph)
        
        assert len(matches) == 0
    
    def test_search_empty_query(self, golden_record, sample_session_graph):
        """Empty query should return empty list."""
        matches = search_mp("", golden_record, sample_session_graph)
        
        assert len(matches) == 0
    
    def test_search_only_in_current_graph(self, golden_record):
        """Search should only return MPs in the current graph."""
        # Create graph with only one MP
        limited_graph = SessionGraph(
            session_id="limited",
            date="2024-01-15",
            graph_file="test.graphml",
            node_count=1,
            edge_count=0,
            nodes=[
                NodeMetrics(
                    node_id="mp_davis_brave",
                    common_name="Brave Davis",
                    party="PLP",
                    degree_in=0,
                    degree_out=0,
                )
            ],
            edges=[],
        )
        
        # Search for Cooper who is not in this graph
        matches = search_mp("Cooper", golden_record, limited_graph)
        
        assert len(matches) == 0
    
    def test_search_handles_multiple_matches(self, golden_record, sample_session_graph):
        """Search that matches multiple MPs should return all."""
        # Add more detail to golden record for this test
        # This would match both if we searched for a common term
        # For now, just verify the mechanism works
        matches = search_mp("Gray", golden_record, sample_session_graph)
        
        assert len(matches) >= 1
        assert "mp_gray_khaalis" in matches
