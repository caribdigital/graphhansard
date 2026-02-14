# Methodology

**Document Status:** FINAL  
**Version:** 1.0  
**Last Updated:** February 2026  
**Implements:** NF-17 (Transparent Methodology)  
**Target Reading Level:** Grade 10

## Overview

This document explains how GraphHansard works in plain language. If you're a citizen, journalist, or researcher who wants to understand what we're measuring and how we're measuring it, this is for you.

## What GraphHansard Does

GraphHansard turns parliamentary speech into data. Specifically, we:

1. **Record who speaks in parliament** by downloading public parliamentary audio
2. **Figure out who said what** using speech-to-text technology
3. **Track who mentions whom** by detecting when one MP refers to another
4. **Measure interaction patterns** by building a network graph of these references
5. **Display the results** in an interactive web dashboard

The output is a **political interaction network**: a map showing which Members of Parliament (MPs) talk to each other, how often, and with what tone.

## The Full Pipeline

### Step 1: Audio Ingestion (The Miner)

**What we do:**  
Download public parliamentary session recordings from YouTube.

**How we do it:**  
We use a tool called `yt-dlp` (a free, open-source downloader) to grab audio from the official Bahamian House of Assembly YouTube channel.

**What we store:**
- The audio file (WAV format)
- Metadata: date, session ID, source URL, duration

**Key point:** We only download publicly available recordings. No private meetings, no leaked audio, no Freedom of Information requests. If you can watch it on YouTube without logging in, we can process it.

---

### Step 2: Transcription and Diarization (The Brain — Part 1)

**What we do:**  
Convert audio to text and identify who spoke when.

**How we do it:**  
We use two AI models:

1. **Whisper (by OpenAI)**: Converts speech to text. It's like YouTube's auto-captions, but more accurate.
2. **Pyannote**: Identifies different speakers and timestamps when each person talks.

We then merge these outputs to create a transcript where each sentence is labeled with the speaker and timestamp.

**What we store:**
- Timestamped transcript (who said what, and when)
- Speaker labels (initially anonymous: "Speaker 1", "Speaker 2", etc.)

**Key point:** This step doesn't know who the MPs are yet. It just knows "someone spoke from 01:23 to 01:45."

---

### Step 3: Speaker Identification (The Brain — Part 2)

**What we do:**  
Figure out which speaker label corresponds to which MP.

**How we do it:**  
We use the **Golden Record** — our database of all 39 MPs and their aliases. Examples:
- "The Member for Cat Island" → Brave Davis (Prime Minister)
- "The Leader of the Opposition" → Michael Pintard (FNM Leader)
- "Papa" → Brave Davis (nickname)

The system looks for these identifying phrases in the transcript and uses them to label speakers. If "Speaker 1" is introduced as "The Prime Minister," we know that's Brave Davis.

**What we store:**
- Updated transcript with real MP names instead of generic speaker labels

**Key point:** This is fuzzy matching, not perfect. We use confidence scores and human review to catch errors.

---

### Step 4: Entity Extraction (The Brain — Part 3)

**What we do:**  
Detect every time one MP mentions another MP.

**How we do it:**  
We scan each MP's speech for references to other MPs. These can be:
- Direct names: "I agree with Mr. Pintard"
- Titles: "The Minister of Finance said..."
- Pronouns: "He makes a good point" (requires co-reference resolution)

We use **spaCy** (an NLP library) to detect names, plus custom rules for Bahamian parliamentary conventions (e.g., "The Honourable Member").

**What we store:**
- A list of edges: (Source MP, Target MP, Timestamp, Mention Type)

**Key point:** We only count explicit mentions. We don't infer relationships from body language, seating arrangements, or off-mic conversations.

---

### Step 5: Sentiment Analysis (The Brain — Part 4)

**What we do:**  
Score whether each mention is positive, neutral, or negative.

**How we do it:**  
We use a **transformer model** (a type of AI trained on millions of text samples) to classify the tone of the sentence containing the mention. Examples:

- **Positive:** "I commend the Prime Minister for his leadership."
- **Neutral:** "The Minister of Finance stated the GDP figures."
- **Negative:** "The Member opposite is misleading the House."

The model outputs a score from -1 (very negative) to +1 (very positive).

**What we store:**
- Sentiment score for each mention

**Key point:** Bahamian parliamentary speech often uses sarcasm and culturally specific expressions. The model is trained on general English, not Bahamian Creole or parliamentary rhetoric. We document this limitation below.

---

### Step 6: Graph Construction (The Brain — Part 5)

**What we do:**  
Build a network graph where each MP is a node, and each mention is an edge.

**How we do it:**  
We use **NetworkX** (a Python library for graph analysis) to create the network. Each edge has:
- **Weight:** Total number of mentions (Source → Target)
- **Sentiment:** Average sentiment score across all mentions

We then compute **centrality metrics** for each node:

1. **Degree Centrality:** How many other MPs does this person mention/get mentioned by?
2. **Betweenness Centrality:** How often does this person connect otherwise disconnected groups? (Bridge role)
3. **Eigenvector Centrality:** Is this person connected to other highly connected people? (Force Multiplier role)
4. **Closeness Centrality:** How "close" is this person to everyone else in the network?

**What we store:**
- Graph file (JSON format) with nodes, edges, and metrics

**Key point:** These are mathematical measures of network structure. They describe patterns, not intentions. High betweenness doesn't mean someone is a "power broker" — it just means they structurally connect different groups.

---

### Step 7: Visualization (The Map)

**What we do:**  
Display the graph in an interactive web dashboard.

**How we do it:**  
We use **Streamlit** (web framework) and **PyVis** (graph visualization) to create a browser-based tool where you can:
- See MPs as colored nodes (color = party affiliation)
- See mentions as lines between nodes (thickness = mention count)
- Filter by date, party, or individual MP
- Click on an MP to see their detailed metrics

**What you can explore:**
- Which MPs are most central in debate?
- Are there cross-party conversations, or is debate polarized?
- How does an MP's role change over time?

**Key point:** This is a tool for exploration, not a "score" of MP performance. There is no "best" or "worst" centrality. Some MPs are backbenchers by design. Some MPs are ministers who speak on every issue. Context matters.

---

## Key Metrics Explained

### Degree Centrality
- **What it measures:** How many connections an MP has.
- **In-Degree:** How often they are mentioned by others.
- **Out-Degree:** How often they mention others.
- **Interpretation:** High in-degree might mean an MP is a focus of attention (e.g., Prime Minister, opposition leader). High out-degree might mean an MP is active in debate.

### Betweenness Centrality
- **What it measures:** How often an MP lies on the shortest path between two other MPs.
- **Interpretation:** High betweenness suggests the MP connects different factions or groups. In parliamentary terms, this could be a cross-party negotiator or a backbencher who bridges regional interests.

### Eigenvector Centrality
- **What it measures:** Whether an MP is connected to other well-connected MPs.
- **Interpretation:** High eigenvector suggests influence through association. If the Prime Minister mentions you, your eigenvector score rises.

### Closeness Centrality
- **What it measures:** How "close" an MP is to all other MPs in the network.
- **Interpretation:** High closeness suggests an MP is well-integrated into the debate structure.

---

## Limitations and Caveats

We are transparent about what this system can and cannot do. Here are the key limitations:

### 1. Transcription Accuracy

**Issue:** Speech-to-text models are not 100% accurate.

**Impact:**
- Background noise, crosstalk, and audio quality affect transcription.
- Bahamian accents and Creole expressions may be misrecognized by models trained on Standard American/British English.
- Target Word Error Rate: ≤15% (we're working to measure this on a validation corpus).

**What this means for you:**  
Individual transcription errors do exist. Aggregate patterns (e.g., "MP X mentions MP Y frequently") are more reliable than individual sentence-level quotes.

**Mitigation:**  
We provide links to original audio. If a claim seems off, you can verify it yourself.

---

### 2. Sentiment Model Limitations

**Issue:** Sentiment analysis models struggle with sarcasm, cultural context, and parliamentary conventions.

**Impact:**
- A sarcastic compliment ("The Member opposite is brilliantly wrong") might be scored as positive.
- Bahamian Creole expressions may not be understood by the model.
- Parliamentary language is formal and often indirect, which confuses general-purpose sentiment models.

**What this means for you:**  
Sentiment scores are rough indicators, not definitive judgments. Use them to spot patterns, not to evaluate individual exchanges.

**Mitigation:**  
We are working on fine-tuning the sentiment model on Bahamian parliamentary speech. We welcome contributions of labeled examples.

---

### 3. Alias Resolution Confidence

**Issue:** Figuring out who said what is probabilistic, not certain.

**Impact:**
- If an MP is not introduced clearly, we might mis-attribute their speech.
- MPs with common names or overlapping constituencies require careful disambiguation.

**What this means for you:**  
Each speaker identification has a confidence score. Low-confidence segments are flagged for manual review.

**Mitigation:**  
We maintain a comprehensive Golden Record of aliases and validate it against real parliamentary sessions.

---

### 4. Audio Quality Impact

**Issue:** Not all parliamentary recordings are high quality.

**Impact:**
- Older sessions, technical glitches, or poor microphone placement reduce transcription accuracy.
- Sessions with frequent interruptions or crosstalk are harder to process.

**What this means for you:**  
Some sessions will have better data quality than others. We tag each session with an audio quality rating (good/fair/poor).

**Mitigation:**  
We prioritize high-quality sessions for analysis. If we can't reliably process a session, we don't include it rather than publish low-confidence data.

---

### 5. What We Don't Measure

This system does **not** measure:

- **Policy positions:** We track mentions, not voting records or policy stances.
- **Effectiveness:** We don't score whether an MP is "good" or "bad" at their job.
- **Private influence:** We only see public debate. Backroom negotiations, committee work, and constituency service are invisible to this system.
- **Intent:** We measure structure, not motivation. High betweenness doesn't mean someone is "manipulating" the system — it's a mathematical property of the network.

---

## How to Use This Data Responsibly

### For Citizens
- Use this tool to see who your MP interacts with, but remember that participation patterns alone don't tell you if they're serving your interests.
- Context matters: A backbencher with low centrality might be doing excellent constituency work outside the House.

### For Journalists
- Use this data as a starting point for investigation, not a conclusion.
- Always verify individual claims by listening to the original audio.
- Be cautious about interpreting sentiment scores without listening to the tone and context.

### For Researchers
- This dataset is suitable for aggregate analysis (e.g., "Are cross-party interactions declining over time?").
- Individual-level claims require validation against ground truth (e.g., comparing transcripts to official Hansard).
- Cite limitations when publishing findings.

---

## Open Methodology = Reproducible Results

The entire GraphHansard pipeline is open source:

- **Code:** https://github.com/caribdigital/graphhansard
- **Data:** All processed datasets are published under CC-BY-4.0
- **Models:** We document which AI models we use (Whisper, Pyannote, transformer sentiment models)
- **Validation Corpus:** We publish a test set so others can benchmark accuracy

If you disagree with our results, you can:
1. Download the code
2. Download the same audio files we used
3. Run the pipeline yourself
4. Compare your results to ours

This is how science works. Transparency enables accountability.

---

## Questions or Corrections?

If you find an error, have a question, or want to suggest improvements:

- **GitHub Issues:** https://github.com/caribdigital/graphhansard/issues
- **Community Contributions:** See [community_contributions.md](community_contributions.md)
- **Contact:** Maintainers are listed in the repository README

We are committed to continuous improvement and welcome constructive feedback.

---

**Document License:** CC-BY-4.0  
**Attribution:** GraphHansard / Carib Digital Labs  
**Last Review:** February 2026  
**Next Review:** September 2026 (or upon major methodology changes)
