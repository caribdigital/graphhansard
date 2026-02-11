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
| **Layer 2 — The Brain** | Transcription (Whisper), diarization (pyannote), entity extraction, sentiment scoring, graph construction | 📋 Planned |
| **Layer 3 — The Map** | Interactive public dashboard (Streamlit + PyVis) | 📋 Planned |

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

---

## Roadmap

- [x] **M-1.1** Golden Record v1.0 — 39 MPs, 357 aliases, validation passing
- [ ] **M-1.2** Miner v1.0 — yt-dlp pipeline, 10+ sessions downloaded
- [ ] **M-1.3** Validation corpus — 50+ annotated mentions from real audio
- [ ] **M-2.1** Transcription pipeline — Whisper + pyannote integration
- [ ] **M-2.3** Entity extraction — mention logs from real sessions
- [ ] **M-2.5** Graph construction — first session graphs with centrality metrics
- [ ] **M-3.1** Dashboard prototype — single-session graph viewable
- [ ] **M-3.4** Public beta launch

See [SRD v1.0](docs/SRD_v1.0.md) for the full requirements document and timeline.

---

## Contributing

GraphHansard is built for the Bahamian public. Contributions are welcome, particularly in:

- **Alias additions** — Know a nickname or informal reference used in House debate? Open an issue or PR against `golden_record/mps.json`.
- **Transcript correction** — Once transcripts are generated, we'll need Bahamian ears to catch what Whisper misses.
- **Validation corpus** — Help annotate real audio clips for testing entity resolution accuracy.
- **Dashboard UX** — Design input for making the graph accessible to non-technical voters.

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
