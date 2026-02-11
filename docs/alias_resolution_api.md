# Alias Resolution API

The Alias Resolution API provides a robust mechanism for resolving raw mention strings from parliamentary debate to canonical MP node IDs.

## Features

- **Exact Matching**: Case-insensitive, whitespace-normalized exact match against 386+ unique aliases
- **Fuzzy Matching**: RapidFuzz-based fuzzy matching (token_sort_ratio ≥ 85) for handling typos and transcription errors
- **Temporal Disambiguation**: Portfolio-based aliases filtered by debate date to handle cabinet reshuffles
- **Collision Detection**: Automatically detects and flags known alias collisions with resolution strategies
- **Confidence Scores**: Returns confidence scores (1.0 for exact, 0.85-1.0 for fuzzy, 0.0 for unresolved)
- **Unresolved Logging**: Logs all unresolved mentions for human review

## Quick Start

```python
from graphhansard.golden_record import AliasResolver

# Initialize the resolver
resolver = AliasResolver("golden_record/mps.json")

# Resolve a simple mention
result = resolver.resolve("Brave Davis")
print(result.node_id)  # mp_davis_brave
print(result.confidence)  # 1.0
print(result.method)  # "exact"

# Fuzzy match with typo
result = resolver.resolve("Chestor Cooper")
print(result.node_id)  # mp_cooper_chester
print(result.method)  # "fuzzy"
print(result.confidence)  # 0.93

# Temporal disambiguation
result = resolver.resolve("Minister of Works", debate_date="2023-08-01")
print(result.node_id)  # mp_sears_alfred (before reshuffle)

result = resolver.resolve("Minister of Works", debate_date="2023-10-01")
print(result.node_id)  # mp_sweeting_clay (after reshuffle)
```

## Resolution Cascade

The resolver implements a three-stage cascade (SRD §6.4):

1. **Exact Match** — Normalized lookup in inverted alias index with temporal filtering
2. **Fuzzy Match** — RapidFuzz token_sort_ratio against all aliases (threshold ≥ 85)
3. **Unresolved** — Return null and log for human review

## API Reference

### `AliasResolver`

#### `__init__(golden_record_path: str, fuzzy_threshold: int = 85)`

Initialize the resolver.

**Parameters:**
- `golden_record_path`: Path to mps.json
- `fuzzy_threshold`: Minimum score for fuzzy matches (0-100), default 85

#### `resolve(mention: str, debate_date: str | None = None) -> ResolutionResult`

Resolve a raw mention string to an MP node_id.

**Parameters:**
- `mention`: Raw text mention (e.g., "da Memba for Cat Island")
- `debate_date`: Optional ISO date (YYYY-MM-DD) for temporal disambiguation

**Returns:** `ResolutionResult` with:
- `node_id`: The resolved MP node_id or None if unresolved
- `confidence`: Float 0.0-1.0 (1.0 for exact, 0.85-1.0 for fuzzy, 0.0 for unresolved)
- `method`: "exact" | "fuzzy" | "unresolved"
- `collision_warning`: Optional warning message for known collisions

#### `save_index(output_path: str)`

Save the inverted alias index to a JSON file.

#### `save_unresolved_log(output_path: str)`

Save the unresolved mentions log to a JSON file.

## Known Alias Collisions

The system handles 6 known alias collisions:

1. **"Doc"** — Michael Darville (PLP) vs Hubert Minnis (FNM)
2. **"Adrian"** — Adrian White (FNM, St. Anne's) vs Adrian Gibson (FNM, Long Island)
3. **"Minister of Works"** — Alfred Sears (until 2023-09-03) vs Clay Sweeting (from 2023-09-03)
4. **"Minister of Housing"** — JoBeth Coleby-Davis (until 2023-09-03) vs Keith Bell (from 2023-09-03)
5. **"Minister of Agriculture"** — Clay Sweeting (until 2023-09-03) vs Jomo Campbell (from late 2023)
6. **"Lightbourne"** — Leonardo Lightbourne (North Andros) vs Zane Lightbourne (Yamacraw)

See `golden_record/mps.json` → `alias_collisions` for resolution strategies.

## Examples

See `scripts/example_resolver_usage.py` for complete working examples.

## Testing

Run the test suite:

```bash
pytest tests/test_alias_resolver.py -v
```

30 tests cover:
- Exact matching (case-insensitive, constituency, portfolio, honorific)
- Fuzzy matching (typos, variations)
- Temporal disambiguation (all 3 known portfolio reshuffles)
- Collision handling
- Confidence scores
- Unresolved logging

## Performance

- Index building: ~50ms for 39 MPs, 386 aliases
- Exact match: O(1) hash lookup
- Fuzzy match: O(n×m) where n = MPs, m = avg aliases per MP (~10)

## Implementation Details

- **Normalization**: Lowercase + strip whitespace
- **Fuzzy Algorithm**: RapidFuzz `token_sort_ratio` (handles word order, partial matches)
- **Temporal Filtering**: Uses `PortfolioTenure.is_active_on()` for date-based filtering
- **Collision Strategy**: Returns first candidate with warning; manual review recommended

## Related

- SRD §6.4 (Alias Resolution Logic)
- Issue #18 (GR: Alias Resolution API)
- `golden_record/mps.json` (canonical entity knowledge base)
