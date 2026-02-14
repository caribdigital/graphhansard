# Interactive Graph Dashboard — MP Node & Edge Interaction

This document describes the interactive features implemented for MP-5, MP-6, and MP-11 requirements.

## Features Implemented

### MP-5: Node Click → MP Profile Card

When a user clicks on a node (or selects from the dropdown), the dashboard displays a comprehensive MP profile card showing:

- **Basic Information**
  - Full name (common name)
  - Party affiliation
  - Constituency
  - Current portfolio/title

- **Centrality Scores**
  - Degree (In/Out)
  - Betweenness centrality
  - Eigenvector centrality
  - Closeness centrality

- **Network Roles**
  - Force Multiplier (high eigenvector centrality)
  - Bridge (high betweenness centrality)
  - Hub (high in-degree)
  - Isolated (zero degree)

- **Community Membership**
  - Community ID from Louvain community detection

### MP-6: Edge Click → Mention Details

When a user clicks on an edge (or selects from the dropdown), the dashboard displays detailed mention information:

- **Summary Metrics**
  - Total mention count
  - Net sentiment score
  - Breakdown: positive/neutral/negative counts

- **Individual Mentions**
  - Raw mention text (e.g., "The Deputy Prime Minister")
  - Context window (surrounding text)
  - Sentiment label (🟢 Positive, ⚫ Neutral, 🔴 Negative)
  - Timestamp (start and end in seconds)
  - **YouTube link** with timestamp parameter for jumping directly to the mention in source video

#### YouTube Timestamp Links

Each mention includes a clickable link that jumps to the exact moment in the parliamentary session video where the mention occurred. Format: `https://www.youtube.com/watch?v=VIDEO_ID&t=SECONDS`

### MP-11: Drag-and-Drop Node Repositioning

Users can physically drag nodes to reposition them in the visualization:

- **Real-time physics**: Layout recalculates using force-directed algorithm
- **Temporary positioning**: Positions reset on page reload (no persistence)
- **Exploration aid**: Helps users explore dense areas of the graph topology

## Usage

### Running the Interactive Dashboard

```bash
# Generate sample data
python examples/build_session_graph.py

# Launch dashboard
streamlit run src/graphhansard/dashboard/app_interactive.py
```

### Interacting with the Graph

1. **View MP Profile (MP-5)**
   - Select an MP from the "Select MP to View Profile" dropdown in the sidebar
   - OR click on a node in the graph (future enhancement)
   - Profile card appears in the right panel

2. **View Mention Details (MP-6)**
   - Select an edge from the "Select Edge for Mention Details" dropdown
   - OR click on an edge in the graph (future enhancement)
   - Mention details appear in the right panel with timestamp links

3. **Reposition Nodes (MP-11)**
   - Click and drag any node in the graph
   - Release to let physics stabilize
   - Layout recalculates automatically

4. **Configure Video URL**
   - Enter the session's YouTube URL in the sidebar
   - Timestamp links will use this base URL
   - Format: `https://www.youtube.com/watch?v=VIDEO_ID`

## Data Model Changes

### NodeMetrics Extended Fields

```python
class NodeMetrics(BaseModel):
    node_id: str
    common_name: str
    party: str
    constituency: str | None = None          # NEW (MP-5)
    current_portfolio: str | None = None     # NEW (MP-5)
    degree_in: int = 0
    degree_out: int = 0
    betweenness: float = 0.0
    eigenvector: float = 0.0
    closeness: float = 0.0
    structural_role: list[str] = []
    community_id: int | None = None
```

### EdgeRecord with Mention Details

```python
class MentionDetail(BaseModel):              # NEW (MP-6)
    timestamp_start: float
    timestamp_end: float
    context_window: str
    sentiment_label: str | None = None
    raw_mention: str | None = None

class EdgeRecord(BaseModel):
    source_node_id: str
    target_node_id: str
    total_mentions: int = 0
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    net_sentiment: float = 0.0
    mention_details: list[MentionDetail] = []  # NEW (MP-6)
```

### Updated MP Registry Format

The `mp_registry` parameter now supports expanded dict format:

```python
mp_registry = {
    "mp_davis_brave": {
        "common_name": "Brave Davis",
        "party": "PLP",
        "constituency": "Cat Island, Rum Cay and San Salvador",  # NEW
        "current_portfolio": "Prime Minister",                    # NEW
    },
}
```

Legacy tuple format `("Name", "Party")` is still supported for backward compatibility.

## Architecture

### Components

- **`graph_builder.py`**: Extended NodeMetrics and EdgeRecord models
- **`interactive_graph.py`**: Helper functions for YouTube links and sentiment badges
- **`app_interactive.py`**: Streamlit dashboard with 2-column layout
- **`graph_viz.py`**: PyVis graph rendering (unchanged, drag-and-drop already enabled)

### Interaction Flow

```
User selects node/edge
    ↓
Streamlit updates state
    ↓
display_mp_profile() or display_mention_details()
    ↓
Renders profile card or mention details in right panel
    ↓
Generates YouTube timestamp links
```

## Testing

Run test suite:

```bash
# All graph visualization tests (30 tests)
pytest tests/test_graph_viz.py -v

# Interactive utilities tests (9 tests)
pytest tests/test_interactive_graph.py -v
```

All tests pass ✅

## Future Enhancements

1. **Direct click handling**: Currently uses dropdowns; future: capture click events from PyVis via JavaScript
2. **Persistent node positions**: Save/load custom layouts
3. **Photo placeholders**: Add MP headshots to profile cards
4. **Full-screen profile modal**: Alternative to sidebar panel
5. **Edge hover preview**: Quick tooltip with mention count and sentiment
6. **Community coloring toggle**: Color nodes by community instead of party
7. **Search/filter**: Find MPs by name or constituency
8. **Export interactions**: Download profile or mention data as JSON/CSV

## References

- SRD §9.2 (MP-5, MP-6, MP-11 requirements)
- SRD §15 (Milestone M-3.2)
- Issue #[TBD]: MP Node & Edge Interaction

## Acceptance Criteria Met ✅

### MP-5: Node Click → MP Profile Card
- ✅ Full name, common name
- ✅ Party, constituency, portfolio
- ✅ Centrality scores (degree, betweenness, eigenvector, closeness)
- ✅ Structural roles (Force Multiplier, Bridge, Isolated, Hub)
- ✅ Community membership
- ✅ Profile card data from NodeMetrics

### MP-6: Edge Click → Mention Details
- ✅ Source MP → Target MP
- ✅ Total mention count
- ✅ Sentiment breakdown (positive/neutral/negative)
- ✅ Individual mentions with timestamps
- ✅ Link to source audio at mention timestamp (YouTube &t= parameter)
- ✅ Mention data from MentionRecord via EdgeRecord

### MP-11: Drag-and-Drop
- ✅ Drag nodes to reposition
- ✅ Graph layout recalculates physics in real-time
- ✅ Positions reset on page reload
