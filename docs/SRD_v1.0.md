# Project Bay Street Graph
## Software Requirements Document — v1.0

**Document Status:** DRAFT  
**Author:** Dr. Aris "Vector" Moncur, Lead Civic Technologist  
**Date:** February 10, 2026  
**Distribution:** Internal Team / Community Stakeholders  
**License:** MIT (All source code) · CC-BY-4.0 (All documentation and data schemas)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Project Vision & Objectives](#3-project-vision--objectives)
4. [Scope](#4-scope)
5. [System Architecture Overview](#5-system-architecture-overview)
6. [Layer 0 — The Golden Record (Entity Knowledge Base)](#6-layer-0--the-golden-record)
7. [Layer 1 — The Miner (Audio Ingestion Pipeline)](#7-layer-1--the-miner)
8. [Layer 2 — The Brain (Processing & NLP Pipeline)](#8-layer-2--the-brain)
9. [Layer 3 — The Map (Visualization & Public Dashboard)](#9-layer-3--the-map)
10. [Data Model & Schema Definitions](#10-data-model--schema-definitions)
11. [Bahamian Context Requirements](#11-bahamian-context-requirements)
12. [Non-Functional Requirements](#12-non-functional-requirements)
13. [Technology Stack](#13-technology-stack)
14. [Risks & Mitigations](#14-risks--mitigations)
15. [Roadmap & Milestones](#15-roadmap--milestones)
16. [Glossary](#16-glossary)
17. [Appendices](#17-appendices)

---

## 1. Executive Summary

Project Bay Street Graph is an open-source civic technology platform that applies computational sociology and graph theory to the proceedings of the Bahamian House of Assembly. The system ingests raw parliamentary audio from publicly available sources, transcribes and diarizes the speech, extracts entity mentions and inter-MP references, and renders the resulting political network as an interactive, publicly accessible force-directed graph.

The core output is a **Political Interaction Network** — a mathematical graph where each of the 39 Members of Parliament is a node, and each reference one MP makes to another during debate is a weighted, sentiment-scored edge. This network reveals structural properties invisible to the casual observer: who are the "bridges" between the governing PLP and opposition FNM? Which backbenchers are structurally isolated? Which ministers are referenced but never reference others — indicating deference hierarchies?

This is not opinion journalism. This is reproducible, auditable, data-driven transparency. Every edge in the graph traces back to a timestamp in a public audio recording. Every centrality score can be independently verified. The methodology is open. The data is open. The code is open.

Democracy is a data problem. We intend to solve it.

---

## 2. Problem Statement

### 2.1 The Transparency Gap

The Bahamas operates a Westminster-style parliamentary democracy with 39 elected Members of Parliament in the House of Assembly. Despite the constitutional importance of parliamentary debate, there is currently:

- **No searchable, machine-readable Hansard.** Transcripts, where they exist, are published as unstructured PDFs with inconsistent formatting — months or years after the fact.
- **No public record of inter-MP interaction patterns.** Citizens can watch debates live, but there is no systematic way to answer questions like: "How many times has my MP been referenced by the Prime Minister this term?" or "Which opposition members does the Minister of Finance actually engage with?"
- **No quantitative accountability tool.** Voters cannot objectively measure whether their MP is active, influential, isolated, or simply absent.

### 2.2 Why This Matters

Political influence in small-island democracies operates through informal networks that are rarely visible to the electorate. In a 39-seat parliament where a single defection can shift the balance of power, understanding *who talks to whom, about what, and with what tone* is not academic curiosity — it is essential civic infrastructure.

### 2.3 Why Now

Three technical developments make this project feasible today in a way it was not five years ago:

1. **Open-source speech-to-text models** (OpenAI Whisper, `insanely-fast-whisper`) have reached near-human accuracy on English speech and can be fine-tuned for dialectal variation.
2. **Speaker diarization** (`pyannote.audio`) now works reliably enough for multi-speaker parliamentary settings.
3. **Graph visualization libraries** (PyVis, Streamlit, D3.js) allow interactive, browser-based network rendering without proprietary software.

The raw audio exists. The tools exist. What has been missing is the integrating architecture and the domain expertise to apply these tools to the Bahamian parliamentary context. That is what this project provides.

---

## 3. Project Vision & Objectives

### 3.1 Vision Statement

> *To make the structure of political influence in the Bahamian House of Assembly visible, searchable, and accountable to every citizen — using open data, open code, and open methodology.*

### 3.2 Primary Objectives

| ID | Objective | Success Metric |
|----|-----------|---------------|
| O-1 | Build a complete, versioned entity knowledge base of all 39 MPs and their aliases | 100% of MPs mapped; alias resolver achieves ≥90% accuracy on validation corpus |
| O-2 | Ingest and archive all publicly available House of Assembly session audio | ≥95% of available YouTube sessions downloaded and catalogued |
| O-3 | Transcribe audio with speaker attribution at per-utterance granularity | Word Error Rate (WER) ≤15% on Bahamian parliamentary speech; diarization error rate (DER) ≤20% |
| O-4 | Extract MP-to-MP references and score each for sentiment | Entity extraction recall ≥85%; sentiment classification accuracy ≥75% on three-class scale (positive/neutral/negative) |
| O-5 | Compute and publish a standard set of network centrality metrics per MP per session | Betweenness, degree, eigenvector, and closeness centrality available for all sessions |
| O-6 | Deliver a public, interactive web dashboard for exploring the network | Dashboard loads in ≤3 seconds; supports filtering by date, MP, party, and topic |

### 3.3 Secondary Objectives

| ID | Objective | Notes |
|----|-----------|-------|
| O-7 | Enable community contribution to alias mapping and transcription correction | Provide a structured feedback mechanism |
| O-8 | Publish raw datasets (transcriptions, entity extractions, graph edge lists) under open license | CC-BY-4.0 for data; MIT for code |
| O-9 | Establish methodology that is replicable for other Caribbean parliaments | Document all Bahamas-specific adaptations clearly |

---

## 4. Scope

### 4.1 In Scope (v1.0)

- **Parliamentary Term:** Current term (2021–present, the 15th Parliament)
- **Chamber:** House of Assembly only (Senate excluded from v1.0)
- **Source:** YouTube recordings from the official Bahamas Parliament channel and any verified mirrors
- **Languages:** English (with Bahamian Creole dialectal variation in phonology and syntax)
- **Outputs:** Interactive web dashboard, downloadable graph datasets (CSV, GraphML, JSON), API for programmatic access

### 4.2 Out of Scope (v1.0)

- Historical parliaments (pre-2021) — deferred to v2.0
- Senate proceedings
- Select committee meetings (audio rarely available)
- Real-time / live transcription (batch processing only)
- Voting record integration (future data source)
- Campaign finance or lobbying network overlay
- Mobile-native application (responsive web only in v1.0)

---

## 5. System Architecture Overview

The system is organized into four layers, each independently testable and deployable:

```
┌─────────────────────────────────────────────────────────────────┐
│                     LAYER 3 — THE MAP                           │
│           Streamlit + PyVis Interactive Dashboard                │
│         (Force-directed graph, filters, MP profiles)            │
└────────────────────────────┬────────────────────────────────────┘
                             │ reads from
┌────────────────────────────▼────────────────────────────────────┐
│                    LAYER 2 — THE BRAIN                          │
│              NLP & Graph Construction Pipeline                  │
│                                                                 │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐ │
│  │  Transcription│  │    Entity     │  │  Graph Construction  │ │
│  │  + Diarization│─▶│  Extraction   │─▶│  + Centrality Calc   │ │
│  │  (Whisper +   │  │  + Coreference│  │  (NetworkX)          │ │
│  │  pyannote)    │  │  Resolution   │  │                      │ │
│  └──────────────┘  └───────┬───────┘  └──────────────────────┘ │
│                            │ consults                           │
│                  ┌─────────▼─────────┐                         │
│                  │   LAYER 0         │                         │
│                  │   GOLDEN RECORD   │                         │
│                  │   (Entity KB)     │                         │
│                  └───────────────────┘                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ consumes
┌────────────────────────────▼────────────────────────────────────┐
│                    LAYER 1 — THE MINER                          │
│                Audio Ingestion Pipeline                         │
│                                                                 │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐ │
│  │  yt-dlp       │  │  Metadata     │  │  Audio Archive       │ │
│  │  Scraper      │─▶│  Cataloguer   │─▶│  (Organized by       │ │
│  │  (+ cookies,  │  │  (date, title,│  │   session/date)      │ │
│  │  rate limits) │  │  duration)    │  │                      │ │
│  └──────────────┘  └───────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 5.1 Data Flow Summary

1. **Miner** downloads raw audio (.opus/.m4a) from YouTube → stores locally with metadata catalogue
2. **Brain — Stage 1** transcribes audio with speaker diarization → produces timestamped, speaker-segmented transcript
3. **Brain — Stage 2** scans transcript for MP references, resolves them via the Golden Record → produces a structured mention log
4. **Brain — Stage 3** scores each mention for sentiment → produces weighted, signed edge list
5. **Brain — Stage 4** constructs the session graph and computes centrality metrics → stores graph in GraphML + JSON
6. **Map** reads stored graphs and metrics → renders interactive dashboard for public consumption

---

## 6. Layer 0 — The Golden Record

### 6.1 Purpose

The Golden Record is the canonical, versioned, machine-readable knowledge base that maps every sitting MP to the complete set of identities by which they may be referenced in parliamentary debate. It is the foundation upon which all entity extraction depends.

### 6.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| GR-1 | Store the canonical profile for all 39 MPs in the current House of Assembly | Must Have |
| GR-2 | For each MP, maintain a list of all known aliases (constituency-based, portfolio-based, name-based, informal) | Must Have |
| GR-3 | Support temporal versioning of portfolio-based aliases (an alias is valid only during the MP's tenure in that role) | Must Have |
| GR-4 | Provide an alias resolution API that accepts a raw mention string and returns the canonical MP node ID, or `null` if unresolved | Must Have |
| GR-5 | Support fuzzy string matching to handle transcription errors and dialectal variation (e.g., "da Memba for Englerston" → "The Member for Englerston") | Must Have |
| GR-6 | Detect and flag alias collisions (two MPs sharing an alias at different times) | Must Have |
| GR-7 | Distinguish the Speaker of the House as a special "control node" with different edge semantics | Must Have |
| GR-8 | Support versioning by parliamentary term to enable future historical analysis | Should Have |
| GR-9 | Provide a structured mechanism for community-submitted alias additions and corrections | Should Have |
| GR-10 | Export the full record in JSON and CSV formats for independent use | Must Have |

### 6.3 Data Schema — `MPNode`

```
MPNode:
  node_id           : string       # Canonical unique ID (e.g., "mp_davis_brave")
  full_name          : string       # Legal full name
  common_name        : string       # Name in common usage
  party              : enum         # "PLP" | "FNM" | "IND" | "DNA"
  constituency       : string       # Official constituency name
  is_cabinet         : boolean
  is_opposition_front: boolean
  gender             : enum         # "M" | "F" | "X"
  node_type          : enum         # "debater" | "control" (Speaker of the House)
  seat_status        : enum         # "active" | "resigned" | "deceased" | "suspended"
  first_elected      : date | null
  portfolios         : list[PortfolioTenure]
  aliases            : list[string] # Manually curated aliases not derivable from rules
```

```
PortfolioTenure:
  title              : string       # Full official title
  short_title        : string       # Commonly used abbreviation
  start_date         : date
  end_date           : date | null  # null = currently active
```

### 6.4 Alias Resolution Logic

The resolver operates in the following cascade:

1. **Exact Match** — Normalize input (lowercase, strip honorifics), look up in inverted alias index. If found and temporally valid for the debate date, return node ID.
2. **Fuzzy Match** — If no exact match, run `rapidfuzz.fuzz.token_sort_ratio` against all aliases. If best match score ≥ configurable threshold (default: 85), return node ID.
3. **Contextual / Anaphoric Resolution** — If the mention is a deictic reference ("the Member who just spoke," "my honourable friend"), pass to the co-reference resolution module in Layer 2, which uses the speaker turn history to resolve.
4. **Unresolved** — If all methods fail, return `null` and log the mention for human review.

### 6.5 Validation Requirement

Before the Golden Record is declared production-ready, it must be validated against a manually annotated corpus of ≥50 resolved mentions from real House of Assembly audio. Target: ≥90% resolution accuracy (Precision and Recall) on this corpus.

---

## 7. Layer 1 — The Miner

### 7.1 Purpose

The Miner is a robust, rate-limited, resumable audio ingestion pipeline that discovers, downloads, catalogues, and archives House of Assembly session recordings from YouTube.

### 7.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| MN-1 | Discover all House of Assembly videos from the official Bahamas Parliament YouTube channel via playlist or channel scrape | Must Have |
| MN-2 | Download audio-only streams in the highest available quality (prefer opus/m4a, ≥128kbps) | Must Have |
| MN-3 | Handle YouTube authentication via exported browser cookies for age-restricted or consent-gated content | Must Have |
| MN-4 | Implement configurable rate limiting (default: 1 request per 5 seconds, max 50 downloads per session) to avoid IP bans | Must Have |
| MN-5 | Support resumable downloads — if interrupted, the pipeline resumes from the last incomplete file without re-downloading completed files | Must Have |
| MN-6 | Generate a metadata catalogue entry for each downloaded session containing: video ID, title, upload date, duration, download timestamp, file path, and file hash (SHA-256) | Must Have |
| MN-7 | Organize downloaded audio into a structured directory hierarchy: `archive/{year}/{session_date}/` | Must Have |
| MN-8 | Detect and skip duplicate downloads (by video ID or file hash) | Must Have |
| MN-9 | Support proxy rotation for resilience against IP-based throttling | Should Have |
| MN-10 | Log all download attempts (success, failure, skip) to a structured log file | Must Have |
| MN-11 | Support manual addition of audio files from non-YouTube sources (e.g., ZNS radio archives) | Should Have |
| MN-12 | Provide a CLI interface for triggering full or incremental scrapes | Must Have |

### 7.3 Technical Approach

- **Primary Tool:** `yt-dlp` (latest stable release)
- **Cookie Handling:** Import from Firefox/Chrome via `--cookies-from-browser` or from an exported Netscape-format cookies file via `--cookies`
- **Rate Limiting:** Enforced via `--sleep-interval` and `--max-sleep-interval` flags, supplemented by a custom wrapper that tracks request count per session
- **Output Template:** `archive/%(upload_date>%Y)s/%(upload_date)s/%(id)s.%(ext)s`
- **Archive File:** `yt-dlp` native `--download-archive` file to track completed downloads and prevent re-downloading

### 7.4 Metadata Catalogue Schema

```
SessionAudio:
  video_id           : string       # YouTube video ID
  title              : string       # Video title (raw from YouTube)
  parsed_date        : date | null  # Extracted session date (parsed from title)
  upload_date        : date         # YouTube upload date
  duration_seconds   : integer
  audio_format       : string       # e.g., "opus", "m4a"
  audio_bitrate_kbps : integer
  file_path          : string       # Relative path in archive
  file_hash_sha256   : string
  download_timestamp : datetime
  source_url         : string       # Full YouTube URL
  status             : enum         # "downloaded" | "failed" | "skipped_duplicate"
  notes              : string | null
```

---

## 8. Layer 2 — The Brain

### 8.1 Purpose

The Brain is the core NLP and graph construction pipeline. It transforms raw audio into a structured, sentiment-scored political interaction network. It operates in four sequential stages.

### 8.2 Stage 1 — Transcription & Diarization

#### 8.2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| BR-1 | Transcribe audio to text using a Whisper-based model with word-level timestamps | Must Have |
| BR-2 | Perform speaker diarization to segment the transcript by individual speaker turns | Must Have |
| BR-3 | Output a structured transcript where each segment contains: speaker label, start time, end time, and transcribed text | Must Have |
| BR-4 | Achieve a Word Error Rate (WER) of ≤15% on Bahamian parliamentary speech, validated against a manually transcribed test set | Must Have |
| BR-5 | Achieve a Diarization Error Rate (DER) of ≤20% on multi-speaker House sessions | Must Have |
| BR-6 | Support GPU-accelerated inference for batch processing (target: process 1 hour of audio in ≤10 minutes on a single consumer GPU) | Should Have |
| BR-7 | Handle audio artifacts common to parliamentary recordings: echo, cross-talk, microphone switching, background heckling | Should Have |
| BR-8 | Provide a manual correction interface or format (e.g., editable JSON) for community transcript review | Should Have |

#### 8.2.2 Technical Approach

- **Transcription:** `insanely-fast-whisper` (Whisper `large-v3` backend with Flash Attention 2 for speed) or `faster-whisper` (CTranslate2 backend for lower VRAM usage)
- **Diarization:** `pyannote.audio` 3.x pipeline (requires Hugging Face token and acceptance of pyannote model terms)
- **Integration:** Use `whisperx` to align Whisper output with pyannote diarization for speaker-attributed, word-level timestamps
- **Fine-Tuning (v1.1):** Prepare a fine-tuning dataset of ≥10 hours of manually corrected Bahamian parliamentary transcripts to reduce WER on dialectal speech

#### 8.2.3 Output Schema — `DiarizedTranscript`

```
DiarizedTranscript:
  session_id         : string       # Links to SessionAudio.video_id
  segments           : list[TranscriptSegment]

TranscriptSegment:
  speaker_label      : string       # Diarization label (e.g., "SPEAKER_00")
  speaker_node_id    : string|null  # Resolved MP node_id (null if unresolved)
  start_time         : float        # Seconds from start of audio
  end_time           : float
  text               : string       # Transcribed text
  confidence         : float        # Average word-level confidence (0.0–1.0)
  words              : list[WordToken]  # Word-level detail (optional)

WordToken:
  word               : string
  start              : float
  end                : float
  confidence         : float
```

### 8.3 Stage 2 — Entity Extraction & Co-reference Resolution

#### 8.3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| BR-9  | Scan each transcript segment for mentions of MPs using pattern matching and NER | Must Have |
| BR-10 | Resolve each detected mention to a canonical MP node ID via the Golden Record resolver | Must Have |
| BR-11 | Handle anaphoric / deictic references ("the Member who just spoke," "the honourable gentleman opposite") using speaker turn context | Must Have |
| BR-12 | For each resolved mention, record: the mentioning MP (source), the mentioned MP (target), the raw mention string, the timestamp, and the surrounding context window (±1 sentence) | Must Have |
| BR-13 | Achieve entity extraction recall ≥85% and precision ≥80% on the validation corpus | Must Have |
| BR-14 | Log all unresolved mentions for human review and Golden Record expansion | Must Have |
| BR-15 | Distinguish self-references (MP referring to themselves in third person, which is common in parliamentary speech) and exclude them from the interaction graph | Should Have |

#### 8.3.2 Technical Approach

- **Pattern Matching Layer:** Regex and rule-based extraction for deterministic patterns ("The Member for [X]", "The Minister of [Y]", "The Honourable [Name]")
- **NER Layer:** spaCy `en_core_web_trf` model for detecting PERSON entities, with a custom entity ruler for parliamentary titles
- **Co-reference Resolution:** A context-window heuristic: for deictic references, examine the previous N speaker turns to identify the most likely referent, scored by recency and semantic fit
- **Fallback — Local LLM (v1.1):** For ambiguous cases, optionally invoke a local LLM (e.g., Mistral 7B or Llama 3 8B via Ollama) with a structured prompt to resolve the reference

#### 8.3.3 Output Schema — `MentionLog`

```
MentionRecord:
  session_id         : string
  source_node_id     : string       # MP who made the mention (the speaker)
  target_node_id     : string|null  # MP who was mentioned (resolved)
  raw_mention        : string       # Exact text as spoken/transcribed
  resolution_method  : enum         # "exact" | "fuzzy" | "coreference" | "llm" | "unresolved"
  resolution_score   : float        # Confidence of the resolution (0.0–1.0)
  timestamp_start    : float
  timestamp_end      : float
  context_window     : string       # Surrounding text for verification
  segment_index      : integer      # Index into DiarizedTranscript.segments
```

### 8.4 Stage 3 — Sentiment Scoring

#### 8.4.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| BR-16 | Score each resolved mention for sentiment on a three-class scale: Positive (supportive, praising, agreeing), Neutral (procedural, factual), Negative (hostile, critical, mocking) | Must Have |
| BR-17 | Use the context window (±1 sentence around the mention) as the input for sentiment classification | Must Have |
| BR-18 | Achieve ≥75% accuracy on three-class sentiment classification, validated against a manually annotated test set | Must Have |
| BR-19 | Detect and flag parliamentary-specific sentiment markers: formal objections ("On a point of order!"), direct challenges ("Will the Member yield?"), heckling, and sarcasm | Should Have |
| BR-20 | Output a sentiment label and confidence score for each mention record | Must Have |

#### 8.4.2 Technical Approach

- **Baseline Model:** Fine-tuned `cardiffnlp/twitter-roberta-base-sentiment-latest` on a parliamentary speech dataset (to be curated)
- **Parliamentary Adaptation:** Custom training set of ≥500 annotated mention-context pairs from Bahamian House debates, labelled by two independent annotators with inter-annotator agreement measured (target: Cohen's κ ≥ 0.65)
- **Fallback — Zero-Shot (v1.0):** For initial deployment, use a zero-shot classification pipeline (`facebook/bart-large-mnli`) with labels: ["supportive reference", "neutral or procedural reference", "hostile or critical reference"]

### 8.5 Stage 4 — Graph Construction & Metric Computation

#### 8.5.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| BR-21 | Construct a directed, weighted graph for each session where nodes are MPs and edges are aggregated mention interactions | Must Have |
| BR-22 | Edge weight = count of mentions from source to target in that session | Must Have |
| BR-23 | Edge attributes include: total count, positive count, neutral count, negative count, net sentiment score | Must Have |
| BR-24 | Compute the following centrality metrics per node per session: Degree (in/out), Betweenness Centrality, Eigenvector Centrality, Closeness Centrality | Must Have |
| BR-25 | Compute a cumulative graph aggregating all sessions in a configurable date range | Must Have |
| BR-26 | Identify and label structural roles: "Force Multiplier" (high eigenvector centrality), "Bridge" (high betweenness centrality), "Isolated Node" (low degree centrality), "Hub" (high in-degree) | Must Have |
| BR-27 | Detect "communities" within the graph using modularity-based community detection (Louvain algorithm) to reveal cross-party clusters | Should Have |
| BR-28 | Export graphs in GraphML, GEXF, JSON (node-link format), and edge list CSV | Must Have |

#### 8.5.2 Technical Approach

- **Graph Library:** NetworkX 3.x
- **Community Detection:** `python-louvain` (community module) or `cdlib`
- **Export:** NetworkX native export functions + custom JSON serialiser for dashboard consumption
- **Storage:** One GraphML file per session + one cumulative GraphML file per parliamentary term, stored alongside computed metrics in a structured directory

#### 8.5.3 Output Schema — `SessionGraph`

```
SessionGraph:
  session_id         : string
  date               : date
  graph_file         : string       # Path to GraphML file
  node_count         : integer
  edge_count         : integer
  nodes              : list[NodeMetrics]
  edges              : list[EdgeRecord]

NodeMetrics:
  node_id            : string
  common_name        : string
  party              : string
  degree_in          : integer
  degree_out         : integer
  betweenness        : float
  eigenvector        : float
  closeness          : float
  structural_role    : list[string]  # e.g., ["bridge", "force_multiplier"]
  community_id       : integer|null

EdgeRecord:
  source_node_id     : string
  target_node_id     : string
  total_mentions     : integer
  positive_count     : integer
  neutral_count      : integer
  negative_count     : integer
  net_sentiment      : float        # Computed: (positive - negative) / total
```

---

## 9. Layer 3 — The Map

### 9.1 Purpose

The Map is the public-facing interactive dashboard that renders the political interaction network for citizen exploration. It transforms the abstract mathematics of graph theory into an intuitive, visual experience that any voter can understand.

### 9.2 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| MP-1 | Display the interaction network as a force-directed graph where MPs are nodes and mentions are edges | Must Have |
| MP-2 | Colour-code nodes by party affiliation (PLP = gold, FNM = red/blue, IND = grey — or user-configurable) | Must Have |
| MP-3 | Scale node size by a selectable metric (default: degree centrality; options: betweenness, eigenvector, total mentions) | Must Have |
| MP-4 | Scale edge thickness by mention count; colour edges by net sentiment (green = positive, grey = neutral, red = negative) | Must Have |
| MP-5 | Allow users to click a node to view the MP's profile card: name, constituency, party, portfolio, centrality scores, structural roles | Must Have |
| MP-6 | Allow users to click an edge to view the mention details: count, sentiment breakdown, and links to source timestamps in the original audio | Must Have |
| MP-7 | Provide a date range filter (single session, date range, or full term) | Must Have |
| MP-8 | Provide a party filter (show only PLP, only FNM, or cross-party edges only) | Must Have |
| MP-9 | Provide a search bar to find and highlight a specific MP by name or constituency | Must Have |
| MP-10 | Display a "Leaderboard" panel showing the top 5 MPs by each centrality metric for the selected time range | Should Have |
| MP-11 | Support drag-and-drop interaction: users can physically reposition nodes to explore graph topology | Should Have |
| MP-12 | Provide a "Session Timeline" view: a horizontal timeline of sessions where users can select a session and see the graph snapshot | Should Have |
| MP-13 | Render an "MP Report Card" page for each MP summarising their network position over time | Should Have |
| MP-14 | Load and render in ≤3 seconds on a standard broadband connection for a single-session graph | Must Have |
| MP-15 | Be fully usable on tablet and desktop browsers; degrade gracefully on mobile | Must Have |
| MP-16 | Include an "About This Data" page explaining the methodology, data sources, and limitations in plain language | Must Have |

### 9.3 Technical Approach

- **Framework:** Streamlit (rapid prototyping for v1.0; consider migration to Next.js for v2.0 if performance requires it)
- **Graph Rendering:** PyVis (generates interactive HTML/JS force-directed graphs embeddable in Streamlit via `components.html()`) or Streamlit-agraph for native integration
- **Alternative Renderer (v1.1):** D3.js force simulation for finer control over aesthetics and performance, embedded via Streamlit custom component
- **Hosting:** Streamlit Community Cloud (free tier for v1.0) or self-hosted on a low-cost VPS (e.g., Hetzner, DigitalOcean)

---

## 10. Data Model & Schema Definitions

### 10.1 Data Storage Strategy

All data is stored as flat files in a structured directory hierarchy. No relational database is required for v1.0. This maximises portability, auditability, and ease of open-data distribution.

```
bay-street-graph/
├── golden_record/
│   ├── mps.json                    # Array of MPNode objects
│   ├── aliases_index.json          # Inverted alias → node_id index
│   └── validation/
│       └── annotated_mentions.json # Human-annotated validation corpus
├── archive/
│   ├── catalogue.json              # Array of SessionAudio objects
│   └── 2024/
│       ├── 20240115/
│       │   └── dQw4w9WgXcQ.opus
│       └── 20240220/
│           └── ...
├── transcripts/
│   ├── dQw4w9WgXcQ.json           # DiarizedTranscript
│   └── ...
├── mentions/
│   ├── dQw4w9WgXcQ.json           # Array of MentionRecord
│   └── ...
├── graphs/
│   ├── sessions/
│   │   ├── dQw4w9WgXcQ.graphml
│   │   └── dQw4w9WgXcQ_metrics.json
│   ├── cumulative/
│   │   └── 15th_parliament.graphml
│   └── exports/
│       ├── edge_list.csv
│       └── node_metrics.csv
├── dashboard/
│   ├── app.py                      # Streamlit entry point
│   └── ...
└── docs/
    ├── SRD_v1.0.md                 # This document
    └── methodology.md
```

### 10.2 Interchange Formats

| Data Type | Primary Format | Secondary Format | Notes |
|-----------|---------------|-----------------|-------|
| Golden Record | JSON | CSV | JSON is canonical; CSV for spreadsheet users |
| Audio Catalogue | JSON | — | |
| Transcripts | JSON | SRT (subtitle) | SRT export for human review alongside video |
| Mention Logs | JSON | CSV | |
| Graphs | GraphML | GEXF, JSON (node-link), edge list CSV | GraphML is canonical for NetworkX interop |
| Centrality Metrics | JSON | CSV | |

---

## 11. Bahamian Context Requirements

This section documents domain-specific constraints and assumptions that are critical to the system's accuracy in the Bahamian parliamentary context.

### 11.1 Dialectal Speech Adaptation

| ID | Requirement | Rationale |
|----|-------------|-----------|
| BC-1 | The transcription model must handle TH-stopping ("da" → "the", "dat" → "that") without hallucinating incorrect words | Standard in Bahamian Creole phonology; Whisper may misinterpret |
| BC-2 | The alias resolver must tolerate vowel shifts in constituency names ("Englerston" → "Englaston") | Common transcription artefact |
| BC-3 | The system must handle code-switching between Standard English and Bahamian Creole within a single speaker turn | MPs frequently switch registers mid-sentence |

### 11.2 Parliamentary Procedure Conventions

| ID | Requirement | Rationale |
|----|-------------|-----------|
| BC-4 | The Speaker of the House is a control node with distinct edge semantics (recognizing, admonishing, cutting off); references to/from the Speaker are tagged as "procedural" and excluded from the political interaction graph by default | The Speaker is constitutionally non-partisan |
| BC-5 | The system must detect "Point of Order" interruptions and model them as a special edge type (they indicate procedural conflict, not substantive debate) | Common mechanism for disrupting debate |
| BC-6 | The system must account for the convention that MPs refer to each other by constituency, not by name, in formal debate | Primary alias pattern |
| BC-7 | The system must handle the "Honourable" prefix and its variants ("The Honourable," "the Hon.," "the honourable member") as noise to be normalised, not as a distinguishing feature | Every MP receives this prefix |

### 11.3 Audio Quality Considerations

| ID | Requirement | Rationale |
|----|-------------|-----------|
| BC-8 | The pipeline must handle variable audio quality including: low-bitrate YouTube compression, chamber echo, overlapping voices during heckling, and microphone cuts | Typical of House recordings |
| BC-9 | The system should detect and flag segments where audio quality falls below a usable threshold (e.g., SNR < 10dB) rather than producing low-confidence transcriptions | Bad transcription is worse than no transcription |
| BC-10 | The system should handle the "hot mic" scenario where an MP is picked up speaking off-the-record; these segments should be flagged and excluded by default | Ethical consideration |

---

## 12. Non-Functional Requirements

### 12.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NF-1 | Audio transcription throughput | ≥6x real-time on a consumer GPU (RTX 3080 or equivalent) |
| NF-2 | Entity extraction processing time | ≤30 seconds per hour of transcribed text |
| NF-3 | Graph computation time (single session) | ≤5 seconds for a 39-node graph |
| NF-4 | Dashboard initial load time | ≤3 seconds on 50 Mbps connection |
| NF-5 | Dashboard graph interaction latency | ≤100ms for node drag, zoom, pan |

### 12.2 Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| NF-6 | Miner pipeline must be idempotent and resumable | Re-running does not duplicate data |
| NF-7 | All pipeline stages must log errors and continue processing remaining items | No single failure kills a batch |
| NF-8 | Dashboard uptime | ≥99% (monthly) |

### 12.3 Security & Privacy

| ID | Requirement | Notes |
|----|-------------|-------|
| NF-9 | No personal data beyond what is on the public parliamentary record is collected or stored | |
| NF-10 | YouTube cookies files are excluded from version control via `.gitignore` | Credentials must never be committed |
| NF-11 | The system does not store or process any data about private citizens; only elected MPs in their public capacity | |

### 12.4 Accessibility

| ID | Requirement | Notes |
|----|-------------|-------|
| NF-12 | Dashboard must be navigable by keyboard | WCAG 2.1 AA |
| NF-13 | Colour coding must not be the sole means of conveying information (provide labels/patterns) | Colour-blind accessibility |
| NF-14 | All methodology documentation must be written in plain language (target: Grade 10 reading level) | Civic tool — must be broadly accessible |

### 12.5 Legal & Ethical

| ID | Requirement | Notes |
|----|-------------|-------|
| NF-15 | All source audio is from publicly available parliamentary recordings; no FOIA or restricted data is used in v1.0 | |
| NF-16 | The system presents data and computed metrics, not editorial conclusions; framing must be neutral | |
| NF-17 | Methodology and limitations must be transparently documented and accessible from the dashboard | |
| NF-18 | The system must include a disclaimer that network metrics are descriptive, not prescriptive, and do not imply wrongdoing | |

---

## 13. Technology Stack

### 13.1 Core Dependencies

| Component | Technology | Version / Notes |
|-----------|-----------|-----------------|
| Language | Python | 3.11+ |
| Audio Ingestion | yt-dlp | Latest stable |
| Transcription | insanely-fast-whisper OR faster-whisper | Whisper large-v3 backend |
| Diarization | pyannote.audio | 3.x |
| Alignment | whisperx | For merging transcription + diarization |
| NER / NLP | spaCy | en_core_web_trf model |
| Fuzzy Matching | rapidfuzz | |
| Sentiment | transformers (HuggingFace) | cardiffnlp or BART-MNLI zero-shot |
| Graph Library | NetworkX | 3.x |
| Community Detection | python-louvain OR cdlib | |
| Dashboard | Streamlit | 1.x |
| Graph Viz | PyVis OR streamlit-agraph | |
| Data Validation | Pydantic | 2.x (schema enforcement) |
| Testing | pytest | |
| Task Orchestration | Prefect OR Dagster | Optional for v1.0; recommended for v1.1 |

### 13.2 Infrastructure

| Component | Recommendation |
|-----------|---------------|
| Development | Local machine with NVIDIA GPU (≥8GB VRAM) |
| CI/CD | GitHub Actions |
| Dashboard Hosting | Streamlit Community Cloud (v1.0) → VPS (v1.1) |
| Data Storage | Local filesystem (v1.0) → S3-compatible object store (v1.1) |
| Version Control | Git + GitHub (public repository) |

---

## 14. Risks & Mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-1 | YouTube blocks scraping or removes parliamentary content | Medium | Critical | Maintain a local archive mirror; implement proxy rotation; monitor for DMCA/ToS changes; explore direct partnership with Parliament for source audio |
| R-2 | Whisper WER on Bahamian speech exceeds 15% target | High | High | Begin fine-tuning dataset curation immediately; establish a manual correction workflow; set up WER benchmarking pipeline before scaling |
| R-3 | Diarization fails to distinguish speakers in noisy House sessions | Medium | High | Experiment with pyannote fine-tuning on parliamentary audio; fall back to rule-based heuristic (Speaker always precedes other MPs; PLP/FNM benches are spatially separated) |
| R-4 | Sentiment model misclassifies Bahamian parliamentary tone (e.g., "friendly insults" common in Bahamian debate) | High | Medium | Build a Bahamas-specific sentiment training set; include a "Bahamian sarcasm" annotation category; accept that v1.0 sentiment will be imperfect and document limitations |
| R-5 | Alias resolution produces false positives (wrong MP attributed) | Medium | Critical | Enforce human-in-the-loop validation for low-confidence resolutions; publish resolution confidence scores alongside graph data; maintain a public errata log |
| R-6 | Low public adoption / engagement with dashboard | Medium | Medium | Partner with local journalists and civic organisations for launch; design "MP Report Card" feature for shareability; prioritise mobile usability |
| R-7 | Political backlash or pressure to take down the project | Low | High | All data is from public sources; all code is open; host outside jurisdiction if necessary; document legal basis clearly |
| R-8 | Scope creep delays v1.0 delivery | High | Medium | Strict adherence to "In Scope" boundaries; defer all v2.0 features ruthlessly; ship a working single-session demo before scaling |

---

## 15. Roadmap & Milestones

### Phase 1 — Foundation (Weeks 1–4)

| Milestone | Deliverable |
|-----------|------------|
| M-1.1 | Golden Record v1.0: All 39 MPs populated with deterministic aliases |
| M-1.2 | Miner v1.0: yt-dlp pipeline operational, 10+ sessions downloaded and catalogued |
| M-1.3 | Validation corpus: 50+ annotated mentions from 3 real House sessions |
| M-1.4 | Golden Record Resolver: Tested against validation corpus, ≥90% accuracy |

### Phase 2 — Processing Pipeline (Weeks 5–10)

| Milestone | Deliverable |
|-----------|------------|
| M-2.1 | Transcription pipeline operational: 5+ sessions transcribed with WER measured |
| M-2.2 | Diarization integrated: Speaker-attributed transcripts produced |
| M-2.3 | Entity extraction pipeline operational: Mention logs generated for 5+ sessions |
| M-2.4 | Sentiment scoring baseline: Zero-shot classifier integrated, accuracy measured |
| M-2.5 | Graph construction: First session graphs generated, centrality metrics computed |

### Phase 3 — Dashboard & Public Launch (Weeks 11–16)

| Milestone | Deliverable |
|-----------|------------|
| M-3.1 | Streamlit dashboard prototype: Single-session graph viewable |
| M-3.2 | Filtering and interactivity: Date range, party filter, node click, edge click |
| M-3.3 | Full pipeline run: All available sessions processed end-to-end |
| M-3.4 | Public beta launch: Dashboard live, open data published, methodology documented |
| M-3.5 | Community feedback mechanism live |

### Phase 4 — Refinement & Scale (Weeks 17+)

| Milestone | Deliverable |
|-----------|------------|
| M-4.1 | Whisper fine-tuning on Bahamian speech (if WER target not met) |
| M-4.2 | Sentiment model fine-tuning on Bahamian parliamentary corpus |
| M-4.3 | MP Report Card feature |
| M-4.4 | API for programmatic access to graph data |
| M-4.5 | Historical parliament ingestion (v2.0 scoping) |

---

## 16. Glossary

| Term | Definition |
|------|-----------|
| **Alias** | Any textual form by which an MP may be referenced in debate (e.g., "The Member for Cat Island," "The Prime Minister") |
| **Betweenness Centrality** | A graph metric measuring how often a node lies on the shortest path between other nodes. High betweenness = "bridge" between groups |
| **Bridge** | An MP with high betweenness centrality who connects otherwise disconnected subgroups of the House |
| **Co-reference Resolution** | The NLP task of determining that two different expressions refer to the same entity (e.g., "The Prime Minister" and "the Member who just spoke" = same person) |
| **Control Node** | The Speaker of the House, who governs debate but does not participate as a partisan actor |
| **DER (Diarization Error Rate)** | Standard metric for evaluating speaker diarization accuracy |
| **Edge** | A directed connection in the graph representing one or more mentions from a source MP to a target MP |
| **Eigenvector Centrality** | A graph metric measuring a node's influence based on the influence of its connections. High eigenvector = "Force Multiplier" |
| **Force Multiplier** | An MP with high eigenvector centrality — influential because they are connected to other influential MPs |
| **Golden Record** | The canonical entity knowledge base mapping all MPs to their aliases |
| **Hansard** | The official transcript of parliamentary proceedings (in The Bahamas, often incomplete or delayed) |
| **Isolated Node** | An MP with low degree centrality — rarely mentioned and rarely mentioning others |
| **Node** | A single MP in the interaction graph |
| **WER (Word Error Rate)** | Standard metric for evaluating speech-to-text accuracy: (insertions + deletions + substitutions) / total reference words |

---

## 17. Appendices

### Appendix A — Current Members of the House of Assembly (15th Parliament)

*To be populated in M-1.1. Will contain the full list of 39 MPs with party, constituency, and cabinet/frontbench status.*

### Appendix B — Golden Record Validation Corpus Methodology

*To be documented in M-1.3. Will describe the annotation protocol: selection of audio clips, annotator instructions, inter-annotator agreement measurement, and threshold-setting procedure.*

### Appendix C — Whisper WER Benchmarking Protocol

*To be documented in M-2.1. Will describe the test set construction, WER computation methodology, and comparison against baseline (no fine-tuning) and adapted models.*

### Appendix D — Ethical Considerations

All data processed by this system is derived from public parliamentary proceedings. MPs are public figures acting in their official capacity. The system:

- Does not surveil private communications
- Does not infer political positions not expressed in public debate
- Does not score MPs as "good" or "bad" — only describes network structure
- Publishes methodology and limitations alongside all outputs
- Welcomes corrections and provides a mechanism for MPs or their offices to flag errors

This project exists because we believe **the public has a right to understand the structure of the institution that governs them.** We build in the open because we believe transparency is not a threat to democracy — it is a prerequisite for it.

---

*End of Document — SRD v1.0*

*"The House is in session. The recorder is running. Let's map the noise."*
*— Dr. Aris Moncur*
