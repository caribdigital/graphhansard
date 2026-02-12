# Golden Record Validation Corpus

This directory contains the manually annotated validation corpus used to benchmark alias resolution accuracy.

## Files

- **`annotated_mentions.json`**: The corpus of 55+ manually annotated MP mentions from real House of Assembly sessions
- **`.gitkeep`**: Placeholder to track this directory in git

## Quick Start

Run validation:

```bash
python scripts/validate_corpus.py
```

Run tests:

```bash
pytest tests/test_validation_corpus.py -v
```

## Current Metrics

✓ **PASSED** - Exceeds SRD §6.5 requirement (90%+ precision and recall)

- **Precision**: 100.0%
- **Recall**: 98.2%
- **F1 Score**: 99.1%
- **Total Mentions**: 55

## Documentation

See [docs/validation_corpus.md](../../docs/validation_corpus.md) for complete documentation including:

- Annotation methodology
- Corpus structure
- Mention type distribution
- Temporal disambiguation test cases
- Known limitations and future improvements

## Related

- **SRD §6.5**: Validation Requirement
- **Issue #19**: GR: Golden Record Validation Corpus
