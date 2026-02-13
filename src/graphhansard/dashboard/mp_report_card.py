"""MP Report Card page for GraphHansard dashboard.

Implements MP-13: Dedicated page per MP summarising network position over time.

See SRD §9.2 (MP-13) for specification.
"""

from __future__ import annotations

from typing import Any
import streamlit as st
from graphhansard.brain.graph_builder import SessionGraph, NodeMetrics


class MPReportCard:
    """Report card data for a single MP across multiple sessions."""
    
    def __init__(self, mp_id: str, mp_name: str):
        """Initialize MP report card.
        
        Args:
            mp_id: MP node ID
            mp_name: MP common name
        """
        self.mp_id = mp_id
        self.mp_name = mp_name
        self.sessions: list[dict] = []
        self.interaction_partners: dict[str, int] = {}  # partner_id -> total_mentions
        self.sentiment_trends: list[dict] = []  # [{date, net_sentiment}, ...]
        self.role_evolution: list[dict] = []  # [{date, roles}, ...]
    
    def add_session_data(
        self,
        session_id: str,
        date: str,
        metrics: NodeMetrics,
        edges: list[dict],
    ) -> None:
        """Add session data for this MP.
        
        Args:
            session_id: Session identifier
            date: Session date
            metrics: NodeMetrics for this MP in this session
            edges: List of edge dicts involving this MP
        """
        # Add session metrics
        self.sessions.append({
            "session_id": session_id,
            "date": date,
            "degree_in": metrics.degree_in,
            "degree_out": metrics.degree_out,
            "betweenness": metrics.betweenness,
            "eigenvector": metrics.eigenvector,
            "closeness": metrics.closeness,
            "structural_role": metrics.structural_role,
        })
        
        # Update interaction partners
        for edge in edges:
            if edge.source_node_id == self.mp_id:
                partner = edge.target_node_id
            elif edge.target_node_id == self.mp_id:
                partner = edge.source_node_id
            else:
                continue
            
            self.interaction_partners[partner] = (
                self.interaction_partners.get(partner, 0) + edge.total_mentions
            )
        
        # Track sentiment trend
        net_sentiment = 0.0
        total_edges = 0
        for edge in edges:
            if edge.source_node_id == self.mp_id or edge.target_node_id == self.mp_id:
                net_sentiment += edge.net_sentiment
                total_edges += 1
        
        avg_sentiment = net_sentiment / total_edges if total_edges > 0 else 0.0
        self.sentiment_trends.append({
            "date": date,
            "net_sentiment": avg_sentiment,
        })
        
        # Track role evolution
        self.role_evolution.append({
            "date": date,
            "roles": metrics.structural_role,
        })
    
    def get_top_partners(self, top_n: int = 5, mp_registry: dict | None = None) -> list[dict]:
        """Get top interaction partners.
        
        Args:
            top_n: Number of top partners to return
            mp_registry: Optional dict mapping node_id to (common_name, party)
            
        Returns:
            List of dicts with partner info sorted by total mentions
        """
        sorted_partners = sorted(
            self.interaction_partners.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        result = []
        for partner_id, mentions in sorted_partners[:top_n]:
            name = partner_id
            party = "Unknown"
            
            if mp_registry and partner_id in mp_registry:
                name, party = mp_registry[partner_id]
            
            result.append({
                "partner_id": partner_id,
                "name": name,
                "party": party,
                "total_mentions": mentions,
            })
        
        return result


def build_report_card(
    mp_id: str,
    session_graphs: list[SessionGraph],
) -> MPReportCard | None:
    """Build report card for an MP across multiple sessions.
    
    Args:
        mp_id: MP node ID
        session_graphs: List of SessionGraph objects
        
    Returns:
        MPReportCard or None if MP not found
    """
    if not session_graphs:
        return None
    
    # Find MP name from first session where they appear
    mp_name = mp_id
    for session in session_graphs:
        for node in session.nodes:
            if node.node_id == mp_id:
                mp_name = node.common_name
                break
        if mp_name != mp_id:
            break
    
    report_card = MPReportCard(mp_id, mp_name)
    
    # Aggregate data across sessions
    for session in session_graphs:
        # Find MP's metrics in this session
        mp_metrics = None
        for node in session.nodes:
            if node.node_id == mp_id:
                mp_metrics = node
                break
        
        if mp_metrics is None:
            continue  # MP not present in this session
        
        # Find edges involving this MP
        mp_edges = [
            edge for edge in session.edges
            if edge.source_node_id == mp_id or edge.target_node_id == mp_id
        ]
        
        report_card.add_session_data(
            session_id=session.session_id,
            date=session.date,
            metrics=mp_metrics,
            edges=mp_edges,
        )
    
    return report_card if report_card.sessions else None


def render_report_card(
    report_card: MPReportCard,
    mp_registry: dict | None = None,
) -> None:
    """Render MP Report Card page.
    
    Implements MP-13 acceptance criteria:
    1. Dedicated page per MP (accessible via URL or node click)
    2. Shows: centrality metrics over time (line chart), top interaction partners, sentiment trend
    3. Structural role evolution across sessions
    4. Shareable URL (for journalists, civic organizations)
    
    Args:
        report_card: MPReportCard with aggregated data
        mp_registry: Optional dict mapping node_id to (common_name, party)
    """
    st.title(f"📊 MP Report Card: {report_card.mp_name}")
    st.markdown(f"**MP ID:** `{report_card.mp_id}`")
    
    # Shareable URL info
    current_url = f"?mp_id={report_card.mp_id}"
    st.info(f"🔗 **Shareable URL:** Add `{current_url}` to the dashboard URL to link directly to this report card.")
    
    if not report_card.sessions:
        st.warning("No session data available for this MP.")
        return
    
    st.markdown(f"**Sessions analyzed:** {len(report_card.sessions)}")
    st.markdown("---")
    
    # Section 1: Centrality Metrics Over Time
    st.subheader("📈 Centrality Metrics Over Time")
    
    try:
        import pandas as pd
        
        # Prepare data for chart
        metrics_df = pd.DataFrame(report_card.sessions)
        metrics_df["total_degree"] = metrics_df["degree_in"] + metrics_df["degree_out"]
        
        # Display line charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Degree Centrality**")
            st.line_chart(metrics_df[["date", "total_degree"]].set_index("date"))
            
            st.markdown("**Betweenness Centrality**")
            st.line_chart(metrics_df[["date", "betweenness"]].set_index("date"))
        
        with col2:
            st.markdown("**Eigenvector Centrality**")
            st.line_chart(metrics_df[["date", "eigenvector"]].set_index("date"))
            
            st.markdown("**Closeness Centrality**")
            st.line_chart(metrics_df[["date", "closeness"]].set_index("date"))
    
    except ImportError:
        # Fallback without pandas/charts
        st.warning("Install pandas for visualization: `pip install pandas`")
        
        # Display as table
        st.dataframe(report_card.sessions)
    
    st.markdown("---")
    
    # Section 2: Top Interaction Partners
    st.subheader("🤝 Top Interaction Partners")
    
    top_partners = report_card.get_top_partners(top_n=10, mp_registry=mp_registry)
    
    if top_partners:
        for idx, partner in enumerate(top_partners, start=1):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**#{idx}** {partner['name']}")
            with col2:
                st.text(partner['party'])
            with col3:
                st.metric("Mentions", partner['total_mentions'])
    else:
        st.info("No interaction partners found.")
    
    st.markdown("---")
    
    # Section 3: Sentiment Trend
    st.subheader("💭 Sentiment Trend")
    
    if report_card.sentiment_trends:
        try:
            import pandas as pd
            
            sentiment_df = pd.DataFrame(report_card.sentiment_trends)
            st.line_chart(sentiment_df.set_index("date"))
            
            # Summary stats
            avg_sentiment = sum(s["net_sentiment"] for s in report_card.sentiment_trends) / len(report_card.sentiment_trends)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Average Net Sentiment", f"{avg_sentiment:+.3f}")
            with col2:
                trend = "Positive" if avg_sentiment > 0.1 else "Negative" if avg_sentiment < -0.1 else "Neutral"
                st.metric("Overall Trend", trend)
        
        except ImportError:
            st.warning("Install pandas for visualization.")
            st.dataframe(report_card.sentiment_trends)
    else:
        st.info("No sentiment data available.")
    
    st.markdown("---")
    
    # Section 4: Structural Role Evolution
    st.subheader("🎭 Structural Role Evolution")
    
    if report_card.role_evolution:
        st.markdown("**Roles across sessions:**")
        
        for session_roles in report_card.role_evolution:
            date = session_roles["date"]
            roles = session_roles["roles"]
            
            if roles:
                role_labels = ", ".join([r.replace("_", " ").title() for r in roles])
                st.markdown(f"- **{date}**: {role_labels}")
            else:
                st.markdown(f"- **{date}**: No special roles")
    else:
        st.info("No role evolution data available.")
    
    st.markdown("---")
    
    # Summary statistics
    st.subheader("📊 Summary Statistics")
    
    if report_card.sessions:
        # Calculate averages
        avg_degree_in = sum(s["degree_in"] for s in report_card.sessions) / len(report_card.sessions)
        avg_degree_out = sum(s["degree_out"] for s in report_card.sessions) / len(report_card.sessions)
        avg_betweenness = sum(s["betweenness"] for s in report_card.sessions) / len(report_card.sessions)
        avg_eigenvector = sum(s["eigenvector"] for s in report_card.sessions) / len(report_card.sessions)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Avg. In-Degree", f"{avg_degree_in:.1f}")
        with col2:
            st.metric("Avg. Out-Degree", f"{avg_degree_out:.1f}")
        with col3:
            st.metric("Avg. Betweenness", f"{avg_betweenness:.3f}")
        with col4:
            st.metric("Avg. Eigenvector", f"{avg_eigenvector:.3f}")


def get_mp_list(session_graphs: list[SessionGraph]) -> list[dict]:
    """Get list of all MPs across sessions.
    
    Args:
        session_graphs: List of SessionGraph objects
        
    Returns:
        List of dicts with MP info (deduplicated)
    """
    mps = {}
    
    for session in session_graphs:
        for node in session.nodes:
            if node.node_id not in mps:
                mps[node.node_id] = {
                    "node_id": node.node_id,
                    "common_name": node.common_name,
                    "party": node.party,
                }
    
    return sorted(mps.values(), key=lambda x: x["common_name"])


def render_mp_selector(session_graphs: list[SessionGraph]) -> str | None:
    """Render MP selector dropdown.
    
    Args:
        session_graphs: List of SessionGraph objects
        
    Returns:
        Selected MP node_id or None
    """
    mps = get_mp_list(session_graphs)
    
    if not mps:
        st.warning("No MPs found in session data.")
        return None
    
    # Create display options
    options = [f"{mp['common_name']} ({mp['party']})" for mp in mps]
    
    selected_idx = st.selectbox(
        "Select MP",
        range(len(options)),
        format_func=lambda i: options[i],
        key="mp_selector",
    )
    
    return mps[selected_idx]["node_id"] if selected_idx is not None else None
