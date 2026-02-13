"""Example: Interactive Force-Directed Graph Visualization

Demonstrates how to build and render interactive network visualizations
for parliamentary interaction data.

Usage:
    python examples/visualize_graph.py
"""

import json
from pathlib import Path

from graphhansard.brain.graph_builder import SessionGraph
from graphhansard.dashboard.graph_viz import (
    build_force_directed_graph,
    render_graph_to_html,
)


def main():
    """Build interactive visualizations with different configurations."""
    
    # Check if sample data exists
    sample_path = Path("output/sample_session_metrics.json")
    if not sample_path.exists():
        print("❌ Sample data not found.")
        print("Run: python examples/build_session_graph.py")
        return
    
    # Load sample session graph
    print("Loading sample session graph...")
    with open(sample_path, "r") as f:
        data = json.load(f)
        session_graph = SessionGraph(**data)
    
    print(f"✓ Loaded {session_graph.session_id}")
    print(f"  Nodes: {session_graph.node_count}")
    print(f"  Edges: {session_graph.edge_count}")
    print()
    
    # Create output directory
    output_dir = Path("output/visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Example 1: Basic force-directed graph (degree centrality)
    print("1. Building graph with degree centrality sizing...")
    net = build_force_directed_graph(
        session_graph,
        metric="degree",
    )
    html_path = output_dir / "graph_degree.html"
    render_graph_to_html(net, str(html_path))
    print(f"   ✓ Saved to {html_path}")
    
    # Example 2: Betweenness centrality (bridge detection)
    print("2. Building graph with betweenness centrality (bridges)...")
    net = build_force_directed_graph(
        session_graph,
        metric="betweenness",
    )
    html_path = output_dir / "graph_betweenness.html"
    render_graph_to_html(net, str(html_path))
    print(f"   ✓ Saved to {html_path}")
    
    # Example 3: Eigenvector centrality (influence)
    print("3. Building graph with eigenvector centrality (influence)...")
    net = build_force_directed_graph(
        session_graph,
        metric="eigenvector",
    )
    html_path = output_dir / "graph_eigenvector.html"
    render_graph_to_html(net, str(html_path))
    print(f"   ✓ Saved to {html_path}")
    
    # Example 4: Total mentions
    print("4. Building graph with total mention count...")
    net = build_force_directed_graph(
        session_graph,
        metric="total_mentions",
    )
    html_path = output_dir / "graph_mentions.html"
    render_graph_to_html(net, str(html_path))
    print(f"   ✓ Saved to {html_path}")
    
    # Example 5: Custom colors (Blue for FNM)
    print("5. Building graph with blue FNM party color...")
    net = build_force_directed_graph(
        session_graph,
        metric="degree",
        use_blue_for_fnm=True,
    )
    html_path = output_dir / "graph_blue_fnm.html"
    render_graph_to_html(net, str(html_path))
    print(f"   ✓ Saved to {html_path}")
    
    # Example 6: Custom node and edge sizes
    print("6. Building graph with custom sizing...")
    net = build_force_directed_graph(
        session_graph,
        metric="degree",
        min_node_size=20,
        max_node_size=80,
        min_edge_width=2.0,
        max_edge_width=15.0,
    )
    html_path = output_dir / "graph_large_sizes.html"
    render_graph_to_html(net, str(html_path))
    print(f"   ✓ Saved to {html_path}")
    
    # Example 7: Compact graph
    print("7. Building compact graph...")
    net = build_force_directed_graph(
        session_graph,
        metric="degree",
        height="500px",
        width="100%",
    )
    html_path = output_dir / "graph_compact.html"
    render_graph_to_html(net, str(html_path))
    print(f"   ✓ Saved to {html_path}")
    
    print()
    print("✅ All visualizations generated successfully!")
    print()
    print("To view:")
    print(f"  - Open any HTML file in: {output_dir}/")
    print("  - Or run: streamlit run src/graphhansard/dashboard/app.py")
    print()
    print("Features demonstrated:")
    print("  ✓ MP-1: Force-directed layout")
    print("  ✓ MP-2: Party-based color coding")
    print("  ✓ MP-3: Multiple node sizing metrics")
    print("  ✓ MP-4: Edge thickness and sentiment coloring")


if __name__ == "__main__":
    main()
