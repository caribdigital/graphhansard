"""MP Leaderboard component for GraphHansard dashboard.

Implements MP-10: Display top 5 MPs by centrality metrics with structural role badges.

See SRD §9.2 (MP-10) for specification.
"""

from __future__ import annotations

import streamlit as st
from graphhansard.brain.graph_builder import SessionGraph, StructuralRole


def get_top_mps_by_metric(
    session_graph: SessionGraph,
    metric: str,
    top_n: int = 5,
) -> list[dict]:
    """Get top N MPs by specified centrality metric.
    
    Args:
        session_graph: SessionGraph with node metrics
        metric: Metric name ('degree', 'betweenness', 'eigenvector', 'closeness')
        top_n: Number of top MPs to return (default: 5)
        
    Returns:
        List of dicts with node info sorted by metric (descending)
    """
    if not session_graph.nodes:
        return []
    
    # Calculate metric values
    nodes_with_metric = []
    for node in session_graph.nodes:
        if metric == "degree":
            value = node.degree_in + node.degree_out
        elif metric == "betweenness":
            value = node.betweenness
        elif metric == "eigenvector":
            value = node.eigenvector
        elif metric == "closeness":
            value = node.closeness
        else:
            value = 0.0
        
        nodes_with_metric.append({
            "node_id": node.node_id,
            "common_name": node.common_name,
            "party": node.party,
            "value": value,
            "structural_role": node.structural_role,
        })
    
    # Sort by metric value (descending) and take top N
    sorted_nodes = sorted(nodes_with_metric, key=lambda x: x["value"], reverse=True)
    return sorted_nodes[:top_n]


def get_role_badge(role: str) -> str:
    """Get emoji badge for structural role.
    
    Args:
        role: Structural role name
        
    Returns:
        Emoji badge string
    """
    badges = {
        StructuralRole.FORCE_MULTIPLIER.value: "⚡",
        StructuralRole.BRIDGE.value: "🌉",
        StructuralRole.HUB.value: "🎯",
        StructuralRole.ISOLATED.value: "🏝️",
    }
    return badges.get(role, "")


def get_role_label(role: str) -> str:
    """Get human-readable label for structural role.
    
    Args:
        role: Structural role name
        
    Returns:
        Human-readable label
    """
    labels = {
        StructuralRole.FORCE_MULTIPLIER.value: "Force Multiplier",
        StructuralRole.BRIDGE.value: "Bridge",
        StructuralRole.HUB.value: "Hub",
        StructuralRole.ISOLATED.value: "Isolated",
    }
    return labels.get(role, role.replace("_", " ").title())


def render_leaderboard(
    session_graph: SessionGraph,
    on_mp_click: callable | None = None,
) -> None:
    """Render the leaderboard panel with top 5 MPs by each metric.
    
    Implements MP-10 acceptance criteria:
    1. Panel showing Top 5 MPs by: Degree, Betweenness, Eigenvector, Closeness
    2. Updates dynamically based on selected date range / session
    3. Each entry clickable (highlights node in graph)
    4. Structural role badges: Force Multiplier, Bridge, Hub, Isolated
    
    Args:
        session_graph: SessionGraph with node metrics
        on_mp_click: Optional callback when MP is clicked (receives node_id)
    """
    st.subheader("🏆 Leaderboard")
    st.markdown("**Top 5 MPs by Centrality Metric**")
    
    # Metric selector tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Degree",
        "🌉 Betweenness",
        "⚡ Eigenvector",
        "🎯 Closeness",
    ])
    
    # Degree Centrality
    with tab1:
        st.markdown("*Most connected MPs (total in + out degree)*")
        top_degree = get_top_mps_by_metric(session_graph, "degree", top_n=5)
        
        for idx, mp in enumerate(top_degree, start=1):
            # Build role badges
            badges = " ".join([get_role_badge(role) for role in mp["structural_role"]])
            role_labels = ", ".join([get_role_label(role) for role in mp["structural_role"]])
            
            # Display entry
            col1, col2 = st.columns([3, 1])
            with col1:
                if on_mp_click:
                    if st.button(
                        f"#{idx} {mp['common_name']} {badges}",
                        key=f"degree_{mp['node_id']}",
                        help=f"Click to highlight in graph. Roles: {role_labels}",
                    ):
                        on_mp_click(mp["node_id"])
                else:
                    st.markdown(f"**#{idx}** {mp['common_name']} {badges}")
            with col2:
                st.metric("", f"{int(mp['value'])}")
        
        if not top_degree:
            st.info("No data available for this session.")
    
    # Betweenness Centrality
    with tab2:
        st.markdown("*MPs who bridge different groups*")
        top_betweenness = get_top_mps_by_metric(session_graph, "betweenness", top_n=5)
        
        for idx, mp in enumerate(top_betweenness, start=1):
            badges = " ".join([get_role_badge(role) for role in mp["structural_role"]])
            role_labels = ", ".join([get_role_label(role) for role in mp["structural_role"]])
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if on_mp_click:
                    if st.button(
                        f"#{idx} {mp['common_name']} {badges}",
                        key=f"betweenness_{mp['node_id']}",
                        help=f"Click to highlight in graph. Roles: {role_labels}",
                    ):
                        on_mp_click(mp["node_id"])
                else:
                    st.markdown(f"**#{idx}** {mp['common_name']} {badges}")
            with col2:
                st.metric("", f"{mp['value']:.3f}")
        
        if not top_betweenness:
            st.info("No data available for this session.")
    
    # Eigenvector Centrality
    with tab3:
        st.markdown("*Most influential MPs (connected to other influential MPs)*")
        top_eigenvector = get_top_mps_by_metric(session_graph, "eigenvector", top_n=5)
        
        for idx, mp in enumerate(top_eigenvector, start=1):
            badges = " ".join([get_role_badge(role) for role in mp["structural_role"]])
            role_labels = ", ".join([get_role_label(role) for role in mp["structural_role"]])
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if on_mp_click:
                    if st.button(
                        f"#{idx} {mp['common_name']} {badges}",
                        key=f"eigenvector_{mp['node_id']}",
                        help=f"Click to highlight in graph. Roles: {role_labels}",
                    ):
                        on_mp_click(mp["node_id"])
                else:
                    st.markdown(f"**#{idx}** {mp['common_name']} {badges}")
            with col2:
                st.metric("", f"{mp['value']:.3f}")
        
        if not top_eigenvector:
            st.info("No data available for this session.")
    
    # Closeness Centrality
    with tab4:
        st.markdown("*MPs with shortest paths to all others*")
        top_closeness = get_top_mps_by_metric(session_graph, "closeness", top_n=5)
        
        for idx, mp in enumerate(top_closeness, start=1):
            badges = " ".join([get_role_badge(role) for role in mp["structural_role"]])
            role_labels = ", ".join([get_role_label(role) for role in mp["structural_role"]])
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if on_mp_click:
                    if st.button(
                        f"#{idx} {mp['common_name']} {badges}",
                        key=f"closeness_{mp['node_id']}",
                        help=f"Click to highlight in graph. Roles: {role_labels}",
                    ):
                        on_mp_click(mp["node_id"])
                else:
                    st.markdown(f"**#{idx}** {mp['common_name']} {badges}")
            with col2:
                st.metric("", f"{mp['value']:.3f}")
        
        if not top_closeness:
            st.info("No data available for this session.")


def render_leaderboard_compact(
    session_graph: SessionGraph,
    metric: str = "degree",
    top_n: int = 5,
) -> None:
    """Render a compact single-metric leaderboard.
    
    Args:
        session_graph: SessionGraph with node metrics
        metric: Metric name ('degree', 'betweenness', 'eigenvector', 'closeness')
        top_n: Number of top MPs to display (default: 5)
    """
    top_mps = get_top_mps_by_metric(session_graph, metric, top_n=top_n)
    
    if not top_mps:
        st.info("No data available.")
        return
    
    for idx, mp in enumerate(top_mps, start=1):
        badges = " ".join([get_role_badge(role) for role in mp["structural_role"]])
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**#{idx}** {mp['common_name']} {badges}")
        with col2:
            if metric == "degree":
                st.text(f"{int(mp['value'])}")
            else:
                st.text(f"{mp['value']:.3f}")
