"""Streamlit dashboard entry point.

Run with: streamlit run src/graphhansard/dashboard/app.py

See SRD §9 (Layer 3 — The Map) for specification.
"""

from __future__ import annotations

import json
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from rapidfuzz import fuzz

from graphhansard.brain.graph_builder import SessionGraph
from graphhansard.dashboard.graph_viz import build_force_directed_graph


# Configuration constants
FUZZY_MATCH_THRESHOLD = 75  # Minimum fuzzy matching score (0-100)
GOLDEN_RECORD_PATH = "golden_record/mps.json"  # Relative to project root


def load_sample_graph() -> SessionGraph | None:
    """Load sample session graph if available."""
    sample_path = Path("output/sample_session_metrics.json")
    if sample_path.exists():
        with open(sample_path, "r") as f:
            data = json.load(f)
            return SessionGraph(**data)
    return None


def load_golden_record() -> dict:
    """Load Golden Record for MP search and alias resolution."""
    golden_record_path = Path(GOLDEN_RECORD_PATH)
    if golden_record_path.exists():
        with open(golden_record_path, "r") as f:
            return json.load(f)
    return {"mps": []}


def filter_graph_by_party(
    session_graph: SessionGraph, 
    selected_parties: list[str], 
    cross_party_only: bool
) -> SessionGraph:
    """Filter graph nodes and edges by party.
    
    Args:
        session_graph: Original session graph
        selected_parties: List of party names to include (e.g., ["PLP", "FNM"])
        cross_party_only: If True, only show edges between different parties
        
    Returns:
        Filtered SessionGraph
    """
    from graphhansard.brain.graph_builder import EdgeRecord, NodeMetrics
    
    # Filter nodes by party
    filtered_nodes = [
        node for node in session_graph.nodes
        if node.party in selected_parties
    ]
    
    # Get node IDs for filtering edges
    node_ids = {node.node_id for node in filtered_nodes}
    
    # Filter edges: both endpoints must be in filtered nodes
    filtered_edges = []
    for edge in session_graph.edges:
        if edge.source_node_id in node_ids and edge.target_node_id in node_ids:
            # Get party info for cross-party filtering
            source_party = next(
                (n.party for n in filtered_nodes if n.node_id == edge.source_node_id),
                None
            )
            target_party = next(
                (n.party for n in filtered_nodes if n.node_id == edge.target_node_id),
                None
            )
            
            # If cross_party_only is enabled, only include edges between different parties
            if cross_party_only:
                if source_party != target_party:
                    filtered_edges.append(edge)
            else:
                filtered_edges.append(edge)
    
    # Create filtered graph
    filtered_graph = SessionGraph(
        session_id=session_graph.session_id,
        date=session_graph.date,
        graph_file=session_graph.graph_file,
        node_count=len(filtered_nodes),
        edge_count=len(filtered_edges),
        nodes=filtered_nodes,
        edges=filtered_edges,
        modularity_score=session_graph.modularity_score,
    )
    
    return filtered_graph


def search_mp(query: str, golden_record: dict, session_graph: SessionGraph) -> list[str]:
    """Search for MPs by name, alias, or constituency using fuzzy matching.
    
    Args:
        query: Search query string
        golden_record: Golden Record data with MP information
        session_graph: Current session graph (for filtering to MPs in graph)
        
    Returns:
        List of matching node_ids
    """
    if not query:
        return []
    
    # Get MPs in current graph
    graph_node_ids = {node.node_id for node in session_graph.nodes}
    
    matches = []
    query_lower = query.lower()
    
    for mp in golden_record.get("mps", []):
        node_id = mp.get("node_id")
        
        # Only search MPs in current graph
        if node_id not in graph_node_ids:
            continue
        
        # Check common name
        common_name = mp.get("common_name", "")
        if fuzz.partial_ratio(query_lower, common_name.lower()) >= FUZZY_MATCH_THRESHOLD:
            matches.append(node_id)
            continue
        
        # Check full name
        full_name = mp.get("full_name", "")
        if fuzz.partial_ratio(query_lower, full_name.lower()) >= FUZZY_MATCH_THRESHOLD:
            matches.append(node_id)
            continue
        
        # Check aliases
        for alias in mp.get("aliases", []):
            if fuzz.partial_ratio(query_lower, alias.lower()) >= FUZZY_MATCH_THRESHOLD:
                matches.append(node_id)
                break
        else:
            # Check constituency (only if no alias matched)
            constituency = mp.get("constituency", "")
            if fuzz.partial_ratio(query_lower, constituency.lower()) >= FUZZY_MATCH_THRESHOLD:
                matches.append(node_id)
    
    return list(set(matches))  # Remove duplicates


def main():
    """Launch the GraphHansard interactive dashboard."""
    st.set_page_config(
        page_title="GraphHansard — Bahamian Parliamentary Network",
        page_icon="🏛️",
        layout="wide",
    )

    st.title("GraphHansard")
    st.subheader("Bahamian House of Assembly — Political Interaction Network")

    # Load Golden Record for search functionality
    golden_record = load_golden_record()

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
    
    # Graph type selector (MP-1)
    graph_type = st.sidebar.radio(
        "Graph Type",
        options=["Sample Session", "Single Session", "Cumulative"],
        index=0,
        help="Select which graph to display"
    )
    
    st.sidebar.markdown("---")
    
    # MP-7: Date Range Filter
    st.sidebar.header("📅 Date Range Filter (MP-7)")
    date_filter_type = st.sidebar.selectbox(
        "Filter Type",
        options=["Full Term", "Single Session", "Date Range"],
        index=0,
        help="Select date filtering option"
    )
    
    if date_filter_type == "Single Session":
        # For now, show info about upcoming feature
        st.sidebar.info("Single session selector coming with additional data.")
    elif date_filter_type == "Date Range":
        # Date range picker (currently disabled until multiple sessions available)
        st.sidebar.info("Date range picker coming with additional sessions.")
    
    st.sidebar.markdown("---")
    
    # MP-8: Party Filter
    st.sidebar.header("🎨 Party Filter (MP-8)")
    
    # Party selection checkboxes
    show_plp = st.sidebar.checkbox("PLP (Progressive Liberal Party)", value=True)
    show_fnm = st.sidebar.checkbox("FNM (Free National Movement)", value=True)
    show_coi = st.sidebar.checkbox("COI (Coalition of Independents)", value=True)
    
    # Cross-party only toggle
    cross_party_only = st.sidebar.checkbox(
        "Cross-party edges only",
        value=False,
        help="Show only interactions between MPs of different parties"
    )
    
    st.sidebar.markdown("---")
    
    # MP-9: Search Bar
    st.sidebar.header("🔍 Search MP (MP-9)")
    search_query = st.sidebar.text_input(
        "Search by name, alias, or constituency",
        placeholder="e.g., Brave, Chester, Fox Hill",
        help="Use fuzzy matching to find MPs"
    )
    
    # Load and display graph
    if graph_type == "Sample Session":
        session_graph = load_sample_graph()
        
        if session_graph is None:
            st.warning(
                "⚠️ Sample graph not found. "
                "Run `python examples/build_session_graph.py` to generate sample data."
            )
        else:
            # Apply party filter (MP-8)
            selected_parties = []
            if show_plp:
                selected_parties.append("PLP")
            if show_fnm:
                selected_parties.append("FNM")
            if show_coi:
                selected_parties.append("COI")
            
            if not selected_parties:
                st.warning("⚠️ Please select at least one party to display.")
                return
            
            # Filter graph
            filtered_graph = filter_graph_by_party(
                session_graph, 
                selected_parties, 
                cross_party_only
            )
            
            # Apply search filter (MP-9)
            search_matches = []
            if search_query:
                search_matches = search_mp(search_query, golden_record, filtered_graph)
                if search_matches:
                    st.sidebar.success(f"✓ Found {len(search_matches)} matching MP(s)")
                else:
                    st.sidebar.warning("No matches found")
            
            st.success(f"✅ Loaded {filtered_graph.session_id} ({filtered_graph.date})")
            st.markdown(f"**{filtered_graph.node_count}** MPs, **{filtered_graph.edge_count}** interactions")
            
            if filtered_graph.node_count == 0:
                st.warning("⚠️ No MPs match the current filters.")
                return
            
            # Build force-directed graph (MP-1 through MP-4)
            with st.spinner("Rendering force-directed graph..."):
                net = build_force_directed_graph(
                    filtered_graph,
                    metric=metric,
                    use_blue_for_fnm=use_blue_for_fnm,
                    height="750px",
                    width="100%",
                    highlight_nodes=search_matches if search_matches else None,
                )
                
                # Render to HTML in memory (no temp file needed)
                html_content = net.generate_html()
                components.html(html_content, height=800, scrolling=True)
            
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
            
            # Show active filters
            if search_matches:
                st.info(f"🔍 **Search Filter Active**: Highlighting {len(search_matches)} MP(s)")
            
            # Show metrics table
            st.markdown("---")
            st.subheader("Node Metrics")
            
            # Build metrics dataframe
            metrics_data = []
            for node in filtered_graph.nodes:
                # Highlight searched MPs in the table
                mp_name = node.common_name
                if search_matches and node.node_id in search_matches:
                    mp_name = f"⭐ {mp_name}"
                
                metrics_data.append({
                    "MP": mp_name,
                    "Party": node.party,
                    "Degree In": node.degree_in,
                    "Degree Out": node.degree_out,
                    "Betweenness": f"{node.betweenness:.3f}",
                    "Eigenvector": f"{node.eigenvector:.3f}",
                    "Roles": ", ".join(node.structural_role) if node.structural_role else "None",
                })
            
            st.dataframe(metrics_data, use_container_width=True)
    
    elif graph_type == "Single Session":
        st.info(
            "📋 **Single Session graphs coming soon.**\n\n"
            "This will allow you to select any parliamentary session and view its interaction network."
        )
    
    elif graph_type == "Cumulative":
        st.info(
            "📋 **Cumulative graphs coming soon.**\n\n"
            "This will aggregate multiple sessions to show overall patterns across a date range."
        )


if __name__ == "__main__":
    main()
