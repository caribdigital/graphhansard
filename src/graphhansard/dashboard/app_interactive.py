"""Enhanced Streamlit dashboard with interactive MP profiles and mention details.

Run with: streamlit run src/graphhansard/dashboard/app_interactive.py

Implements MP-5 (node click → MP profile), MP-6 (edge click → mention details),
and MP-11 (drag-and-drop nodes).
"""

from __future__ import annotations

import json
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

from graphhansard.brain.graph_builder import SessionGraph
from graphhansard.dashboard.graph_viz import build_force_directed_graph
from graphhansard.dashboard.interactive_graph import (
    format_youtube_timestamp_link,
    format_sentiment_badge,
)


def load_sample_graph() -> SessionGraph | None:
    """Load sample session graph if available."""
    sample_path = Path("output/sample_session_metrics.json")
    if sample_path.exists():
        with open(sample_path, "r") as f:
            data = json.load(f)
            return SessionGraph(**data)
    return None


def display_mp_profile(node_id: str, session_graph: SessionGraph):
    """Display MP profile card for MP-5 (node click).
    
    Args:
        node_id: ID of the clicked node
        session_graph: Session graph with node data
    """
    # Find node in session graph
    node = next((n for n in session_graph.nodes if n.node_id == node_id), None)
    
    if node is None:
        st.error(f"Node {node_id} not found")
        return
    
    # Display profile card
    st.subheader("🏛️ MP Profile")
    st.markdown(f"### {node.common_name}")
    
    # Basic info
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Party:** {node.party}")
        if node.constituency:
            st.markdown(f"**Constituency:** {node.constituency}")
    with col2:
        if node.current_portfolio:
            st.markdown(f"**Portfolio:** {node.current_portfolio}")
        if node.community_id is not None:
            st.markdown(f"**Community:** {node.community_id}")
    
    # Centrality scores
    st.markdown("---")
    st.markdown("**📊 Centrality Scores**")
    
    metrics_col1, metrics_col2 = st.columns(2)
    with metrics_col1:
        st.metric("Degree (In)", node.degree_in)
        st.metric("Betweenness", f"{node.betweenness:.3f}")
    with metrics_col2:
        st.metric("Degree (Out)", node.degree_out)
        st.metric("Eigenvector", f"{node.eigenvector:.3f}")
    
    st.metric("Closeness", f"{node.closeness:.3f}")
    
    # Structural roles
    if node.structural_role:
        st.markdown("---")
        st.markdown("**🎯 Structural Roles**")
        for role in node.structural_role:
            role_display = role.replace('_', ' ').title()
            st.markdown(f"- {role_display}")
    
    st.markdown("---")
    st.caption(f"Node ID: `{node_id}`")


def display_mention_details(
    source_id: str,
    target_id: str,
    session_graph: SessionGraph,
    youtube_url: str = "https://www.youtube.com/watch?v=example",
):
    """Display mention details for MP-6 (edge click).
    
    Args:
        source_id: Source node ID
        target_id: Target node ID
        session_graph: Session graph with edge data
        youtube_url: Base YouTube URL for generating timestamped links
    """
    # Find edge in session graph
    edge = next(
        (e for e in session_graph.edges
         if e.source_node_id == source_id and e.target_node_id == target_id),
        None
    )
    
    if edge is None:
        st.error(f"Edge {source_id} → {target_id} not found")
        return
    
    # Get source and target names
    source_node = next((n for n in session_graph.nodes if n.node_id == source_id), None)
    target_node = next((n for n in session_graph.nodes if n.node_id == target_id), None)
    
    source_name = source_node.common_name if source_node else source_id
    target_name = target_node.common_name if target_node else target_id
    
    # Display mention details
    st.subheader("💬 Mention Details")
    st.markdown(f"### {source_name} → {target_name}")
    
    # Summary metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Mentions", edge.total_mentions)
    with col2:
        st.metric("Net Sentiment", f"{edge.net_sentiment:+.2f}")
    
    # Sentiment breakdown
    st.markdown(f"🟢 Positive: {edge.positive_count} | "
                f"⚫ Neutral: {edge.neutral_count} | "
                f"🔴 Negative: {edge.negative_count}")
    
    # Individual mentions with timestamps
    if edge.mention_details:
        st.markdown("---")
        st.markdown("**📝 Individual Mentions**")
        
        for idx, mention in enumerate(edge.mention_details, 1):
            with st.expander(f"Mention #{idx} — {format_sentiment_badge(mention.sentiment_label)}"):
                # Display mention details
                if mention.raw_mention:
                    st.markdown(f"**Raw Mention:** \"{mention.raw_mention}\"")
                
                # Context
                st.markdown(f"**Context:**")
                st.markdown(f"> {mention.context_window}")
                
                # Timestamp with YouTube link
                st.markdown(f"**Timestamp:** {mention.timestamp_start:.1f}s - {mention.timestamp_end:.1f}s")
                
                # Generate YouTube link with timestamp
                timestamp_link = format_youtube_timestamp_link(
                    youtube_url,
                    mention.timestamp_start,
                    label=f"▶️ Play at {int(mention.timestamp_start)}s"
                )
                st.markdown(timestamp_link)
    else:
        st.info("No detailed mention records available for this edge.")
    
    st.markdown("---")
    st.caption(f"Edge: `{source_id}` → `{target_id}`")


def main():
    """Launch the GraphHansard interactive dashboard."""
    st.set_page_config(
        page_title="GraphHansard — Interactive Network",
        page_icon="🏛️",
        layout="wide",
    )

    st.title("GraphHansard — Interactive Dashboard")
    st.subheader("Bahamian House of Assembly Political Network (MP-5, MP-6, MP-11)")

    # Sidebar controls
    st.sidebar.header("Graph Controls")
    
    # Metric selector (MP-3)
    metric = st.sidebar.selectbox(
        "Node Size Metric",
        options=["degree", "betweenness", "eigenvector", "total_mentions"],
        index=0,
        help="Select which metric to use for sizing nodes"
    )
    
    # Party color toggle for FNM (MP-2)
    use_blue_for_fnm = st.sidebar.checkbox(
        "Use Blue for FNM (instead of Red)",
        value=False,
        help="Toggle FNM party color between Red and Blue"
    )
    
    # Load session graph
    session_graph = load_sample_graph()
    
    if session_graph is None:
        st.warning(
            "⚠️ Sample graph not found. "
            "Run `python examples/build_session_graph.py` to generate sample data."
        )
        return
    
    # Build node and edge selector options
    node_options = ["None"] + [f"{n.common_name} ({n.node_id})" for n in session_graph.nodes]
    edge_options = ["None"] + [
        f"{next(n.common_name for n in session_graph.nodes if n.node_id == e.source_node_id)} → "
        f"{next(n.common_name for n in session_graph.nodes if n.node_id == e.target_node_id)}"
        for e in session_graph.edges
    ]
    
    # MP-5, MP-6: Interaction selectors
    st.sidebar.markdown("---")
    st.sidebar.header("Interactions")
    
    # Node selector for MP profile (MP-5)
    selected_node = st.sidebar.selectbox(
        "Select MP to View Profile (MP-5)",
        options=node_options,
        key="node_selector",
        help="Select an MP to view their profile"
    )
    
    # Edge selector for mention details (MP-6)
    selected_edge = st.sidebar.selectbox(
        "Select Edge for Mention Details (MP-6)",
        options=edge_options,
        key="edge_selector",
        help="Select an edge to view mention details"
    )
    
    # YouTube URL for timestamp links (MP-6)
    youtube_url = st.sidebar.text_input(
        "Session Video URL",
        value="https://www.youtube.com/watch?v=example",
        help="Base YouTube URL for generating timestamped links"
    )
    
    # Session info
    st.success(f"✅ Loaded {session_graph.session_id} ({session_graph.date})")
    st.markdown(f"**{session_graph.node_count}** MPs, **{session_graph.edge_count}** interactions")
    
    # Main layout with graph and interaction panel
    col_graph, col_panel = st.columns([2, 1])
    
    with col_graph:
        # Build force-directed graph (MP-1 through MP-4)
        with st.spinner("Rendering force-directed graph..."):
            net = build_force_directed_graph(
                session_graph,
                metric=metric,
                use_blue_for_fnm=use_blue_for_fnm,
                height="750px",
                width="100%",
            )
            
            # Render to HTML in memory
            html_content = net.generate_html()
            components.html(html_content, height=800, scrolling=True)
        
        # MP-11: Drag-and-drop info
        st.info("💡 **MP-11**: Drag nodes to reposition them. The layout will recalculate in real-time.")
    
    with col_panel:
        # MP-5: Display MP profile if node selected
        if selected_node and selected_node != "None":
            # Extract node_id from selection "Name (node_id)"
            node_id = selected_node.rsplit("(", 1)[1].rstrip(")")
            display_mp_profile(node_id, session_graph)
        
        # MP-6: Display mention details if edge selected
        elif selected_edge and selected_edge != "None":
            # Extract source and target from selection "Source → Target"
            parts = selected_edge.split(" → ")
            if len(parts) == 2:
                source_name, target_name = parts
                # Find node IDs from names
                source_node = next(
                    (n for n in session_graph.nodes if n.common_name == source_name),
                    None
                )
                target_node = next(
                    (n for n in session_graph.nodes if n.common_name == target_name),
                    None
                )
                if source_node and target_node:
                    display_mention_details(
                        source_node.node_id,
                        target_node.node_id,
                        session_graph,
                        youtube_url
                    )
        else:
            st.info(
                "👆 **Select a node or edge** from the sidebar to view details.\n\n"
                "- **MP-5**: Select a node to view MP profile\n"
                "- **MP-6**: Select an edge to view mention details\n"
                "- **MP-11**: Drag nodes in the graph to explore topology"
            )
    
    # Display legend
    st.markdown("---")
    st.subheader("Legend")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Party Colors (MP-2)**")
        st.markdown("🟡 **PLP** — Gold (#FFD700)")
        if use_blue_for_fnm:
            st.markdown("🔵 **FNM** — Blue (#1E90FF)")
        else:
            st.markdown("🔴 **FNM** — Red (#DC143C)")
        st.markdown("⚫ **COI** — Grey (#808080)")
    
    with col2:
        st.markdown("**Edge Colors (MP-4)**")
        st.markdown("🟢 **Positive** — Net sentiment > 0.2")
        st.markdown("⚫ **Neutral** — Net sentiment -0.2 to 0.2")
        st.markdown("🔴 **Negative** — Net sentiment < -0.2")
    
    st.markdown(f"**Node Size**: {metric.replace('_', ' ').title()}")
    st.markdown("**Edge Thickness**: Mention count")


if __name__ == "__main__":
    main()
