"""Streamlit dashboard entry point.

Run with: streamlit run src/graphhansard/dashboard/app.py

See SRD §9 (Layer 3 — The Map) for specification.
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from rapidfuzz import fuzz

from graphhansard.brain.graph_builder import SessionGraph
from graphhansard.dashboard.graph_viz import build_force_directed_graph
from graphhansard.dashboard.leaderboard import render_leaderboard
from graphhansard.dashboard.mp_report_card import (
    build_report_card,
    render_mp_selector,
    render_report_card,
)
from graphhansard.dashboard.timeline import (
    discover_sessions,
    load_session_data,
    render_timeline,
)

# Configuration constants
FUZZY_MATCH_THRESHOLD = 75  # Minimum fuzzy matching score (0-100)
GOLDEN_RECORD_PATH = "golden_record/mps.json"  # Relative to project root


@st.cache_data(ttl=3600)  # Cache for 1 hour (MP-14: Performance)
def load_sample_graph() -> SessionGraph | None:
    """Load sample session graph if available.
    
    Cached to improve load times per MP-14 requirement.
    """
    sample_path = Path("output/sample_session_metrics.json")
    if sample_path.exists():
        with open(sample_path, "r") as f:
            data = json.load(f)
            return SessionGraph(**data)
    return None


@st.cache_data(ttl=3600)  # Cache for 1 hour (MP-14: Performance)
def load_golden_record() -> dict:
    """Load Golden Record for MP search and alias resolution.
    
    Cached to improve load times per MP-14 requirement.
    """
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
    """Launch the GraphHansard interactive dashboard.
    
    Performance targets (MP-14):
    - Initial load time: ≤3 seconds on 50 Mbps connection
    - Graph interaction latency: ≤100ms (drag, zoom, pan)
    - Single-session graph: 39 nodes, ~100 edges
    
    Responsiveness targets (MP-15):
    - Full functionality: Desktop (1200px+) and Tablet (768px+)
    - Graceful degradation: Mobile (<768px)
    - Touch interactions: Pinch-to-zoom, pan, drag
    """
    st.set_page_config(
        page_title="GraphHansard — Bahamian Parliamentary Network",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",  # MP-15: Better mobile experience
    )

    # MP-15: Add responsive CSS for tablet and mobile support
    st.markdown("""
    <style>
    /* Responsive design for MP-15 */
    @media (max-width: 768px) {
        /* Mobile: Stack elements vertically */
        .stApp {
            max-width: 100vw;
            overflow-x: hidden;
        }
        .block-container {
            padding: 1rem;
        }
        /* Make graphs scrollable on mobile */
        iframe {
            max-width: 100%;
        }
    }
    
    @media (min-width: 768px) and (max-width: 1200px) {
        /* Tablet: Optimize layout */
        .block-container {
            padding: 2rem;
        }
    }
    
    @media (min-width: 1200px) {
        /* Desktop: Full layout */
        .block-container {
            padding: 3rem;
        }
    }
    
    /* Prevent horizontal scrolling (MP-15) */
    .main {
        overflow-x: hidden;
    }
    
    /* Touch-friendly controls (MP-15) */
    .stButton > button {
        min-height: 44px;
        min-width: 44px;
    }
    
    /* Performance: Reduce animations on low-end devices (MP-14) */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    /* Loading optimization (MP-14) */
    .stSpinner {
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

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

    # NF-18: Disclaimer
    st.info(
        "ℹ️ **Disclaimer:** Network metrics are descriptive statistics derived from parliamentary proceedings. "
        "They do not imply wrongdoing, incompetence, or endorsement. See the About page for methodology and limitations."
    )

    # Load Golden Record for search functionality
    golden_record = load_golden_record()

    # Sidebar controls
    st.sidebar.header("Navigation")

    # View selector
    view_mode = st.sidebar.radio(
        "Dashboard View",
        options=["Graph Explorer", "Session Timeline", "MP Report Card", "About"],
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

    # === VIEW MODE: ABOUT (NF-17) ===
    if view_mode == "About":
        st.markdown("---")
        st.header("📖 About GraphHansard")

        st.markdown("""
        ## What is GraphHansard?
        
        GraphHansard is an open-source civic technology platform that applies computational sociology 
        and graph theory to the proceedings of the Bahamian House of Assembly. We transform 
        parliamentary speech into data, revealing the structure of political influence through 
        network analysis.
        
        ### What We Do
        
        We analyze public parliamentary audio to create an interactive **Political Interaction Network** 
        that shows:
        - **Who mentions whom** during parliamentary debate
        - **How often** these interactions occur
        - **The tone** of these interactions (positive, neutral, negative)
        - **Structural roles** of MPs within the debate network
        
        ### How Data is Collected
        
        Our system follows a five-step process:
        
        1. **Audio Download**: We download publicly available parliamentary session recordings from YouTube
        2. **Transcription**: We convert speech to text using AI models (OpenAI Whisper)
        3. **Speaker Identification**: We identify which MP is speaking using our Golden Record database
        4. **Mention Extraction**: We detect when one MP mentions another MP in their speech
        5. **Network Analysis**: We build a graph and compute centrality metrics
        
        For a detailed technical explanation, see our [**Full Methodology Documentation**](https://github.com/caribdigital/graphhansard/blob/main/docs/methodology.md).
        
        ### Our Principles
        
        1. **Open Data**: All source audio is from publicly available parliamentary recordings
        2. **Open Code**: The entire codebase is MIT-licensed on GitHub
        3. **Open Methodology**: We transparently document how the system works
        4. **Neutral Framing**: We present data and metrics, not editorial conclusions
        
        ## Methodology & Limitations
        
        For a complete explanation of how GraphHansard works in plain language, please read:
        
        📄 **[Full Methodology Documentation](https://github.com/caribdigital/graphhansard/blob/main/docs/methodology.md)**
        
        ### Key Limitations
        
        1. **Transcription Accuracy**: Speech-to-text models are not 100% accurate (target: ≤15% error rate)
        2. **Sentiment Analysis**: Models struggle with Bahamian Creole, sarcasm, and parliamentary conventions
        3. **Alias Resolution**: Identifying speakers is probabilistic, with confidence scores
        4. **Audio Quality**: Older or lower-quality recordings reduce accuracy
        5. **Scope**: We only measure public debate, not committee work, constituency service, or private negotiations
        
        ### What We Don't Measure
        
        - Policy positions or voting records
        - MP "effectiveness" or job performance
        - Private influence or backroom negotiations
        - Intent or motivation (only observable patterns)
        
        ## Data Sources
        
        All audio data comes from:
        - Official Bahamian House of Assembly YouTube channel
        - Public parliamentary broadcasts
        
        **We do NOT use:**
        - FOIA requests
        - Leaked documents
        - Private communications
        - Restricted data
        
        📄 **[Data Provenance Documentation](https://github.com/caribdigital/graphhansard/blob/main/docs/data_provenance.md)**
        
        ## Understanding Network Metrics
        
        ### How Metrics Are Computed
        
        We use standard graph theory algorithms from the NetworkX library to calculate these metrics:
        
        ### Degree Centrality
        How many connections an MP has (mentions made + mentions received).
        
        **Computation**: Simply count the edges connected to each MP node.
        
        ### Betweenness Centrality
        How often an MP connects different groups ("bridge" role).
        
        **Computation**: For each pair of MPs, we find the shortest path between them. 
        If an MP appears on many shortest paths, they have high betweenness.
        
        ### Eigenvector Centrality
        Whether an MP is connected to other well-connected MPs ("force multiplier" role).
        
        **Computation**: An iterative algorithm that gives higher scores to MPs who are 
        connected to other high-scoring MPs.
        
        ### Closeness Centrality
        How "close" an MP is to all others in the network.
        
        **Computation**: Calculate the average shortest path length from an MP to all other MPs. 
        Shorter paths mean higher closeness.
        
        **Important**: These are descriptive statistics, not value judgments. There is no "best" 
        centrality score. Context matters.
        
        ## How to Use This Data Responsibly
        
        ### For Citizens
        - Use this tool to explore interaction patterns, but remember that debate participation 
          alone doesn't tell you if your MP is serving your interests
        - Context matters: A backbencher with low centrality might be doing excellent constituency work
        
        ### For Journalists
        - Use this data as a starting point for investigation, not a conclusion
        - Always verify individual claims by listening to the original audio
        - Be cautious about interpreting sentiment scores without listening to context
        
        ### For Researchers
        - This dataset is suitable for aggregate analysis
        - Individual-level claims require validation against ground truth
        - Always cite limitations when publishing findings
        
        ## Contributing
        
        GraphHansard is a community project. You can contribute by:
        - Reporting transcription errors
        - Improving the Golden Record (MP aliases)
        - Contributing to documentation
        - Submitting code improvements
        
        📄 **[Community Contributions Guide](https://github.com/caribdigital/graphhansard/blob/main/docs/community_contributions.md)**
        
        ## License & Attribution
        
        - **Code**: MIT License
        - **Data**: CC-BY-4.0 (attribution required)
        - **Attribution**: GraphHansard / Carib Digital Labs
        
        ## Contact & Support
        
        - **GitHub**: https://github.com/caribdigital/graphhansard
        - **Issues**: https://github.com/caribdigital/graphhansard/issues
        - **Documentation**: https://github.com/caribdigital/graphhansard/tree/main/docs
        
        ## Version Information
        
        - **Platform Version**: 0.1.0
        - **Parliament**: 15th Parliament of The Bahamas
        - **Last Updated**: February 2026
        
        ---
        
        *"The House is in session. The recorder is running. Let's map the noise."*  
        *— Dr. Aris Moncur*
        """)

        return

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

            # Create two columns: main graph and sidebar leaderboard
            col_graph, col_leaderboard = st.columns([3, 1])

            with col_graph:
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

            with col_leaderboard:
                # Render Leaderboard (MP-10)
                def on_mp_click(node_id):
                    st.session_state.highlighted_node = node_id
                    st.info(f"Node highlighted: {node_id}")

                render_leaderboard(filtered_graph, on_mp_click=on_mp_click)

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
