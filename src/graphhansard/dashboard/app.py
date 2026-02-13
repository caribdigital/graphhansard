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
from graphhansard.dashboard.graph_viz import build_force_directed_graph, render_graph_to_html


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

    st.title("GraphHansard")
    st.subheader("Bahamian House of Assembly — Political Interaction Network")

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
    
    # Load and display graph
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
            
            # Build force-directed graph (MP-1 through MP-4)
            with st.spinner("Rendering force-directed graph..."):
                net = build_force_directed_graph(
                    session_graph,
                    metric=metric,
                    use_blue_for_fnm=use_blue_for_fnm,
                    height="750px",
                    width="100%",
                )
                
                # Render to HTML
                html_path = render_graph_to_html(net, "/tmp/graph.html")
                
                # Display in Streamlit
                with open(html_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
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
