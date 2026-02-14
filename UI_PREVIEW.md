# Interactive Dashboard UI Preview

## Layout Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│ GraphHansard — Interactive Dashboard                                       │
│ Bahamian House of Assembly Political Network (MP-5, MP-6, MP-11)         │
├─────────────────────┬─────────────────────────────────────────────────────┤
│ Sidebar (Controls)  │ Main Content Area                                   │
├─────────────────────┼─────────────────────────────────────────────────────┤
│ Graph Controls      │ ✅ Loaded sample_session_2024_01_15 (2024-01-15)  │
│ ▼ Node Size Metric  │ 3 MPs, 4 interactions                              │
│   • Degree          │                                                     │
│                     │ ┌───────────────────────┬──────────────────────────┐│
│ □ Use Blue for FNM  │ │ Graph Visualization   │ Interaction Panel       ││
│                     │ │  (2/3 width)          │  (1/3 width)            ││
│ ───────────────────  │ │                       │                         ││
│ Interactions        │ │    🟡 Brave Davis     │ 🏛️ MP Profile          ││
│                     │ │   (PLP, PM)           │                         ││
│ ▼ Select MP         │ │      ↓ ↗              │ ### Brave Davis         ││
│   • Brave Davis     │ │      ↓   ↗            │                         ││
│   • Chester Cooper  │ │  🟡 Chester ──→  🔴   │ **Party:** PLP          ││
│   • Michael Pintard │ │   (Deputy PM)  (FNM)  │ **Constituency:**       ││
│                     │ │               Michael  │ Cat Island, Rum Cay     ││
│ ▼ Select Edge       │ │                        │ **Portfolio:**          ││
│   • Brave → Chester │ │  [Drag nodes to        │ Prime Minister          ││
│   • Brave → Michael │ │   reposition]          │                         ││
│   • ...             │ │                        │ ───────────────────     ││
│                     │ │ Legend:                │ 📊 Centrality Scores    ││
│ Session Video URL   │ │ 🟡 PLP • 🔴 FNM       │                         ││
│ [youtube.com/...]   │ │ 🟢 Pos • ⚫ Neu       │ Degree (In):     2      ││
└─────────────────────┴─│ 🔴 Neg                │ Degree (Out):    2      ││
                        │                        │ Betweenness:   1.000    ││
                        │                        │ Eigenvector:   0.707    ││
                        │                        │ Closeness:     1.000    ││
                        │                        │                         ││
                        │                        │ ───────────────────     ││
                        │                        │ 🎯 Structural Roles     ││
                        │                        │ • Force Multiplier      ││
                        │                        │ • Bridge                ││
                        │                        │ • Hub                   ││
                        └────────────────────────┴──────────────────────────┘
```

## MP-5: Node Click → MP Profile Example

When "Brave Davis" is selected:

```
┌────────────────────────────────────┐
│ 🏛️ MP Profile                     │
├────────────────────────────────────┤
│ ### Brave Davis                    │
│                                    │
│ Party: PLP                         │
│ Constituency: Cat Island, Rum Cay  │
│                and San Salvador    │
│ Portfolio: Prime Minister          │
│ Community: 0                       │
│                                    │
│ ─────────────────────────────────  │
│ 📊 Centrality Scores               │
│                                    │
│ Degree (In):     2                 │
│ Degree (Out):    2                 │
│ Betweenness:     1.000             │
│ Eigenvector:     0.707             │
│ Closeness:       1.000             │
│                                    │
│ ─────────────────────────────────  │
│ 🎯 Structural Roles                │
│ • Force Multiplier                 │
│ • Bridge                           │
│ • Hub                              │
│                                    │
│ ─────────────────────────────────  │
│ Node ID: mp_davis_brave            │
└────────────────────────────────────┘
```

## MP-6: Edge Click → Mention Details Example

When "Brave Davis → Chester Cooper" is selected:

```
┌──────────────────────────────────────────────────┐
│ 💬 Mention Details                               │
├──────────────────────────────────────────────────┤
│ ### Brave Davis → Chester Cooper                │
│                                                  │
│ Total Mentions: 5     Net Sentiment: +0.80      │
│ 🟢 Positive: 4 | ⚫ Neutral: 1 | 🔴 Negative: 0 │
│                                                  │
│ ──────────────────────────────────────────────── │
│ 📝 Individual Mentions                           │
│                                                  │
│ ▼ Mention #1 — 🟢 Positive                      │
│                                                  │
│   Raw Mention: "Deputy Prime Minister"          │
│                                                  │
│   Context:                                       │
│   > I commend the Deputy Prime Minister for     │
│     his excellent work on this initiative.      │
│                                                  │
│   Timestamp: 10.5s - 12.0s                      │
│   [▶️ Play at 10s](youtube.com/watch?v=...&t=10)│
│                                                  │
│ ▼ Mention #2 — 🟢 Positive                      │
│   ...                                            │
│                                                  │
│ ──────────────────────────────────────────────── │
│ Edge: mp_davis_brave → mp_cooper_chester        │
└──────────────────────────────────────────────────┘
```

## MP-11: Drag-and-Drop Interaction

Visual state before and after:

```
Before Drag:                    After Drag:

  🟡 A                             🟡 A ← (repositioned)
    ↓                               ↓
  🟡 B → 🔴 C                     🟡 B → 🔴 C
                                          ↑
                                    (physics recalculates)

User drags node A → Physics engine adjusts all connected edges
                 → Layout stabilizes in new configuration
```

## Features Demonstrated

### Sidebar Controls

1. **Graph Controls**
   - Node size metric selector (degree, betweenness, eigenvector, total_mentions)
   - Party color toggle (FNM: red ↔ blue)

2. **Interaction Selectors (MP-5, MP-6)**
   - MP dropdown for profile viewing
   - Edge dropdown for mention details
   - YouTube URL input for timestamp links

### Main Graph Area

- Force-directed layout with party-colored nodes
- Edge thickness by mention count
- Edge color by sentiment (🟢 green, ⚫ grey, 🔴 red)
- Draggable nodes for topology exploration
- Tooltips on hover (existing functionality)

### Interaction Panel

- **MP Profile Card (MP-5)**
  - Personal info + constituency + portfolio
  - All centrality metrics
  - Structural role badges
  - Community membership

- **Mention Details (MP-6)**
  - Aggregate statistics
  - Individual mention cards with:
    - Sentiment badge
    - Raw mention text
    - Context window
    - Timestamps
    - **YouTube links** (jump to video)

## Color Scheme

- **Party Colors**: 🟡 PLP (Gold), 🔴 FNM (Red), ⚫ COI (Grey)
- **Sentiment**: 🟢 Positive, ⚫ Neutral, 🔴 Negative
- **Backgrounds**: Clean white panels with subtle borders
- **Text**: Dark grey for readability

## Responsive Design

- Two-column layout on desktop (graph 2/3, panel 1/3)
- Sidebar collapses on mobile
- Graph adjusts to container width
- Panel scrolls independently

## Accessibility

- Emoji indicators for visual distinction
- Text labels supplement colors
- High contrast text
- Keyboard navigation support (Streamlit default)
- Screen reader compatible (ARIA labels via Streamlit)
