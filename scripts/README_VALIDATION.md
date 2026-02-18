# Output Validation

This module provides quality validation for session graph outputs to catch data quality issues immediately after processing.

## Overview

The `validate_output()` function performs 6 validation checks on session graphs:

1. **Enrichment**: At least 1 node has `party != "Unknown"` (MP registry worked)
2. **Common names**: No node with `common_name == node_id` when node_id starts with `mp_` (name resolution worked)
3. **Procedural edges**: At least 1 edge has `is_procedural == True` (GR-7 tagging worked)
4. **Sentiment distribution**: Not >80% positive across all edges (bias check)
5. **Node count**: At least 5 nodes per session (minimum viable graph)
6. **Edge count**: At least 3 edges per session

## Usage

### Command Line

The validation is integrated into the CLI commands and runs automatically after graph building:

```bash
# Build graph with validation (default)
python -m graphhansard.brain build-graph mentions.json --session-id S001 --date 2024-01-15

# Build graph without validation
python -m graphhansard.brain build-graph mentions.json --session-id S001 --date 2024-01-15 --skip-validation

# Full pipeline with validation
python -m graphhansard.brain process audio.mp3 --session-id S001 --golden-record mps.json
```

### Python API

```python
from graphhansard.brain.validation import validate_output

# Validate a session graph
report = validate_output(
    session_graph=session_graph,  # dict or pydantic model
    session_id="S001",
    output_dir="output"  # optional, saves validation_{session_id}.json
)

# Check overall status
if report.overall_status == "FAIL":
    print("Validation failed!")
    for check in report.checks:
        if check.status == "FAIL":
            print(f"  {check.check_name}: {check.message}")
```

## Output

### Console Output

The validation prints a clear report to console:

```
======================================================================
VALIDATION REPORT: S001
======================================================================
  [PASS] [OK] enrichment: 38/38 nodes have party information
  [PASS] [OK] common_names: All MP nodes have resolved common names
  [PASS] [OK] procedural_edges: 12/45 edges are procedural
  [PASS] [OK] sentiment_distribution: Sentiment distribution acceptable (65.3% positive)
  [PASS] [OK] node_count: Session has 38 nodes (minimum: 5)
  [PASS] [OK] edge_count: Session has 45 edges (minimum: 3)
----------------------------------------------------------------------
  OVERALL: PASS
======================================================================

Validation report saved: output/validation_S001.json
```

### JSON Report

A JSON validation report is saved alongside the output:

```json
{
  "session_id": "S001",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": [
    {
      "check_name": "enrichment",
      "status": "PASS",
      "message": "38/38 nodes have party information",
      "details": {
        "enriched_count": 38,
        "total_count": 38
      }
    },
    ...
  ],
  "overall_status": "PASS"
}
```

## Status Levels

- **PASS**: Check passed, no issues detected
- **WARN**: Check found potential issues, but pipeline continues
- **FAIL**: Check failed, indicating serious data quality problems

The validation is **non-blocking** - warnings and failures are logged but don't stop the pipeline.

## Integration

The validation is automatically called in two places:

1. `build-graph` command - After building a single session graph
2. `process` command - After the full end-to-end pipeline completes

Both commands support `--skip-validation` to disable validation if needed.

## Testing

Run the validation tests:

```bash
pytest tests/test_output_validation.py -v
```

## Dependencies

The validation module only requires:
- `pydantic>=2.0` - for data models

No heavy dependencies (NumPy, PyTorch, etc.) are needed, making it lightweight and fast.
