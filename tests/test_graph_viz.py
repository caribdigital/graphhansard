"""Tests for force-directed graph visualization.

Covers: MP-1 through MP-6, MP-11 requirements.
"""

import pytest
from pyvis.network import Network

from graphhansard.brain.graph_builder import SessionGraph, NodeMetrics, EdgeRecord, MentionDetail
from graphhansard.dashboard.graph_viz import (
    build_force_directed_graph,
    get_sentiment_color,
    normalize_metric,
    PARTY_COLORS,
    EDGE_COLOR_POSITIVE,
    EDGE_COLOR_NEUTRAL,
    EDGE_COLOR_NEGATIVE,
)


@pytest.fixture
def sample_session_graph():
    """Create a sample SessionGraph for testing."""
    nodes = [
        NodeMetrics(
            node_id="mp_davis_brave",
            common_name="Brave Davis",
            party="PLP",
            constituency="Cat Island, Rum Cay and San Salvador",
            current_portfolio="Prime Minister",
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
            constituency="Exuma and Ragged Island",
            current_portfolio="Deputy Prime Minister",
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
            constituency="Marco City",
            current_portfolio="Leader of the Opposition",
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
            constituency="MICAL",
            current_portfolio=None,
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
            net_sentiment=0.8,  # Positive
            mention_details=[
                MentionDetail(
                    timestamp_start=10.5,
                    timestamp_end=12.0,
                    context_window="I commend the Deputy Prime Minister.",
                    sentiment_label="positive",
                    raw_mention="Deputy Prime Minister"
                )
            ]
        ),
        EdgeRecord(
            source_node_id="mp_davis_brave",
            target_node_id="mp_pintard_michael",
            total_mentions=3,
            positive_count=1,
            neutral_count=2,
            negative_count=0,
            net_sentiment=0.0,  # Neutral
            mention_details=[]
        ),
        EdgeRecord(
            source_node_id="mp_pintard_michael",
            target_node_id="mp_davis_brave",
            total_mentions=2,
            positive_count=0,
            neutral_count=0,
            negative_count=2,
            net_sentiment=-1.0,  # Negative
            mention_details=[
                MentionDetail(
                    timestamp_start=120.0,
                    timestamp_end=122.5,
                    context_window="The Prime Minister has failed.",
                    sentiment_label="negative",
                    raw_mention="Prime Minister"
                )
            ]
        ),
        EdgeRecord(
            source_node_id="mp_cooper_chester",
            target_node_id="mp_davis_brave",
            total_mentions=1,
            positive_count=1,
            neutral_count=0,
            negative_count=0,
            net_sentiment=1.0,  # Positive
            mention_details=[]
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


class TestSentimentColor:
    """Test sentiment-based edge coloring (MP-4)."""
    
    def test_positive_sentiment(self):
        """Positive sentiment should return green."""
        assert get_sentiment_color(0.3) == EDGE_COLOR_POSITIVE
        assert get_sentiment_color(1.0) == EDGE_COLOR_POSITIVE
    
    def test_negative_sentiment(self):
        """Negative sentiment should return red."""
        assert get_sentiment_color(-0.3) == EDGE_COLOR_NEGATIVE
        assert get_sentiment_color(-1.0) == EDGE_COLOR_NEGATIVE
    
    def test_neutral_sentiment(self):
        """Neutral sentiment should return grey."""
        assert get_sentiment_color(0.0) == EDGE_COLOR_NEUTRAL
        assert get_sentiment_color(0.1) == EDGE_COLOR_NEUTRAL
        assert get_sentiment_color(-0.1) == EDGE_COLOR_NEUTRAL
    
    def test_threshold_boundaries(self):
        """Test exact threshold values."""
        # Values at boundaries should be neutral (not strictly > or < threshold)
        assert get_sentiment_color(0.2) == EDGE_COLOR_NEUTRAL  # At positive boundary
        assert get_sentiment_color(0.21) == EDGE_COLOR_POSITIVE  # Just above
        assert get_sentiment_color(-0.2) == EDGE_COLOR_NEUTRAL  # At negative boundary
        assert get_sentiment_color(-0.21) == EDGE_COLOR_NEGATIVE  # Just below


class TestMetricNormalization:
    """Test metric value normalization."""
    
    def test_normalize_basic(self):
        """Test basic normalization."""
        values = [10, 20, 30]
        normalized = normalize_metric(values, min_size=10, max_size=50)
        
        assert len(normalized) == 3
        assert normalized[0] == 10  # Min value gets min size
        assert normalized[2] == 50  # Max value gets max size
        assert normalized[1] == 30  # Middle value
    
    def test_normalize_empty(self):
        """Empty list should return empty list."""
        assert normalize_metric([]) == []
    
    def test_normalize_single_value(self):
        """Single value should get middle size."""
        normalized = normalize_metric([100], min_size=10, max_size=50)
        assert len(normalized) == 1
        assert normalized[0] == 30  # Middle of range
    
    def test_normalize_identical_values(self):
        """Identical values should all get middle size."""
        normalized = normalize_metric([5, 5, 5], min_size=10, max_size=50)
        assert len(normalized) == 3
        assert all(n == 30 for n in normalized)


class TestGraphConstruction:
    """Test MP-1: Force-directed graph construction."""
    
    def test_builds_network(self, sample_session_graph):
        """Should build a PyVis Network object."""
        net = build_force_directed_graph(sample_session_graph)
        assert isinstance(net, Network)
    
    def test_node_count(self, sample_session_graph):
        """Network should have all nodes from session graph."""
        net = build_force_directed_graph(sample_session_graph)
        assert len(net.nodes) == sample_session_graph.node_count
    
    def test_edge_count(self, sample_session_graph):
        """Network should have all edges from session graph."""
        net = build_force_directed_graph(sample_session_graph)
        assert len(net.edges) == sample_session_graph.edge_count
    
    def test_directed_graph(self, sample_session_graph):
        """Graph should be directed."""
        net = build_force_directed_graph(sample_session_graph)
        # PyVis Network is directed if options include arrows
        assert net.directed is True


class TestPartyColors:
    """Test MP-2: Party-based color coding."""
    
    def test_plp_color(self, sample_session_graph):
        """PLP nodes should be gold."""
        net = build_force_directed_graph(sample_session_graph)
        
        # Find PLP nodes
        plp_nodes = [n for n in net.nodes if n["id"] in ["mp_davis_brave", "mp_cooper_chester"]]
        assert len(plp_nodes) == 2
        assert all(n["color"] == PARTY_COLORS["PLP"] for n in plp_nodes)
    
    def test_fnm_color_red(self, sample_session_graph):
        """FNM nodes should be red by default."""
        net = build_force_directed_graph(sample_session_graph, use_blue_for_fnm=False)
        
        # Find FNM node
        fnm_node = next(n for n in net.nodes if n["id"] == "mp_pintard_michael")
        assert fnm_node["color"] == PARTY_COLORS["FNM"]  # Red
        assert fnm_node["color"] == "#DC143C"
    
    def test_fnm_color_blue(self, sample_session_graph):
        """FNM nodes should be blue when toggled."""
        net = build_force_directed_graph(sample_session_graph, use_blue_for_fnm=True)
        
        # Find FNM node
        fnm_node = next(n for n in net.nodes if n["id"] == "mp_pintard_michael")
        assert fnm_node["color"] == "#1E90FF"  # Blue
    
    def test_coi_color(self, sample_session_graph):
        """COI nodes should be grey."""
        net = build_force_directed_graph(sample_session_graph)
        
        # Find COI node
        coi_node = next(n for n in net.nodes if n["id"] == "mp_gray_khaalis")
        assert coi_node["color"] == PARTY_COLORS["COI"]  # Grey
    
    def test_custom_colors(self, sample_session_graph):
        """Should accept custom party colors."""
        custom_colors = {
            "PLP": "#000000",
            "FNM": "#FFFFFF",
            "COI": "#FF00FF",
        }
        net = build_force_directed_graph(sample_session_graph, party_colors=custom_colors)
        
        plp_node = next(n for n in net.nodes if n["id"] == "mp_davis_brave")
        assert plp_node["color"] == "#000000"


class TestNodeSizing:
    """Test MP-3: Node sizing by metric."""
    
    def test_size_by_degree(self, sample_session_graph):
        """Node size should reflect degree centrality."""
        net = build_force_directed_graph(sample_session_graph, metric="degree")
        
        # Brave Davis has highest degree (4), should have largest size
        davis_node = next(n for n in net.nodes if n["id"] == "mp_davis_brave")
        cooper_node = next(n for n in net.nodes if n["id"] == "mp_cooper_chester")
        gray_node = next(n for n in net.nodes if n["id"] == "mp_gray_khaalis")
        
        assert davis_node["size"] > cooper_node["size"]
        assert cooper_node["size"] > gray_node["size"]
    
    def test_size_by_betweenness(self, sample_session_graph):
        """Node size should reflect betweenness centrality."""
        net = build_force_directed_graph(sample_session_graph, metric="betweenness")
        
        # Brave Davis has highest betweenness (1.0)
        davis_node = next(n for n in net.nodes if n["id"] == "mp_davis_brave")
        cooper_node = next(n for n in net.nodes if n["id"] == "mp_cooper_chester")
        
        assert davis_node["size"] > cooper_node["size"]
    
    def test_size_by_eigenvector(self, sample_session_graph):
        """Node size should reflect eigenvector centrality."""
        net = build_force_directed_graph(sample_session_graph, metric="eigenvector")
        
        # Brave Davis has highest eigenvector (0.707)
        davis_node = next(n for n in net.nodes if n["id"] == "mp_davis_brave")
        cooper_node = next(n for n in net.nodes if n["id"] == "mp_cooper_chester")
        
        assert davis_node["size"] > cooper_node["size"]
    
    def test_size_by_total_mentions(self, sample_session_graph):
        """Node size should reflect total mentions."""
        net = build_force_directed_graph(sample_session_graph, metric="total_mentions")
        
        # Brave Davis appears in most edges
        davis_node = next(n for n in net.nodes if n["id"] == "mp_davis_brave")
        gray_node = next(n for n in net.nodes if n["id"] == "mp_gray_khaalis")
        
        # Davis has mentions, Gray has none
        assert davis_node["size"] > gray_node["size"]
    
    def test_custom_size_range(self, sample_session_graph):
        """Should respect custom min/max node sizes."""
        net = build_force_directed_graph(
            sample_session_graph,
            min_node_size=20,
            max_node_size=100,
        )
        
        sizes = [n["size"] for n in net.nodes]
        assert min(sizes) >= 20
        assert max(sizes) <= 100


class TestEdgeStyling:
    """Test MP-4: Edge styling by mention count and sentiment."""
    
    def test_edge_colors(self, sample_session_graph):
        """Edges should be colored by sentiment."""
        net = build_force_directed_graph(sample_session_graph)
        
        # Find edge with positive sentiment (davis -> cooper, sentiment=0.8)
        positive_edge = next(
            e for e in net.edges
            if e["from"] == "mp_davis_brave" and e["to"] == "mp_cooper_chester"
        )
        assert positive_edge["color"] == EDGE_COLOR_POSITIVE
        
        # Find edge with negative sentiment (pintard -> davis, sentiment=-1.0)
        negative_edge = next(
            e for e in net.edges
            if e["from"] == "mp_pintard_michael" and e["to"] == "mp_davis_brave"
        )
        assert negative_edge["color"] == EDGE_COLOR_NEGATIVE
        
        # Find edge with neutral sentiment (davis -> pintard, sentiment=0.0)
        neutral_edge = next(
            e for e in net.edges
            if e["from"] == "mp_davis_brave" and e["to"] == "mp_pintard_michael"
        )
        assert neutral_edge["color"] == EDGE_COLOR_NEUTRAL
    
    def test_edge_thickness(self, sample_session_graph):
        """Edges should vary in thickness by mention count."""
        net = build_force_directed_graph(sample_session_graph)
        
        # Edge with 5 mentions should be thicker than edge with 1 mention
        thick_edge = next(
            e for e in net.edges
            if e["from"] == "mp_davis_brave" and e["to"] == "mp_cooper_chester"
        )
        thin_edge = next(
            e for e in net.edges
            if e["from"] == "mp_cooper_chester" and e["to"] == "mp_davis_brave"
        )
        
        assert thick_edge["width"] > thin_edge["width"]
    
    def test_edge_value(self, sample_session_graph):
        """Edges should have value property for mention count."""
        net = build_force_directed_graph(sample_session_graph)
        
        edge = next(
            e for e in net.edges
            if e["from"] == "mp_davis_brave" and e["to"] == "mp_cooper_chester"
        )
        assert edge["value"] == 5  # 5 mentions
    
    def test_custom_edge_width_range(self, sample_session_graph):
        """Should respect custom min/max edge widths."""
        net = build_force_directed_graph(
            sample_session_graph,
            min_edge_width=2.0,
            max_edge_width=20.0,
        )
        
        widths = [e["width"] for e in net.edges]
        assert min(widths) >= 2.0
        assert max(widths) <= 20.0


class TestTooltips:
    """Test interactive tooltips."""
    
    def test_node_tooltips(self, sample_session_graph):
        """Nodes should have informative tooltips."""
        net = build_force_directed_graph(sample_session_graph)
        
        davis_node = next(n for n in net.nodes if n["id"] == "mp_davis_brave")
        tooltip = davis_node["title"]
        
        # Should contain key information
        assert "Brave Davis" in tooltip
        assert "PLP" in tooltip
        assert "Degree:" in tooltip
        assert "Betweenness:" in tooltip
        assert "Eigenvector:" in tooltip
        assert "Roles:" in tooltip
    
    def test_edge_tooltips(self, sample_session_graph):
        """Edges should have informative tooltips."""
        net = build_force_directed_graph(sample_session_graph)
        
        edge = next(
            e for e in net.edges
            if e["from"] == "mp_davis_brave" and e["to"] == "mp_cooper_chester"
        )
        tooltip = edge["title"]
        
        # Should contain key information
        assert "mp_davis_brave" in tooltip
        assert "mp_cooper_chester" in tooltip
        assert "Mentions:" in tooltip
        assert "Sentiment:" in tooltip
        assert "Positive:" in tooltip
        assert "Neutral:" in tooltip
        assert "Negative:" in tooltip


class TestGraphConfiguration:
    """Test graph configuration options."""
    
    def test_custom_dimensions(self, sample_session_graph):
        """Should respect custom height and width."""
        net = build_force_directed_graph(
            sample_session_graph,
            height="600px",
            width="90%",
        )
        
        assert net.height == "600px"
        assert net.width == "90%"
    
    def test_physics_enabled(self, sample_session_graph):
        """Physics should be enabled for force-directed layout."""
        net = build_force_directed_graph(sample_session_graph)
        
        # Check that options include physics configuration
        options = net.options
        assert "physics" in options
        assert options["physics"]["enabled"] is True
