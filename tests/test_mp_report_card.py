"""Tests for MP report card component (MP-13).

See SRD §9.2 (MP-13) for specification.
"""

from graphhansard.brain.graph_builder import (
    NodeMetrics,
    SessionGraph,
    EdgeRecord,
    StructuralRole,
)
from graphhansard.dashboard.mp_report_card import (
    MPReportCard,
    build_report_card,
    get_mp_list,
)


def test_mp_report_card_creation():
    """Test MPReportCard initialization."""
    card = MPReportCard("mp_test", "Test MP")
    
    assert card.mp_id == "mp_test"
    assert card.mp_name == "Test MP"
    assert len(card.sessions) == 0
    assert len(card.interaction_partners) == 0
    assert len(card.sentiment_trends) == 0
    assert len(card.role_evolution) == 0


def test_mp_report_card_add_session_data():
    """Test adding session data to report card."""
    card = MPReportCard("mp1", "MP One")
    
    metrics = NodeMetrics(
        node_id="mp1",
        common_name="MP One",
        party="PLP",
        degree_in=5,
        degree_out=3,
        betweenness=0.5,
        eigenvector=0.8,
        closeness=0.7,
        structural_role=[StructuralRole.FORCE_MULTIPLIER.value],
    )
    
    edges = [
        EdgeRecord(
            source_node_id="mp1",
            target_node_id="mp2",
            total_mentions=10,
            positive_count=7,
            neutral_count=2,
            negative_count=1,
            net_sentiment=0.6,
        ),
        EdgeRecord(
            source_node_id="mp3",
            target_node_id="mp1",
            total_mentions=5,
            positive_count=2,
            neutral_count=2,
            negative_count=1,
            net_sentiment=0.2,
        ),
    ]
    
    card.add_session_data(
        session_id="session1",
        date="2024-01-15",
        metrics=metrics,
        edges=edges,
    )
    
    assert len(card.sessions) == 1
    assert card.sessions[0]["session_id"] == "session1"
    assert card.sessions[0]["date"] == "2024-01-15"
    assert card.sessions[0]["degree_in"] == 5
    assert card.sessions[0]["degree_out"] == 3
    assert card.sessions[0]["betweenness"] == 0.5
    assert card.sessions[0]["eigenvector"] == 0.8
    
    # Check interaction partners
    assert "mp2" in card.interaction_partners
    assert card.interaction_partners["mp2"] == 10
    assert "mp3" in card.interaction_partners
    assert card.interaction_partners["mp3"] == 5
    
    # Check sentiment trends
    assert len(card.sentiment_trends) == 1
    # Average of 0.6 and 0.2 = 0.4
    assert abs(card.sentiment_trends[0]["net_sentiment"] - 0.4) < 0.01
    
    # Check role evolution
    assert len(card.role_evolution) == 1
    assert card.role_evolution[0]["date"] == "2024-01-15"
    assert StructuralRole.FORCE_MULTIPLIER.value in card.role_evolution[0]["roles"]


def test_mp_report_card_multiple_sessions():
    """Test adding multiple sessions to report card."""
    card = MPReportCard("mp1", "MP One")
    
    # Add first session
    metrics1 = NodeMetrics(
        node_id="mp1",
        common_name="MP One",
        party="PLP",
        degree_in=5,
        degree_out=3,
        betweenness=0.5,
    )
    edges1 = [
        EdgeRecord(
            source_node_id="mp1",
            target_node_id="mp2",
            total_mentions=10,
            net_sentiment=0.5,
        ),
    ]
    card.add_session_data("session1", "2024-01-15", metrics1, edges1)
    
    # Add second session
    metrics2 = NodeMetrics(
        node_id="mp1",
        common_name="MP One",
        party="PLP",
        degree_in=8,
        degree_out=4,
        betweenness=0.7,
    )
    edges2 = [
        EdgeRecord(
            source_node_id="mp1",
            target_node_id="mp2",
            total_mentions=5,
            net_sentiment=0.3,
        ),
    ]
    card.add_session_data("session2", "2024-01-20", metrics2, edges2)
    
    assert len(card.sessions) == 2
    assert card.sessions[0]["session_id"] == "session1"
    assert card.sessions[1]["session_id"] == "session2"
    
    # Check cumulative interaction partners
    assert card.interaction_partners["mp2"] == 15  # 10 + 5
    
    # Check sentiment trends
    assert len(card.sentiment_trends) == 2


def test_mp_report_card_get_top_partners():
    """Test getting top interaction partners."""
    card = MPReportCard("mp1", "MP One")
    
    card.interaction_partners = {
        "mp2": 50,
        "mp3": 30,
        "mp4": 20,
        "mp5": 10,
        "mp6": 5,
    }
    
    top_partners = card.get_top_partners(top_n=3)
    
    assert len(top_partners) == 3
    assert top_partners[0]["partner_id"] == "mp2"
    assert top_partners[0]["total_mentions"] == 50
    assert top_partners[1]["partner_id"] == "mp3"
    assert top_partners[1]["total_mentions"] == 30
    assert top_partners[2]["partner_id"] == "mp4"
    assert top_partners[2]["total_mentions"] == 20


def test_mp_report_card_get_top_partners_with_registry():
    """Test getting top partners with MP registry."""
    card = MPReportCard("mp1", "MP One")
    
    card.interaction_partners = {
        "mp2": 50,
        "mp3": 30,
    }
    
    mp_registry = {
        "mp2": ("MP Two", "FNM"),
        "mp3": ("MP Three", "PLP"),
    }
    
    top_partners = card.get_top_partners(top_n=2, mp_registry=mp_registry)
    
    assert len(top_partners) == 2
    assert top_partners[0]["name"] == "MP Two"
    assert top_partners[0]["party"] == "FNM"
    assert top_partners[1]["name"] == "MP Three"
    assert top_partners[1]["party"] == "PLP"


def test_build_report_card():
    """Test building report card from session graphs."""
    session_graph1 = SessionGraph(
        session_id="session1",
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
            ),
            NodeMetrics(
                node_id="mp2",
                common_name="MP Two",
                party="FNM",
                degree_in=3,
                degree_out=5,
            ),
        ],
        edges=[
            EdgeRecord(
                source_node_id="mp1",
                target_node_id="mp2",
                total_mentions=10,
                net_sentiment=0.5,
            ),
        ],
    )
    
    session_graphs = [session_graph1]
    
    card = build_report_card("mp1", session_graphs)
    
    assert card is not None
    assert card.mp_id == "mp1"
    assert card.mp_name == "MP One"
    assert len(card.sessions) == 1


def test_build_report_card_mp_not_found():
    """Test building report card for non-existent MP."""
    session_graph = SessionGraph(
        session_id="session1",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=1,
        edge_count=0,
        nodes=[
            NodeMetrics(
                node_id="mp1",
                common_name="MP One",
                party="PLP",
            ),
        ],
        edges=[],
    )
    
    card = build_report_card("mp_nonexistent", [session_graph])
    
    assert card is None


def test_build_report_card_empty_sessions():
    """Test building report card with no sessions."""
    card = build_report_card("mp1", [])
    
    assert card is None


def test_get_mp_list():
    """Test getting list of all MPs from sessions."""
    session_graph = SessionGraph(
        session_id="session1",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=3,
        edge_count=0,
        nodes=[
            NodeMetrics(
                node_id="mp1",
                common_name="Alice",
                party="PLP",
            ),
            NodeMetrics(
                node_id="mp2",
                common_name="Charlie",
                party="FNM",
            ),
            NodeMetrics(
                node_id="mp3",
                common_name="Bob",
                party="PLP",
            ),
        ],
        edges=[],
    )
    
    mps = get_mp_list([session_graph])
    
    assert len(mps) == 3
    # Should be sorted by common_name
    assert mps[0]["common_name"] == "Alice"
    assert mps[1]["common_name"] == "Bob"
    assert mps[2]["common_name"] == "Charlie"


def test_get_mp_list_deduplication():
    """Test that MPs are deduplicated across sessions."""
    session_graph1 = SessionGraph(
        session_id="session1",
        date="2024-01-15",
        graph_file="test.graphml",
        node_count=2,
        edge_count=0,
        nodes=[
            NodeMetrics(node_id="mp1", common_name="MP One", party="PLP"),
            NodeMetrics(node_id="mp2", common_name="MP Two", party="FNM"),
        ],
        edges=[],
    )
    
    session_graph2 = SessionGraph(
        session_id="session2",
        date="2024-01-20",
        graph_file="test2.graphml",
        node_count=2,
        edge_count=0,
        nodes=[
            NodeMetrics(node_id="mp1", common_name="MP One", party="PLP"),
            NodeMetrics(node_id="mp3", common_name="MP Three", party="COI"),
        ],
        edges=[],
    )
    
    mps = get_mp_list([session_graph1, session_graph2])
    
    # Should have 3 unique MPs (mp1, mp2, mp3)
    assert len(mps) == 3
    assert all(mp["node_id"] in ["mp1", "mp2", "mp3"] for mp in mps)
