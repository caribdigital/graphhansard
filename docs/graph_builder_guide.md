# Session Graph Construction & Centrality Metrics

Implementation of BR-21 through BR-26: Directed, weighted interaction graphs with network centrality metrics for parliamentary sessions.

## Overview

The `GraphBuilder` class constructs directed, weighted graphs from mention data where:
- **Nodes** represent Members of Parliament (MPs)
- **Edges** represent aggregated mention interactions
- **Edge weights** reflect mention frequency and sentiment

## Features

### ✅ BR-21: Directed, Weighted Graphs
- Build session-specific graphs from mention records
- Aggregate mentions by source-target pairs
- Edge weight = total mention count

### ✅ BR-22 & BR-23: Edge Attributes
Each edge includes:
- `total_mentions`: Count of mentions from source to target
- `positive_count`: Number of positive sentiment mentions
- `neutral_count`: Number of neutral sentiment mentions
- `negative_count`: Number of negative sentiment mentions
- `net_sentiment`: (positive - negative) / total

### ✅ BR-24: Centrality Metrics
Per node, per session:
- **Degree**: In-degree and out-degree
- **Betweenness Centrality**: Bridge between communities
- **Eigenvector Centrality**: Influence through connections
- **Closeness Centrality**: Average distance to all other nodes

### ✅ BR-25: Cumulative Graphs
- Aggregate multiple sessions into a date-range graph
- Merge edges across sessions
- Compute cumulative centrality metrics

### ✅ BR-26: Structural Roles
Configurable threshold-based role assignment:
- **Force Multiplier**: High eigenvector centrality (influential)
- **Bridge**: High betweenness centrality (connector)
- **Hub**: High in-degree (frequently mentioned)
- **Isolated**: Zero degree (no connections)

## Usage

### Basic Session Graph

```python
from graphhansard.brain.graph_builder import GraphBuilder
from graphhansard.brain.entity_extractor import MentionRecord, ResolutionMethod

# Create mention records
mentions = [
    MentionRecord(
        session_id="session_001",
        source_node_id="mp_davis_brave",
        target_node_id="mp_cooper_chester",
        raw_mention="The Deputy PM",
        resolution_method=ResolutionMethod.EXACT,
        resolution_score=1.0,
        timestamp_start=10.0,
        timestamp_end=11.0,
        context_window="I thank the Deputy PM for his work.",
        segment_index=0,
    ),
]

# Convert to graph dict format with sentiment
mention_dicts = [
    m.to_graph_dict(sentiment_label="positive") for m in mentions
]

# Build graph
builder = GraphBuilder()
session_graph = builder.build_session_graph(
    mentions=mention_dicts,
    session_id="session_001",
    date="2024-01-15",
)

# Access metrics
for node in session_graph.nodes:
    print(f"{node.common_name}: in={node.degree_in}, out={node.degree_out}")
    print(f"  Roles: {', '.join(node.structural_role)}")

# Export
builder.export_json(session_graph, "output/session_001_metrics.json")
```

### With MP Registry

```python
mp_registry = {
    "mp_davis_brave": ("Brave Davis", "PLP"),
    "mp_cooper_chester": ("Chester Cooper", "PLP"),
}

session_graph = builder.build_session_graph(
    mentions=mention_dicts,
    session_id="session_001",
    date="2024-01-15",
    mp_registry=mp_registry,
)
```

### Cumulative Graph

```python
# Build individual session graphs
sg1 = builder.build_session_graph(mentions_jan, "session_001", "2024-01-15")
sg2 = builder.build_session_graph(mentions_feb, "session_002", "2024-02-15")

# Aggregate into cumulative graph
cumulative = builder.build_cumulative_graph(
    session_graphs=[sg1, sg2],
    cumulative_id="q1_2024",
    date_range=("2024-01-15", "2024-02-15"),
)
```

### Custom Structural Role Thresholds

```python
builder = GraphBuilder(
    force_multiplier_threshold=0.8,  # Top 20% eigenvector centrality
    bridge_threshold=0.75,            # Top 25% betweenness centrality
    hub_threshold=0.9,                # Top 10% in-degree
)
```

## Export Formats

### JSON Metrics
Complete session graph with nodes and edges:
```python
builder.export_json(session_graph, "output/session_metrics.json")
```

### CSV Edge List
Simple edge table for spreadsheet analysis:
```python
builder.export_csv(session_graph, "output/edges.csv")
```

### GraphML
For Gephi, yEd, Cytoscape visualization:
```python
nx_graph = builder.build_graph_from_session(session_graph)
builder.export_graphml(nx_graph, "output/graph.graphml")
```

### GEXF
For Gephi dynamic network visualization:
```python
builder.export_gexf(nx_graph, "output/graph.gexf")
```

## Schema

### SessionGraph
```python
SessionGraph:
  session_id: str
  date: str
  graph_file: str
  node_count: int
  edge_count: int
  nodes: list[NodeMetrics]
  edges: list[EdgeRecord]
```

### NodeMetrics
```python
NodeMetrics:
  node_id: str
  common_name: str
  party: str
  degree_in: int
  degree_out: int
  betweenness: float
  eigenvector: float
  closeness: float
  structural_role: list[str]
  community_id: int | None
```

### EdgeRecord
```python
EdgeRecord:
  source_node_id: str
  target_node_id: str
  total_mentions: int
  positive_count: int
  neutral_count: int
  negative_count: int
  net_sentiment: float
```

## Performance

- **NF-3 Requirement**: Graph computation ≤5 seconds for 39-node graph
- **Achieved**: 0.38 seconds (13x faster than requirement)
- Tested with ~780 mentions (20 mentions per MP average)

## Example

See `examples/build_session_graph.py` for a complete working example.

```bash
python examples/build_session_graph.py
```

## Testing

Run the test suite:
```bash
pytest tests/test_graph_builder.py -v
```

23 tests covering:
- Graph construction (BR-21)
- Edge aggregation (BR-22)
- Sentiment attributes (BR-23)
- Centrality metrics (BR-24)
- Cumulative graphs (BR-25)
- Structural roles (BR-26)
- Export functionality
- Performance benchmarks
- MentionRecord integration

## References

- SRD §8.5 (Stage 4 — Graph Construction)
- SRD §15 (Milestone M-2.5)
- NetworkX 3.x Documentation
- Issue #13: BR-21 through BR-26
