"""Force-directed graph visualization for GraphHansard.

Implements MP-1 through MP-4: Interactive network visualization with
party-based coloring, metric-driven sizing, and sentiment-based styling.

See SRD §9.3 (Layer 3 — The Map) and Issue #16.
"""

from __future__ import annotations

from typing import Literal

from pyvis.network import Network

from graphhansard.brain.graph_builder import SessionGraph


# Party color scheme per acceptance criteria
PARTY_COLORS = {
    "PLP": "#FFD700",  # Gold
    "FNM": "#DC143C",  # Red (can be toggled to Blue #1E90FF)
    "COI": "#808080",  # Grey
    "Unknown": "#C0C0C0",  # Silver for undefined parties
}

# Sentiment color thresholds per MP-4
SENTIMENT_POSITIVE_THRESHOLD = 0.2
SENTIMENT_NEGATIVE_THRESHOLD = -0.2

# Edge colors for sentiment
EDGE_COLOR_POSITIVE = "#00FF00"  # Green
EDGE_COLOR_NEUTRAL = "#808080"  # Grey
EDGE_COLOR_NEGATIVE = "#FF0000"  # Red


def get_sentiment_color(net_sentiment: float) -> str:
    """Map net sentiment to edge color per MP-4.
    
    Args:
        net_sentiment: Net sentiment score from EdgeRecord
        
    Returns:
        Hex color code (green, grey, or red)
    """
    if net_sentiment > SENTIMENT_POSITIVE_THRESHOLD:
        return EDGE_COLOR_POSITIVE
    elif net_sentiment < SENTIMENT_NEGATIVE_THRESHOLD:
        return EDGE_COLOR_NEGATIVE
    else:
        return EDGE_COLOR_NEUTRAL


def normalize_metric(
    values: list[float],
    min_size: int = 10,
    max_size: int = 50,
) -> list[float]:
    """Normalize metric values to node size range.
    
    Args:
        values: List of metric values
        min_size: Minimum node size in pixels
        max_size: Maximum node size in pixels
        
    Returns:
        List of normalized sizes
    """
    if not values:
        return []
    
    min_val = min(values)
    max_val = max(values)
    
    # Handle case where all values are the same
    if max_val == min_val:
        return [min_size + (max_size - min_size) / 2] * len(values)
    
    # Linear normalization
    normalized = []
    for val in values:
        norm = (val - min_val) / (max_val - min_val)
        size = min_size + norm * (max_size - min_size)
        normalized.append(size)
    
    return normalized


def build_force_directed_graph(
    session_graph: SessionGraph,
    metric: Literal["degree", "betweenness", "eigenvector", "total_mentions"] = "degree",
    party_colors: dict[str, str] | None = None,
    use_blue_for_fnm: bool = False,
    min_node_size: int = 10,
    max_node_size: int = 50,
    min_edge_width: float = 1.0,
    max_edge_width: float = 10.0,
    height: str = "750px",
    width: str = "100%",
) -> Network:
    """Build interactive force-directed graph using PyVis.
    
    Implements MP-1 through MP-4 requirements:
    - MP-1: Force-directed layout with MPs as nodes, mentions as edges
    - MP-2: Party-based color coding (PLP=gold, FNM=red/blue, COI=grey)
    - MP-3: Node size by selectable metric
    - MP-4: Edge thickness by mention count, color by sentiment
    
    Args:
        session_graph: SessionGraph with nodes and edges
        metric: Metric to use for node sizing
        party_colors: Optional custom party color mapping
        use_blue_for_fnm: If True, use blue (#1E90FF) instead of red for FNM
        min_node_size: Minimum node size in pixels
        max_node_size: Maximum node size in pixels
        min_edge_width: Minimum edge width
        max_edge_width: Maximum edge width
        height: Graph height (CSS format)
        width: Graph width (CSS format)
        
    Returns:
        PyVis Network object ready to render
    """
    # Initialize PyVis network with force-directed physics
    net = Network(
        height=height,
        width=width,
        notebook=False,
        directed=True,
    )
    
    # Configure physics for force-directed layout
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 200,
                "springConstant": 0.08,
                "damping": 0.4,
                "avoidOverlap": 1
            },
            "solver": "forceAtlas2Based",
            "stabilization": {
                "enabled": true,
                "iterations": 100
            }
        },
        "edges": {
            "smooth": {
                "enabled": true,
                "type": "dynamic"
            },
            "arrows": {
                "to": {
                    "enabled": true,
                    "scaleFactor": 0.5
                }
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "zoomView": true,
            "dragView": true
        }
    }
    """)
    
    # Use custom colors or defaults
    colors = party_colors or PARTY_COLORS.copy()
    if use_blue_for_fnm:
        colors["FNM"] = "#1E90FF"  # Blue
    
    # Extract metric values for normalization (MP-3)
    metric_values = []
    for node in session_graph.nodes:
        if metric == "degree":
            metric_values.append(node.degree_in + node.degree_out)
        elif metric == "betweenness":
            metric_values.append(node.betweenness)
        elif metric == "eigenvector":
            metric_values.append(node.eigenvector)
        elif metric == "total_mentions":
            # Calculate total mentions for this node across all edges
            total = 0
            for edge in session_graph.edges:
                if edge.source_node_id == node.node_id:
                    total += edge.total_mentions
                if edge.target_node_id == node.node_id:
                    total += edge.total_mentions
            metric_values.append(total)
    
    # Normalize to node size range
    node_sizes = normalize_metric(metric_values, min_node_size, max_node_size)
    
    # Add nodes with party colors and metric-based sizing (MP-2, MP-3)
    for idx, node in enumerate(session_graph.nodes):
        color = colors.get(node.party, colors["Unknown"])
        size = node_sizes[idx]
        
        # Build tooltip with node info
        tooltip = f"""
        <b>{node.common_name}</b><br>
        Party: {node.party}<br>
        Degree: {node.degree_in + node.degree_out} (in: {node.degree_in}, out: {node.degree_out})<br>
        Betweenness: {node.betweenness:.3f}<br>
        Eigenvector: {node.eigenvector:.3f}<br>
        Roles: {', '.join(node.structural_role) if node.structural_role else 'None'}
        """
        
        net.add_node(
            node.node_id,
            label=node.common_name,
            title=tooltip.strip(),
            color=color,
            size=size,
        )
    
    # Extract edge weights for normalization (MP-4)
    edge_weights = [edge.total_mentions for edge in session_graph.edges]
    
    # Normalize edge widths
    if edge_weights:
        min_weight = min(edge_weights)
        max_weight = max(edge_weights)
        
        if max_weight > min_weight:
            edge_widths = [
                min_edge_width + (w - min_weight) / (max_weight - min_weight) * (max_edge_width - min_edge_width)
                for w in edge_weights
            ]
        else:
            edge_widths = [(min_edge_width + max_edge_width) / 2] * len(edge_weights)
    else:
        edge_widths = []
    
    # Add edges with thickness and sentiment color (MP-4)
    for idx, edge in enumerate(session_graph.edges):
        # Color by sentiment
        edge_color = get_sentiment_color(edge.net_sentiment)
        
        # Width by mention count
        width = edge_widths[idx] if idx < len(edge_widths) else min_edge_width
        
        # Build tooltip
        tooltip = f"""
        <b>{edge.source_node_id} → {edge.target_node_id}</b><br>
        Mentions: {edge.total_mentions}<br>
        Sentiment: {edge.net_sentiment:+.2f}<br>
        Positive: {edge.positive_count}, Neutral: {edge.neutral_count}, Negative: {edge.negative_count}
        """
        
        net.add_edge(
            edge.source_node_id,
            edge.target_node_id,
            title=tooltip.strip(),
            color=edge_color,
            width=width,
            value=edge.total_mentions,  # For automatic scaling
        )
    
    return net


def render_graph_to_html(
    net: Network,
    output_path: str = "/tmp/graph.html",
) -> str:
    """Render PyVis network to HTML file.
    
    Args:
        net: PyVis Network object
        output_path: Path to output HTML file
        
    Returns:
        Path to generated HTML file
    """
    net.save_graph(output_path)
    return output_path
