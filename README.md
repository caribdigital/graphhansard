# GraphHansard

**Mapping the hidden power structure of the Bahamian House of Assembly.**

GraphHansard is an open-source civic technology platform that applies computational sociology and graph theory to the proceedings of the Bahamian Parliament. It ingests parliamentary audio, transcribes and diarizes speech, extracts entity mentions between MPs, scores sentiment, and renders the resulting political interaction network as an interactive force-directed graph — turning debate into data any voter can explore.

[![License: MIT](https://img.shields.io/badge/License-MIT-gold.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Data: CC-BY-4.0](https://img.shields.io/badge/data-CC--BY--4.0-green.svg)](https://creativecommons.org/licenses/by/4.0/)

---

## What This Does

Parliamentary debate in The Bahamas generates thousands of hours of public audio — but no structured, searchable, machine-readable record of *who talks to whom, about what, and with what tone*. GraphHansard closes that gap.

**Input:** Raw audio from House of Assembly sessions (sourced from publicly available YouTube recordings).

**Output:** An interactive network graph where:
- Each **node** is one of the 39 Members of Parliament
- Each **edge** is a reference one MP makes to another during debate
- Edges are **weighted** by frequency and **coloured** by sentiment (supportive, neutral, hostile)
- Network metrics reveal **Force Multipliers** (high eigenvector centrality), **Bridges** (high betweenness centrality), and **Isolated Nodes** (low degree centrality)

Every edge traces back to a timestamp in a public audio recording. Every metric is independently verifiable. The methodology is open. The data is open. The code is open.

---

## Architecture

GraphHansard is organized into four layers:

```
┌─────────────────────────────────────────────────────┐
│  LAYER 3 — THE MAP                                  │
│  Streamlit + PyVis Interactive Dashboard             │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  LAYER 2 — THE BRAIN                                │
│  Transcription → Entity Extraction → Sentiment →    │
│  Graph Construction (NetworkX)                       │
│           │                                         │
│  ┌────────▼────────┐                                │
│  │  LAYER 0        │                                │
│  │  GOLDEN RECORD  │  ← Entity Knowledge Base       │
│  │  (39 MPs, 357   │     for alias resolution       │
│  │   aliases)      │                                │
│  └─────────────────┘                                │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  LAYER 1 — THE MINER                                │
│  yt-dlp Audio Ingestion Pipeline                     │
└─────────────────────────────────────────────────────┘
```

| Layer | Purpose | Status |
|-------|---------|--------|
| **Layer 0 — Golden Record** | Canonical entity knowledge base mapping all 39 MPs to their aliases, portfolios, and constituencies | ✅ Complete |
| **Layer 1 — The Miner** | Audio ingestion pipeline (yt-dlp, rate limiting, metadata cataloguing) | 🔧 In Progress |
| **Layer 2 — The Brain** | Transcription (Whisper), diarization (pyannote), entity extraction, sentiment scoring, graph construction | ✅ Complete |
| **Layer 3 — The Map** | Interactive public dashboard (Streamlit + PyVis force-directed graph visualization) | ✅ Complete |

---

## The Golden Record

The foundation of GraphHansard is the **Golden Record** — a versioned, machine-readable knowledge base that maps every sitting MP to every form by which they may be referenced in debate.

In the Bahamian House of Assembly, no one says "Philip Davis." They say:
- *"The Prime Minister"*
- *"The Member for Cat Island, Rum Cay and San Salvador"*
- *"The Honourable Member opposite"*
- *"The Minister of Finance"*
- *"Brave"*

That is **one node** with multiple aliases — some time-dependent (portfolios change in reshuffles), some dialect-dependent (*"da Memba for Englerston"*), and some anaphoric (*"the gentleman who just spoke"*).

The Golden Record resolver handles all of these through a three-stage cascade:

1. **Exact match** against a 357-alias inverted index
2. **Fuzzy match** (RapidFuzz, token sort ratio ≥ 85) for transcription errors and dialectal variation
3. **Unresolved** — flagged for co-reference resolution or human review

Current validation: **44/44 test cases passing** (100%), including constituency-based, portfolio-based, name-based, fuzzy/dialect, temporal disambiguation across the September 2023 cabinet reshuffle, and correct rejection of anaphoric references.

---

## Project Structure

```
graphhansard/
├── golden_record/
│   ├── __init__.py
│   ├── schema.py              # Pydantic v2 data models (MPNode, PortfolioTenure, etc.)
│   ├── alias_generator.py     # Deterministic alias generation from parliamentary conventions
│   ├── resolver.py            # Entity resolution engine (exact → fuzzy → unresolved)
│   ├── validate.py            # Diagnostic suite (run: python -m golden_record.validate)
│   ├── mps.json               # The canonical record — all 39 MPs
│   └── validation/            # Annotated mention corpus (in progress)
├── archive/                   # Downloaded audio (git-ignored)
│   └── {year}/{session_date}/{video_id}.opus
├── transcripts/               # Diarized transcripts (planned)
├── mentions/                  # Entity mention logs (planned)
├── graphs/                    # NetworkX graph exports (planned)
│   ├── sessions/
│   ├── cumulative/
│   └── exports/
├── dashboard/                 # Streamlit app (planned)
├── docs/
│   └── SRD_v1.0.md           # Software Requirements Document
├── LICENSE
├── README.md
├── pyproject.toml             # (planned)
└── .gitignore
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Install & Validate

```bash
# Clone the repository
git clone https://github.com/carib-digital-labs/graphhansard.git
cd graphhansard

# Install core dependencies
pip install pydantic rapidfuzz

# Run the Golden Record diagnostic
python -m golden_record.validate
```

Expected output:
```
Project Bay Street Graph — Golden Record v1.0 Diagnostic
...
  Test Results: 44/44 passed (100.0%)
  Active MPs: 39
  Total Aliases in Index: 357
  Known Collisions: 6
  ✅ All MPs have ≥ 5 aliases. Coverage acceptable.
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Schema Validation | Pydantic 2.x |
| Fuzzy Matching | RapidFuzz |
| Audio Ingestion | yt-dlp |
| Transcription | insanely-fast-whisper / faster-whisper (Whisper large-v3) |
| Speaker Diarization | pyannote.audio 3.x |
| NLP / NER | spaCy (en_core_web_trf) |
| Sentiment | HuggingFace Transformers (BART-MNLI zero-shot) |
| Graph Library | NetworkX 3.x |
| Community Detection | python-louvain / cdlib |
| Dashboard | Streamlit |
| Graph Visualization | PyVis / D3.js |

---

## Current Parliament: 14th Parliament of The Bahamas

| | |
|---|---|
| **Parliament** | 14th (seated September 16, 2021) |
| **Total Seats** | 39 |
| **Government (PLP)** | 32 seats |
| **Opposition (FNM)** | 6 seats |
| **Coalition of Independents (COI)** | 1 seat |
| **Next General Election** | By September 2026 |

---

## Key Concepts

| Term | Definition |
|------|-----------|
| **Betweenness Centrality** | How often an MP lies on the shortest path between other MPs. High betweenness = **Bridge** between groups. |
| **Eigenvector Centrality** | An MP's influence weighted by the influence of their connections. High eigenvector = **Force Multiplier**. |
| **Golden Record** | The canonical entity knowledge base mapping all MPs to their aliases. |
| **Control Node** | The Speaker of the House — governs debate but does not participate as a partisan actor. |
| **Isolated Node** | An MP with low degree centrality — rarely mentioned and rarely mentioning others. |
| **Force-Directed Graph** | Interactive network visualization where nodes repel and edges attract, creating natural layouts. |
| **Net Sentiment** | (positive_mentions - negative_mentions) / total_mentions. Ranges from -1.0 to +1.0. |

---

## Interactive Dashboard

The GraphHansard dashboard provides an interactive force-directed graph visualization of parliamentary interactions with advanced analytics features:

### Features

#### Core Visualization (MP-1 through MP-4)

- **Force-Directed Layout**: MPs as nodes with physics-based positioning
- **Party Colors**: PLP (gold), FNM (red/blue), COI (grey)
- **Node Sizing**: Choose from degree, betweenness, eigenvector, or total mentions
- **Edge Styling**: Thickness by mention count, color by sentiment (green/grey/red)
- **Interactive Controls**: Pan, zoom, hover tooltips, metric selection

#### 🏆 Leaderboard Panel (MP-10)

- **Top 5 Rankings** by centrality metric (degree, betweenness, eigenvector, closeness)
- **Structural Role Badges**: Force Multiplier ⚡, Bridge 🌉, Hub 🎯, Isolated 🏝️
- **Clickable Entries**: Select any MP to highlight them in the graph
- **Real-time Updates**: Dynamically reflects selected session

#### 📅 Session Timeline (MP-12)

- **Horizontal Timeline**: Navigate all parliamentary sessions by date
- **Visual Indicators**: ✅ data available, ⏳ pending processing
- **Previous/Next Navigation**: Browse sessions chronologically
- **Auto-loading**: Selected session graph renders automatically

#### 📊 MP Report Card (MP-13)

- **Centrality Metrics Over Time**: Line charts tracking network position evolution
- **Top Interaction Partners**: Ranked list of most frequent connections
- **Sentiment Trend Analysis**: Net sentiment evolution with trend classification
- **Structural Role Evolution**: Timeline of role changes across sessions
- **Shareable URLs**: Direct links for journalists and civic organizations

### Quick Start

```bash
# Install dashboard dependencies
pip install -e ".[dashboard]"

# Generate sample data
python examples/build_session_graph.py

# Launch dashboard
streamlit run src/graphhansard/dashboard/app.py
```

### Dashboard Views

Navigate between three main views via the sidebar:

- **Graph Explorer**: Interactive network with real-time leaderboard
- **Session Timeline**: Temporal exploration of sessions
- **MP Report Card**: Individual MP analysis over time

### Documentation

- Complete guide: [`docs/dashboard_features.md`](docs/dashboard_features.md)
- Graph visualization: [`docs/graph_visualization_guide.md`](docs/graph_visualization_guide.md)
- API reference: See module docstrings in `src/graphhansard/dashboard/`

---

## Roadmap

- [x] **M-1.1** Golden Record v1.0 — 39 MPs, 357 aliases, validation passing
- [ ] **M-1.2** Miner v1.0 — yt-dlp pipeline, 10+ sessions downloaded
- [ ] **M-1.3** Validation corpus — 50+ annotated mentions from real audio
- [ ] **M-2.1** Transcription pipeline — Whisper + pyannote integration
- [ ] **M-2.3** Entity extraction — mention logs from real sessions
- [x] **M-2.5** Graph construction — session graphs with centrality metrics
- [x] **M-3.1** Dashboard prototype — force-directed graph visualization (MP-1 through MP-4)
- [x] **M-3.2** Advanced dashboard views — Leaderboard (MP-10), Timeline (MP-12), MP Report Cards (MP-13)
- [ ] **M-3.4** Public beta launch

See [SRD v1.0](docs/SRD_v1.0.md) for the full requirements document and timeline.

---

## Contributing

GraphHansard is built for the Bahamian public. Contributions are welcome, particularly in:

- **Alias additions** — Know a nickname or informal reference used in House debate? Submit it using our structured contribution system. See the [Community Contributions Guide](docs/community_contributions.md) for details.
- **Transcript correction** — Once transcripts are generated, we'll need Bahamian ears to catch what Whisper misses.
- **Validation corpus** — Help annotate real audio clips for testing entity resolution accuracy.
- **Dashboard UX** — Design input for making the graph accessible to non-technical voters.

### Community Alias Submissions (GR-9)

We provide a structured mechanism for community-submitted alias additions and corrections:

```bash
# Submit a new alias
python scripts/submit_alias.py \
  --type alias_addition \
  --alias "Papa" \
  --target mp_davis_brave \
  --evidence "Used in House debate 2024-01-15, video at https://..." \
  --submitter "Your Name"
```

All submissions go through a review queue before being merged. See the [Community Contributions Guide](docs/community_contributions.md) for complete instructions.

---

## Data Export (GR-10)

The Golden Record can be exported in multiple formats for independent use:

```bash
# Export all formats (JSON, CSV, alias index)
python scripts/export_golden_record.py

# Export specific format
python scripts/export_golden_record.py --format csv
```

**Available formats:**
- **JSON**: Canonical format with full metadata
- **CSV**: Flattened format, one row per MP (spreadsheet-ready)
- **Alias Index**: Inverted index mapping aliases to MPs

All exports include metadata headers (version, date, parliament). See the [Data Export Guide](docs/data_export.md) for complete instructions.

---

## Data & Ethics

- All source audio is from **publicly available** parliamentary recordings.
- Only **elected MPs acting in their public capacity** are tracked. No private citizens.
- The system presents **data and computed metrics**, not editorial conclusions.
- Methodology and limitations are **transparently documented**.
- Network metrics are **descriptive, not prescriptive** — they do not imply wrongdoing.

---

## License

Code: [MIT License](LICENSE) — Copyright (c) 2026 Carib Digital Labs

Data & Documentation: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)

---

<p align="center"><em>"Democracy is a data problem."</em></p>
