"""Tests for leaderboard component (MP-10).

See SRD §9.2 (MP-10) for specification.
"""

from graphhansard.brain.graph_builder import NodeMetrics, SessionGraph, StructuralRole
from graphhansard.dashboard.leaderboard import (
    get_top_mps_by_metric,
    get_role_badge,
    get_role_label,
)


def test_get_top_mps_by_metric_degree():
    """Test getting top MPs by degree centrality."""
    session_graph = SessionGraph(
        session_id="test_session",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=3,
        edge_count=2,
        nodes=[
            NodeMetrics(
                node_id="mp1",
                common_name="MP One",
                party="PLP",
                degree_in=5,
                degree_out=3,
            ),
            NodeMetrics(
                node_id="mp2",
                common_name="MP Two",
                party="FNM",
                degree_in=2,
                degree_out=1,
            ),
            NodeMetrics(
                node_id="mp3",
                common_name="MP Three",
                party="PLP",
                degree_in=4,
                degree_out=2,
            ),
        ],
    )
    
    top_mps = get_top_mps_by_metric(session_graph, "degree", top_n=2)
    
    assert len(top_mps) == 2
    assert top_mps[0]["node_id"] == "mp1"
    assert top_mps[0]["value"] == 8  # 5 + 3
    assert top_mps[1]["node_id"] == "mp3"
    assert top_mps[1]["value"] == 6  # 4 + 2


def test_get_top_mps_by_metric_betweenness():
    """Test getting top MPs by betweenness centrality."""
    session_graph = SessionGraph(
        session_id="test_session",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=3,
        edge_count=2,
        nodes=[
            NodeMetrics(
                node_id="mp1",
                common_name="MP One",
                party="PLP",
                betweenness=0.5,
            ),
            NodeMetrics(
                node_id="mp2",
                common_name="MP Two",
                party="FNM",
                betweenness=0.8,
            ),
            NodeMetrics(
                node_id="mp3",
                common_name="MP Three",
                party="PLP",
                betweenness=0.3,
            ),
        ],
    )
    
    top_mps = get_top_mps_by_metric(session_graph, "betweenness", top_n=3)
    
    assert len(top_mps) == 3
    assert top_mps[0]["node_id"] == "mp2"
    assert top_mps[0]["value"] == 0.8
    assert top_mps[1]["node_id"] == "mp1"
    assert top_mps[2]["node_id"] == "mp3"


def test_get_top_mps_by_metric_eigenvector():
    """Test getting top MPs by eigenvector centrality."""
    session_graph = SessionGraph(
        session_id="test_session",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=2,
        edge_count=1,
        nodes=[
            NodeMetrics(
                node_id="mp1",
                common_name="MP One",
                party="PLP",
                eigenvector=0.9,
            ),
            NodeMetrics(
                node_id="mp2",
                common_name="MP Two",
                party="FNM",
                eigenvector=0.4,
            ),
        ],
    )
    
    top_mps = get_top_mps_by_metric(session_graph, "eigenvector", top_n=5)
    
    assert len(top_mps) == 2
    assert top_mps[0]["node_id"] == "mp1"
    assert top_mps[0]["value"] == 0.9


def test_get_top_mps_by_metric_closeness():
    """Test getting top MPs by closeness centrality."""
    session_graph = SessionGraph(
        session_id="test_session",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=2,
        edge_count=1,
        nodes=[
            NodeMetrics(
                node_id="mp1",
                common_name="MP One",
                party="PLP",
                closeness=0.7,
            ),
            NodeMetrics(
                node_id="mp2",
                common_name="MP Two",
                party="FNM",
                closeness=0.6,
            ),
        ],
    )
    
    top_mps = get_top_mps_by_metric(session_graph, "closeness", top_n=2)
    
    assert len(top_mps) == 2
    assert top_mps[0]["value"] == 0.7
    assert top_mps[1]["value"] == 0.6


def test_get_top_mps_empty_graph():
    """Test getting top MPs from empty graph."""
    session_graph = SessionGraph(
        session_id="test_session",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=0,
        edge_count=0,
        nodes=[],
    )
    
    top_mps = get_top_mps_by_metric(session_graph, "degree", top_n=5)
    
    assert len(top_mps) == 0


def test_get_role_badge():
    """Test role badge emoji mapping."""
    assert get_role_badge(StructuralRole.FORCE_MULTIPLIER.value) == "⚡"
    assert get_role_badge(StructuralRole.BRIDGE.value) == "🌉"
    assert get_role_badge(StructuralRole.HUB.value) == "🎯"
    assert get_role_badge(StructuralRole.ISOLATED.value) == "🏝️"
    assert get_role_badge("unknown_role") == ""


def test_get_role_label():
    """Test role label mapping."""
    assert get_role_label(StructuralRole.FORCE_MULTIPLIER.value) == "Force Multiplier"
    assert get_role_label(StructuralRole.BRIDGE.value) == "Bridge"
    assert get_role_label(StructuralRole.HUB.value) == "Hub"
    assert get_role_label(StructuralRole.ISOLATED.value) == "Isolated"


def test_get_top_mps_with_structural_roles():
    """Test that structural roles are included in results."""
    session_graph = SessionGraph(
        session_id="test_session",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=2,
        edge_count=1,
        nodes=[
            NodeMetrics(
                node_id="mp1",
                common_name="MP One",
                party="PLP",
                degree_in=5,
                degree_out=3,
                structural_role=[
                    StructuralRole.FORCE_MULTIPLIER.value,
                    StructuralRole.HUB.value,
                ],
            ),
            NodeMetrics(
                node_id="mp2",
                common_name="MP Two",
                party="FNM",
                degree_in=1,
                degree_out=0,
                structural_role=[StructuralRole.ISOLATED.value],
            ),
        ],
    )
    
    top_mps = get_top_mps_by_metric(session_graph, "degree", top_n=2)
    
    assert len(top_mps) == 2
    assert len(top_mps[0]["structural_role"]) == 2
    assert StructuralRole.FORCE_MULTIPLIER.value in top_mps[0]["structural_role"]
    assert StructuralRole.HUB.value in top_mps[0]["structural_role"]
    assert len(top_mps[1]["structural_role"]) == 1
    assert StructuralRole.ISOLATED.value in top_mps[1]["structural_role"]
