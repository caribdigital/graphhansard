# Force-Directed Graph Visualization Guide

## Overview

The GraphHansard dashboard includes an interactive force-directed graph visualization that displays the political interaction network of the Bahamian House of Assembly. This visualization implements requirements MP-1 through MP-4.

## Features

### MP-1: Force-Directed Layout
- **MPs as nodes**: Each Member of Parliament is represented as a node
- **Mentions as edges**: Directed edges represent references one MP makes to another
- **Interactive physics**: Nodes and edges use force-directed physics for natural layout
- **Pan and zoom**: Fully interactive with mouse/touch controls
- **Hover tooltips**: Detailed information on nodes and edges

### MP-2: Party-Based Color Coding
Nodes are colored by party affiliation:
- **PLP (Progressive Liberal Party)**: Gold `#FFD700`
- **FNM (Free National Movement)**: Red `#DC143C` or Blue `#1E90FF` (user-toggleable)
- **COI (Coalition of Independents)**: Grey `#808080`
- **Unknown**: Silver `#C0C0C0` (fallback)

### MP-3: Metric-Driven Node Sizing
Node size can be dynamically scaled by one of four metrics:

1. **Degree Centrality** (default)
   - Size reflects total connections (in-degree + out-degree)
   - Highlights MPs who are frequently mentioned or mention others

2. **Betweenness Centrality**
   - Size reflects "bridge" role between different groups
   - Highlights MPs who connect otherwise separate communities

3. **Eigenvector Centrality**
   - Size reflects influence through network position
   - Highlights "force multipliers" who are connected to other influential MPs

4. **Total Mentions**
   - Size reflects raw mention count across all interactions
   - Highlights MPs who are most active in parliamentary discourse

### MP-4: Sentiment-Based Edge Styling

**Edge thickness**: Proportional to mention count (1-10px range)
- More mentions = thicker edge
- Visualizes interaction frequency

**Edge color**: Based on net sentiment
- **Green** `#00FF00`: Positive sentiment (net_sentiment > 0.2)
- **Grey** `#808080`: Neutral sentiment (-0.2 ≤ net_sentiment ≤ 0.2)
- **Red** `#FF0000`: Negative sentiment (net_sentiment < -0.2)

Net sentiment formula: `(positive_count - negative_count) / total_mentions`

## Usage

### Running the Dashboard

```bash
# Install dependencies
pip install -e ".[dashboard]"

# Generate sample data (if needed)
python examples/build_session_graph.py

# Launch dashboard
streamlit run src/graphhansard/dashboard/app.py
```

The dashboard will open in your browser at `http://localhost:8501`.

### Controls

**Sidebar Options:**
- **Node Size Metric**: Select which metric to use for node sizing
- **Use Blue for FNM**: Toggle FNM party color between Red and Blue
- **Graph Type**: Select Sample Session, Single Session, or Cumulative (future)

**Graph Interactions:**
- **Pan**: Click and drag the background
- **Zoom**: Mouse wheel or pinch gesture
- **Hover**: Hover over nodes/edges to see details
- **Select**: Click nodes to highlight connections

## Code Examples

### Build a Force-Directed Graph

```python
from graphhansard.brain.graph_builder import SessionGraph
from graphhansard.dashboard.graph_viz import build_force_directed_graph

# Load your SessionGraph
session_graph = SessionGraph(...)

# Build interactive graph
net = build_force_directed_graph(
    session_graph,
    metric="degree",           # or "betweenness", "eigenvector", "total_mentions"
    use_blue_for_fnm=False,    # Toggle FNM color
    min_node_size=10,          # Minimum node size in pixels
    max_node_size=50,          # Maximum node size in pixels
    min_edge_width=1.0,        # Minimum edge width
    max_edge_width=10.0,       # Maximum edge width
)

# Save to HTML
net.save_graph("output/graph.html")
```

### Customize Party Colors

```python
custom_colors = {
    "PLP": "#FFD700",    # Gold
    "FNM": "#0000FF",    # Blue
    "COI": "#808080",    # Grey
}

net = build_force_directed_graph(
    session_graph,
    party_colors=custom_colors
)
```

### Get Sentiment Color

```python
from graphhansard.dashboard.graph_viz import get_sentiment_color

# Returns color based on net sentiment
color = get_sentiment_color(0.5)   # Green (positive)
color = get_sentiment_color(0.0)   # Grey (neutral)
color = get_sentiment_color(-0.5)  # Red (negative)
```

## Technical Details

### Graph Physics

The visualization uses the **forceAtlas2Based** physics solver with these parameters:
- `gravitationalConstant`: -50 (repulsion between nodes)
- `centralGravity`: 0.01 (pull toward center)
- `springLength`: 200 (ideal edge length)
- `springConstant`: 0.08 (edge stiffness)
- `damping`: 0.4 (motion damping)
- `avoidOverlap`: 1 (prevent node overlap)

### Node Attributes

Each node includes:
- `id`: MP node_id
- `label`: Common name
- `color`: Party color
- `size`: Metric-based size (10-50px)
- `title`: Tooltip with detailed metrics

### Edge Attributes

Each edge includes:
- `from`: Source MP node_id
- `to`: Target MP node_id
- `color`: Sentiment-based color
- `width`: Mention-based thickness
- `value`: Mention count (for weight)
- `title`: Tooltip with mention breakdown
- `arrows`: Directed arrows enabled

## Testing

The visualization module has comprehensive test coverage:

```bash
# Run all visualization tests (30 tests)
pytest tests/test_graph_viz.py -v

# Run dashboard integration tests (4 tests)
pytest tests/test_dashboard.py -v

# Run all tests together
pytest tests/test_graph_viz.py tests/test_dashboard.py -v
```

Test coverage includes:
- Sentiment color mapping (4 tests)
- Metric normalization (4 tests)
- Graph construction (4 tests)
- Party color coding (5 tests)
- Node sizing by metrics (5 tests)
- Edge styling (4 tests)
- Tooltips (2 tests)
- Configuration (2 tests)
- Dashboard integration (4 tests)

## Performance

The visualization is optimized for the 39-MP Bahamian Parliament:
- Typical render time: < 1 second
- Recommended maximum nodes: 100
- Recommended maximum edges: 500

For larger graphs, consider:
- Filtering to show only significant edges (e.g., ≥3 mentions)
- Using aggregated metrics instead of showing all interactions
- Implementing pagination or time-based filtering

## Browser Compatibility

The visualization requires a modern web browser with:
- JavaScript enabled
- SVG/Canvas support
- HTML5 compatibility

Tested on:
- Chrome 90+
- Firefox 85+
- Safari 14+
- Edge 90+

## Future Enhancements

Potential improvements for future versions:
- **Session selector**: Choose any parliamentary session from database
- **Cumulative graphs**: Aggregate multiple sessions over date ranges
- **Time slider**: Animate network evolution over time
- **Community detection**: Visual highlighting of detected communities
- **Export options**: PNG, SVG, PDF export for reports
- **Filter controls**: Filter by party, mention count, sentiment
- **Custom layouts**: Alternative layouts (circular, hierarchical)
- **Node clustering**: Group MPs by party or committee
- **Search/highlight**: Find and highlight specific MPs

## References

- **SRD §9.3**: Layer 3 — The Map specification
- **Issue #16**: MP-1 through MP-4 requirements
- **PyVis Documentation**: https://pyvis.readthedocs.io/
- **Streamlit Documentation**: https://docs.streamlit.io/
- **NetworkX Documentation**: https://networkx.org/

## Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/caribdigital/graphhansard/issues
- Project Documentation: See `docs/` directory
- Code Examples: See `examples/` directory
