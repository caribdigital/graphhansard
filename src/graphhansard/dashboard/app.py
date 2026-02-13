"""Streamlit dashboard entry point.

Run with: streamlit run src/graphhansard/dashboard/app.py

See SRD §9 (Layer 3 — The Map) for specification.
"""

from __future__ import annotations

import json
import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

from graphhansard.brain.graph_builder import SessionGraph
from graphhansard.dashboard.graph_viz import build_force_directed_graph
from graphhansard.dashboard.leaderboard import render_leaderboard
from graphhansard.dashboard.timeline import discover_sessions, render_timeline, load_session_data
from graphhansard.dashboard.mp_report_card import (
    build_report_card,
    render_report_card,
    render_mp_selector,
)


def load_sample_graph() -> SessionGraph | None:
    """Load sample session graph if available."""
    sample_path = Path("output/sample_session_metrics.json")
    if sample_path.exists():
        with open(sample_path, "r") as f:
            data = json.load(f)
            return SessionGraph(**data)
    return None


def main():
    """Launch the GraphHansard interactive dashboard."""
    st.set_page_config(
        page_title="GraphHansard — Bahamian Parliamentary Network",
        page_icon="🏛️",
        layout="wide",
    )

    # Check for MP Report Card URL parameter (MP-13)
    query_params = st.query_params
    mp_id_param = query_params.get("mp_id")
    
    # Initialize session state
    if "selected_session" not in st.session_state:
        st.session_state.selected_session = None
    if "highlighted_node" not in st.session_state:
        st.session_state.highlighted_node = None

    st.title("GraphHansard")
    st.subheader("Bahamian House of Assembly — Political Interaction Network")

    # Sidebar controls
    st.sidebar.header("Navigation")
    
    # View selector
    view_mode = st.sidebar.radio(
        "Dashboard View",
        options=["Graph Explorer", "Session Timeline", "MP Report Card"],
        index=0,
        help="Select dashboard view"
    )
    
    st.sidebar.markdown("---")
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
        options=["Sample Session", "Timeline Sessions"],
        index=0,
        help="Select which graph to display"
    )
    
    # === VIEW MODE: MP REPORT CARD (MP-13) ===
    if view_mode == "MP Report Card" or mp_id_param:
        st.markdown("---")
        
        # Discover sessions for report card
        sessions = discover_sessions()
        
        if not sessions:
            st.warning("No session data available. Generate sample data with `python examples/build_session_graph.py`")
            return
        
        # Load all sessions for report card
        session_graphs = []
        for session_info in sessions:
            if session_info.has_data:
                data = load_session_data(session_info)
                if data:
                    session_graphs.append(SessionGraph(**data))
        
        if not session_graphs:
            st.warning("Could not load session data.")
            return
        
        # If MP ID provided in URL, use it directly
        if mp_id_param:
            selected_mp_id = mp_id_param
        else:
            # Otherwise show MP selector
            selected_mp_id = render_mp_selector(session_graphs)
        
        if selected_mp_id:
            # Build and render report card
            report_card = build_report_card(selected_mp_id, session_graphs)
            
            if report_card:
                render_report_card(report_card)
            else:
                st.error(f"No data found for MP: {selected_mp_id}")
        
        return
    
    # === VIEW MODE: SESSION TIMELINE (MP-12) ===
    if view_mode == "Session Timeline":
        st.markdown("---")
        
        # Discover available sessions
        sessions = discover_sessions()
        
        # Callback for session selection
        def on_session_select(session_info):
            st.session_state.selected_session = session_info
        
        # Render timeline
        selected_session = render_timeline(
            sessions=sessions,
            selected_session=st.session_state.selected_session,
            on_session_select=on_session_select,
        )
        
        # Update session state if changed
        if selected_session:
            st.session_state.selected_session = selected_session
        
        # Load and display selected session
        if st.session_state.selected_session:
            session_info = st.session_state.selected_session
            st.markdown("---")
            st.subheader(f"Session: {session_info.display_date}")
            
            # Load session data
            data = load_session_data(session_info)
            if data:
                session_graph = SessionGraph(**data)
                
                # Display session info
                st.success(f"✅ Loaded {session_graph.session_id} ({session_graph.date})")
                st.markdown(f"**{session_graph.node_count}** MPs, **{session_graph.edge_count}** interactions")
                
                # Build force-directed graph
                with st.spinner("Rendering force-directed graph..."):
                    net = build_force_directed_graph(
                        session_graph,
                        metric=metric,
                        use_blue_for_fnm=use_blue_for_fnm,
                        height="600px",
                        width="100%",
                    )
                    
                    html_content = net.generate_html()
                    components.html(html_content, height=650, scrolling=True)
            else:
                st.error(f"Could not load data for session: {session_info.session_id}")
        
        return
    
    # === VIEW MODE: GRAPH EXPLORER (default with leaderboard) ===
    
    # === VIEW MODE: GRAPH EXPLORER (default with leaderboard) ===
    if graph_type == "Sample Session":
        session_graph = load_sample_graph()
        
        if session_graph is None:
            st.warning(
                "⚠️ Sample graph not found. "
                "Run `python examples/build_session_graph.py` to generate sample data."
            )
        else:
            st.success(f"✅ Loaded {session_graph.session_id} ({session_graph.date})")
            st.markdown(f"**{session_graph.node_count}** MPs, **{session_graph.edge_count}** interactions")
            
            # Create two columns: main graph and sidebar leaderboard
            col_graph, col_leaderboard = st.columns([3, 1])
            
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
                    
                    # Render to HTML in memory (no temp file needed)
                    html_content = net.generate_html()
                    components.html(html_content, height=800, scrolling=True)
            
            with col_leaderboard:
                # Render Leaderboard (MP-10)
                def on_mp_click(node_id):
                    st.session_state.highlighted_node = node_id
                    st.info(f"Node highlighted: {node_id}")
                
                render_leaderboard(session_graph, on_mp_click=on_mp_click)
            
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
            
            # Show metrics table
            st.markdown("---")
            st.subheader("Node Metrics")
            
            # Build metrics dataframe
            metrics_data = []
            for node in session_graph.nodes:
                metrics_data.append({
                    "MP": node.common_name,
                    "Party": node.party,
                    "Degree In": node.degree_in,
                    "Degree Out": node.degree_out,
                    "Betweenness": f"{node.betweenness:.3f}",
                    "Eigenvector": f"{node.eigenvector:.3f}",
                    "Roles": ", ".join(node.structural_role) if node.structural_role else "None",
                })
            
            st.dataframe(metrics_data, use_container_width=True)
    
    elif graph_type == "Timeline Sessions":
        # Redirect to timeline view
        st.info("📋 Switch to **Session Timeline** view in the sidebar to explore sessions over time.")
        st.markdown("The Session Timeline view provides:")
        st.markdown("- 📅 Horizontal timeline of all available sessions")
        st.markdown("- 🔍 Session selection and graph visualization")
        st.markdown("- ⏮️ Previous/Next navigation")
        st.markdown("- ✅ Visual indicators for data availability")


if __name__ == "__main__":
    main()
