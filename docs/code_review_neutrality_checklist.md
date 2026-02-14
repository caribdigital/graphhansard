# Code Review Checklist: Framing Neutrality

**Purpose:** Ensure all code changes maintain neutral, descriptive framing per NF-16  
**Implements:** SRD §12.5 (Legal & Ethical) - NF-16  
**Last Updated:** February 2026

## Neutral Framing Requirements

All code, UI text, and documentation must:
1. Present data and computed metrics, not editorial conclusions
2. Avoid value judgments or loaded language
3. Use factual descriptions only
4. Describe structural roles neutrally using standard graph theory terminology

## Pre-Merge Checklist

Before merging any PR, verify the following:

### ✅ Dashboard UI Text

- [ ] No editorial language ("good", "bad", "corrupt", "lazy", "incompetent")
- [ ] No loaded terms ("power broker", "kingmaker", "puppet", "stooge")
- [ ] Metrics presented with factual descriptions
- [ ] Structural roles use standard network analysis terms (per SRD Glossary)
- [ ] Disclaimers present where metrics are displayed

### ✅ Documentation

- [ ] Plain language explanations avoid value judgments
- [ ] Limitations clearly stated
- [ ] "What we don't measure" sections included where relevant
- [ ] Attribution and provenance documented
- [ ] No claims of measuring "effectiveness" or "performance"

### ✅ API & Data Exports

- [ ] Field names are descriptive, not judgmental
- [ ] CSV/JSON headers include disclaimers
- [ ] Metadata clearly states data is descriptive, not prescriptive
- [ ] No "score" or "rating" terminology (use "metric" or "measure")

### ✅ Code Comments

- [ ] Technical comments focus on methodology, not interpretation
- [ ] Avoid phrases like "good MP", "bad actor", "suspicious behavior"
- [ ] Use "high centrality" not "influential" (unless mathematically defined)
- [ ] Use "low degree" not "inactive" or "disengaged"

## Approved Terminology

### ✅ Acceptable (Neutral)

**Structural Roles** (per SRD BR-26):
- "Force Multiplier" (high eigenvector centrality) — standard graph theory term
- "Bridge" (high betweenness centrality) — standard graph theory term
- "Hub" (high in-degree) — standard graph theory term
- "Isolated Node" (low degree centrality) — standard graph theory term

**Metrics & Descriptions**:
- Degree centrality (in/out)
- Betweenness centrality
- Eigenvector centrality
- Closeness centrality
- Mention count
- Sentiment score (positive/neutral/negative)
- Interaction frequency
- Network position
- Structural properties
- Observable patterns

**Contextual Phrases**:
- "High betweenness suggests the MP connects different groups"
- "Low degree indicates fewer direct mentions in debate"
- "Positive sentiment reflects favorable language in references"
- "Centrality metrics describe network structure"

### ❌ Unacceptable (Editorial)

**Value Judgments**:
- "Good MP" / "Bad MP"
- "Effective" / "Ineffective"
- "Hardworking" / "Lazy"
- "Competent" / "Incompetent"
- "Honest" / "Corrupt"
- "Strong leader" / "Weak leader"

**Loaded Interpretations**:
- "Power broker" (use "high betweenness centrality")
- "Kingmaker" / "Powerless"
- "Puppet" / "Master"
- "Manipulator" / "Victim"
- "Rising star" / "Has-been"

**Prescriptive Language**:
- "Should have higher centrality"
- "Needs to engage more"
- "Is failing their constituents"
- "Outperforms peers"

## Review Process

### For Code Authors

Before submitting a PR:
1. Read through all user-facing text
2. Check against the "Unacceptable" list above
3. Replace any editorial language with neutral descriptions
4. Ensure disclaimers are present where metrics are displayed

### For Code Reviewers

When reviewing PRs:
1. Check all new UI text against this checklist
2. Verify documentation additions maintain neutrality
3. Confirm no new "score" or "rating" terminology introduced
4. Ensure any new metrics include appropriate context and disclaimers

### Flag for Discussion

If you're unsure whether a term is neutral:
1. Check if it's defined in the SRD Glossary (§16) — if yes, it's approved
2. Check if it's a standard graph theory or network analysis term — if yes, likely acceptable
3. Ask: "Does this describe what we observe, or does it judge whether it's good/bad?"
4. When in doubt, tag the project lead for clarification

## Examples

### ❌ Non-Neutral → ✅ Neutral

**Example 1:**
- ❌ "MP Davis is a powerful force in parliament"
- ✅ "MP Davis has high eigenvector centrality (Force Multiplier role)"

**Example 2:**
- ❌ "MP Smith is ineffective and rarely participates"
- ✅ "MP Smith has low degree centrality (0 outgoing mentions in this session)"

**Example 3:**
- ❌ "This shows Minister Jones is manipulating the debate"
- ✅ "Minister Jones has high betweenness centrality (Bridge role)"

**Example 4:**
- ❌ "Top 5 Best-Performing MPs"
- ✅ "Top 5 MPs by Degree Centrality"

**Example 5:**
- ❌ "Cross-party collaboration is declining (bad for democracy)"
- ✅ "Cross-party edge density decreased from 0.45 to 0.32"

## Rationale

From SRD §12.5 (NF-16):
> "The system presents data and computed metrics, not editorial conclusions; framing must be neutral"

From SRD Appendix D (Ethical Considerations):
> "Does not score MPs as 'good' or 'bad' — only describes network structure"

**Why this matters:**
- GraphHansard is a transparency tool, not a judgment tool
- Neutral framing respects democratic processes
- Editorial language undermines scientific credibility
- Citizens deserve data, not opinions disguised as data

## Questions or Updates?

If you believe this checklist needs updating:
1. Open a GitHub issue with the proposed change
2. Provide rationale for why the change improves neutrality
3. Tag with label: `documentation` and `ethics`

---

**Document License:** CC-BY-4.0  
**Maintained by:** GraphHansard Core Team  
**Review Frequency:** Quarterly or as-needed
