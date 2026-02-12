# Community Contributions Guide

This document describes how to contribute alias additions and corrections to the GraphHansard Golden Record (GR-9).

## Overview

The Golden Record maintains a comprehensive knowledge base of all Members of Parliament and their aliases. Community members can suggest new aliases or corrections to existing ones through a structured submission process.

**Important:** All submissions go through a review queue. They are **not** automatically merged into the Golden Record.

## Submission Format

All submissions must include:

1. **contribution_type**: Either `alias_addition` or `alias_correction`
2. **proposed_alias**: The alias you're suggesting (e.g., "Papa", "The PM")
3. **target_node_id**: The MP this alias refers to (e.g., `mp_davis_brave`)
4. **source_evidence**: Evidence supporting this alias (URL, citation, description)
5. **submitter_name**: Your name (or "Anonymous")

Optional fields:
- **submitter_email**: Email for follow-up (optional)
- **notes**: Additional context (optional)

## How to Submit

### Method 1: Command-Line Tool (Recommended)

Use the `submit_alias.py` script:

```bash
python scripts/submit_alias.py \
  --type alias_addition \
  --alias "Papa" \
  --target mp_davis_brave \
  --evidence "Used in House debate 2024-01-15, video at https://youtube.com/watch?v=..." \
  --submitter "Your Name"
```

With optional fields:

```bash
python scripts/submit_alias.py \
  --type alias_addition \
  --alias "Papa" \
  --target mp_davis_brave \
  --evidence "https://youtube.com/watch?v=..." \
  --submitter "Your Name" \
  --email "your.email@example.com" \
  --notes "Heard this nickname used multiple times in recent debates"
```

### Method 2: Interactive Mode

Run the script without arguments for interactive prompts:

```bash
python scripts/submit_alias.py
```

You'll be prompted for each field.

### Method 3: Direct JSON Submission

Create a JSON file following the [submission schema](schemas/alias-submission-schema.json):

```json
{
  "contribution_type": "alias_addition",
  "proposed_alias": "Papa",
  "target_node_id": "mp_davis_brave",
  "source_evidence": "Used frequently in House debates, https://youtube.com/watch?v=example",
  "submitter_name": "Jane Doe",
  "submitter_email": "jane@example.com",
  "notes": "This nickname is commonly used by both government and opposition MPs"
}
```

Then submit it (implementation-specific).

## Finding MP Node IDs

To find the correct `node_id` for an MP:

1. Check `golden_record/mps.json` - search for the MP's name
2. Use the export tool:
   ```bash
   python scripts/export_golden_record.py --format csv
   ```
   Open the CSV and find the MP's `node_id`.

Node IDs follow the pattern: `mp_lastname_firstname` (e.g., `mp_davis_brave`, `mp_cooper_chester`)

## Evidence Requirements

Good evidence includes:

- **Parliamentary video URLs** with timestamp (preferred)
  - Example: `https://youtube.com/watch?v=ABC123&t=4523s (at 1:15:23)`
- **Hansard citations** (if available)
  - Example: `Hansard, 2024-03-12, page 45`
- **News articles** quoting parliamentary usage
  - Example: `The Tribune, 2024-01-15: "...referred to as 'Papa' by the Opposition Leader"`
- **Detailed descriptions** (minimum 10 characters)
  - Example: `Common nickname used by both government and opposition MPs in informal debate`

## Review Process

1. Your submission is added to `contributions_queue.json`
2. A maintainer reviews your submission:
   - Verifies the alias is correct
   - Checks the evidence
   - Confirms the target MP
3. The submission is either:
   - **Approved**: Alias will be added to the Golden Record in the next update
   - **Rejected**: You'll be notified with the reason

## Checking Submission Status

Maintainers can review the queue using:

```bash
# List all submissions
python scripts/review_submissions.py --list

# Check statistics
python scripts/review_submissions.py --stats

# Review a specific submission
python scripts/review_submissions.py --review sub_20260212_140530_123456
```

## Submission Guidelines

### DO:
- Provide specific evidence (URLs, citations)
- Use the MP's official `node_id`
- Submit one alias per submission
- Include context in the notes field if helpful

### DON'T:
- Submit aliases without evidence
- Submit offensive or inappropriate content
- Submit aliases for non-MPs or private citizens
- Submit speculative or unverified aliases

## Examples

### Example 1: Common Nickname

```bash
python scripts/submit_alias.py \
  --type alias_addition \
  --alias "Papa" \
  --target mp_davis_brave \
  --evidence "Used by opposition MPs in debate, https://youtube.com/watch?v=ABC&t=1234" \
  --submitter "Community Observer"
```

### Example 2: Portfolio Abbreviation

```bash
python scripts/submit_alias.py \
  --type alias_addition \
  --alias "Min of Works" \
  --target mp_sweeting_clay \
  --evidence "Common abbreviation used in House proceedings" \
  --submitter "Jane Doe" \
  --notes "Informal shorthand used when speaking quickly"
```

### Example 3: Correction

```bash
python scripts/submit_alias.py \
  --type alias_correction \
  --alias "The Honourable Member for Exuma" \
  --target mp_cooper_chester \
  --evidence "Correct constituency is 'Exumas and Ragged Island' per official record" \
  --submitter "Fact Checker"
```

## Data License

All community contributions become part of the Golden Record dataset, which is licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). By submitting, you agree to license your contribution under CC-BY-4.0.

## Questions?

- Check the [SRD v1.0](SRD_v1.0.md) for technical details
- Review existing aliases in `golden_record/mps.json`
- Open an issue on GitHub for questions about specific submissions

---

**Last updated:** February 2026  
**Implements:** GR-9 (Community Contributions)  
**Schema:** [alias-submission-schema.json](schemas/alias-submission-schema.json)
