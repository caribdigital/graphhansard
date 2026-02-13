# Dashboard Features Guide

This guide covers the three major dashboard views introduced in GraphHansard: the Leaderboard, Session Timeline, and MP Report Card.

## Overview

GraphHansard's dashboard provides three main views for exploring parliamentary network data:

1. **Graph Explorer** (with Leaderboard) — Interactive graph visualization with real-time leaderboard
2. **Session Timeline** — Temporal exploration of sessions with date-based navigation
3. **MP Report Card** — Individual MP network position analysis over time

## MP-10: Leaderboard Panel

The Leaderboard displays the top 5 MPs by each centrality metric for the selected session or time range.

### Features

- **Top 5 Rankings** for four centrality metrics:
  - 📊 **Degree Centrality** — Most connected MPs (total in + out degree)
  - 🌉 **Betweenness Centrality** — MPs who bridge different groups
  - ⚡ **Eigenvector Centrality** — Most influential MPs (connected to other influential MPs)
  - 🎯 **Closeness Centrality** — MPs with shortest paths to all others

- **Structural Role Badges**:
  - ⚡ **Force Multiplier** — High eigenvector centrality
  - 🌉 **Bridge** — High betweenness centrality
  - 🎯 **Hub** — High in-degree
  - 🏝️ **Isolated** — No connections

- **Interactive Elements**:
  - Click any MP name to highlight them in the graph
  - Hover over badges to see role descriptions
  - Updates dynamically based on selected session

### Usage

```python
from graphhansard.dashboard.leaderboard import render_leaderboard

# Render full leaderboard with tabs
render_leaderboard(session_graph, on_mp_click=callback_function)

# Render compact single-metric view
from graphhansard.dashboard.leaderboard import render_leaderboard_compact
render_leaderboard_compact(session_graph, metric="degree", top_n=5)
```

### Example Output

```
🏆 Leaderboard
Top 5 MPs by Centrality Metric

📊 Degree
#1 Brave Davis ⚡🎯     8
#2 Chester Cooper       4
#3 Michael Pintard      2
```

## MP-12: Session Timeline View

The Session Timeline provides horizontal temporal navigation of parliamentary sessions.

### Features

- **Horizontal Timeline** showing all available sessions by date
- **Visual Indicators**:
  - ✅ Green checkmark — Data available
  - ⏳ Hourglass — Pending processing
- **Navigation Controls**:
  - ◀️ Previous button — Navigate to older session
  - Next ▶️ button — Navigate to newer session
  - Direct session selection — Click any session button
- **Auto-loading** — Selected session graph loads automatically

### Usage

```python
from graphhansard.dashboard.timeline import discover_sessions, render_timeline

# Discover available sessions
sessions = discover_sessions(
    sessions_dir="output",
    graphs_dir="graphs/sessions",
)

# Render timeline with selection callback
def on_session_select(session_info):
    print(f"Selected: {session_info.display_date}")

selected_session = render_timeline(
    sessions=sessions,
    selected_session=current_session,
    on_session_select=on_session_select,
)
```

### Session Discovery

The timeline automatically discovers sessions from:
- `output/*.json` files (session metrics)
- `graphs/sessions/*.graphml` files (graph exports)

Sessions are sorted by date (most recent first) and deduplicated by session ID.

### Navigation

```python
from graphhansard.dashboard.timeline import get_session_navigation

# Get adjacent sessions
prev_session, next_session = get_session_navigation(sessions, current_session)
```

## MP-13: MP Report Card Page

The MP Report Card provides comprehensive network analysis for individual MPs across multiple sessions.

### Features

1. **Centrality Metrics Over Time** — Line charts showing:
   - Degree centrality evolution
   - Betweenness centrality evolution
   - Eigenvector centrality evolution
   - Closeness centrality evolution

2. **Top Interaction Partners** — Ranked list of MPs most frequently mentioned or mentioned by

3. **Sentiment Trend** — Average net sentiment over time with trend analysis

4. **Structural Role Evolution** — Timeline of role changes across sessions

5. **Shareable URLs** — Direct links to MP report cards for external sharing

### Usage

#### Building a Report Card

```python
from graphhansard.dashboard.mp_report_card import build_report_card

# Build report card from multiple sessions
report_card = build_report_card(
    mp_id="mp_davis_brave",
    session_graphs=[session1, session2, session3],
)
```

#### Rendering a Report Card

```python
from graphhansard.dashboard.mp_report_card import render_report_card

# Render full report card page
render_report_card(report_card, mp_registry=registry)
```

#### Shareable URLs

Report cards can be accessed directly via URL parameters:

```
http://localhost:8501/?mp_id=mp_davis_brave
```

This is useful for:
- 📰 Journalists linking to specific MP analysis
- 🏛️ Civic organizations tracking representatives
- 📊 Researchers sharing specific data points

### Report Card Components

#### 1. Overview Section
- MP name and ID
- Shareable URL
- Number of sessions analyzed

#### 2. Metrics Over Time
Line charts showing each centrality metric's evolution:
- X-axis: Session dates
- Y-axis: Metric values
- Supports pandas for enhanced visualization

#### 3. Top Interaction Partners
Ranked table showing:
- Partner name and party
- Total mentions across all sessions
- Top 10 partners displayed

#### 4. Sentiment Trend
Line chart and summary statistics:
- Average net sentiment per session
- Overall average
- Trend classification (Positive/Neutral/Negative)

#### 5. Structural Role Evolution
Timeline showing roles across sessions:
- Date and role assignments
- Visual indicators for role changes
- Empty sessions noted

#### 6. Summary Statistics
Aggregate metrics:
- Average in-degree
- Average out-degree
- Average betweenness
- Average eigenvector

## Dashboard Navigation

### View Selection

Use the sidebar to switch between views:

```
Navigation
○ Graph Explorer      # Main graph with leaderboard
○ Session Timeline    # Temporal session browser
○ MP Report Card      # Individual MP analysis
```

### Graph Controls

Common controls available in all views:
- **Node Size Metric** — Choose sizing metric
- **Party Colors** — Toggle FNM blue/red
- **Graph Type** — Sample or Timeline sessions

## Integration Example

Complete workflow integrating all three features:

```python
import streamlit as st
from graphhansard.dashboard.leaderboard import render_leaderboard
from graphhansard.dashboard.timeline import discover_sessions, render_timeline
from graphhansard.dashboard.mp_report_card import build_report_card, render_report_card

# 1. Discover sessions
sessions = discover_sessions()

# 2. Render timeline for selection
selected_session = render_timeline(sessions)

# 3. Load selected session graph
session_graph = load_session_data(selected_session)

# 4. Render graph with leaderboard
col_graph, col_leaderboard = st.columns([3, 1])

with col_graph:
    render_graph(session_graph)

with col_leaderboard:
    render_leaderboard(session_graph)

# 5. Link to MP report cards
if st.button("View Report Card"):
    report_card = build_report_card(selected_mp_id, [session_graph])
    render_report_card(report_card)
```

## Best Practices

### For Leaderboard
- Use in sidebar or secondary column for space efficiency
- Provide click callbacks to integrate with graph highlighting
- Consider compact view for limited screen space

### For Timeline
- Auto-select most recent session on initial load
- Cache session discovery results for performance
- Show loading indicators during graph rendering

### For Report Cards
- Pre-generate reports for all MPs in batch processing
- Cache report card data to reduce computation
- Provide export options (PDF, CSV) for external use
- Include data freshness indicators

## Performance Considerations

### Leaderboard
- O(n log n) sorting for top-k selection
- Minimal memory footprint
- Real-time updates on session change

### Timeline
- O(n) session discovery on directory scan
- Consider pagination for >100 sessions
- Cache session metadata

### Report Card
- O(s × e) where s = sessions, e = edges per session
- Consider lazy loading for line charts
- Pre-aggregate common queries

## API Reference

### Leaderboard Module

```python
# Get top MPs by metric
get_top_mps_by_metric(session_graph, metric, top_n=5)
# Returns: list[dict] with node_id, common_name, party, value, structural_role

# Get role badge emoji
get_role_badge(role: str) -> str

# Get role human-readable label
get_role_label(role: str) -> str

# Render full leaderboard
render_leaderboard(session_graph, on_mp_click=None)

# Render compact leaderboard
render_leaderboard_compact(session_graph, metric, top_n=5)
```

### Timeline Module

```python
# Session info class
SessionInfo(session_id, date, has_data=False, file_path=None)

# Discover sessions
discover_sessions(sessions_dir="output", graphs_dir="graphs/sessions")
# Returns: list[SessionInfo]

# Render timeline
render_timeline(sessions, selected_session=None, on_session_select=None)
# Returns: SessionInfo | None

# Get navigation sessions
get_session_navigation(sessions, current_session)
# Returns: (previous_session, next_session)

# Load session data
load_session_data(session: SessionInfo)
# Returns: dict | None
```

### Report Card Module

```python
# Report card class
MPReportCard(mp_id, mp_name)

# Build report card
build_report_card(mp_id, session_graphs)
# Returns: MPReportCard | None

# Render report card
render_report_card(report_card, mp_registry=None)

# Get all MPs
get_mp_list(session_graphs)
# Returns: list[dict]

# Render MP selector
render_mp_selector(session_graphs)
# Returns: str | None (selected mp_id)
```

## Testing

Run tests for all components:

```bash
pytest tests/test_leaderboard.py -v
pytest tests/test_timeline.py -v
pytest tests/test_mp_report_card.py -v
```

Coverage includes:
- ✅ Top MP selection by all metrics
- ✅ Role badge and label mapping
- ✅ Session discovery and navigation
- ✅ Report card data aggregation
- ✅ MP list generation and deduplication

## Troubleshooting

### Leaderboard not showing
- Verify session_graph has nodes
- Check that metrics are computed (not all zeros)
- Ensure structural roles are assigned

### Timeline empty
- Run `python examples/build_session_graph.py` to generate sample data
- Check `output/` and `graphs/sessions/` directories exist
- Verify JSON files are valid SessionGraph format

### Report card error
- Ensure MP exists in provided sessions
- Check session_graphs list is not empty
- Verify MP ID matches node_id format

### Charts not rendering
- Install pandas: `pip install pandas`
- Check data format (lists of dicts with 'date' keys)
- Verify Streamlit version >= 1.0

## Future Enhancements

Planned improvements:
- [ ] Export leaderboard as CSV/PNG
- [ ] Timeline zoom controls for large date ranges
- [ ] Report card comparison mode (multiple MPs)
- [ ] Real-time updates with session streaming
- [ ] Advanced filtering (party, role, date range)

## References

- SRD §9.2 (MP-10, MP-12, MP-13) — Requirements specification
- SRD §15 (Milestones M-3.2, M-4.3) — Implementation timeline
- `examples/build_session_graph.py` — Sample data generation
- `tests/test_*.py` — Component test suites
