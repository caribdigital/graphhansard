# Data Export Guide

This document describes how to export the GraphHansard Golden Record in multiple formats (GR-10).

## Overview

The Golden Record can be exported in three formats:

1. **JSON** - Canonical format with full metadata
2. **CSV** - Flattened format, one row per MP
3. **Alias Index JSON** - Inverted index mapping aliases to MPs

All exports include metadata headers (version, date, parliament).

## Quick Start

Export all formats at once:

```bash
python scripts/export_golden_record.py
```

This creates three files in the `exports/` directory:
- `golden_record_YYYYMMDD_HHMMSS.json`
- `golden_record_YYYYMMDD_HHMMSS.csv`
- `golden_record_alias_index_YYYYMMDD_HHMMSS.json`

## Export Formats

### 1. JSON Export

The JSON export preserves the complete Golden Record structure with an optional metadata wrapper.

**Usage:**

```bash
python scripts/export_golden_record.py --format json
```

**Structure:**

```json
{
  "export_metadata": {
    "exported_at": "2026-02-12T14:00:00.000000+00:00",
    "export_format": "json",
    "source_file": "mps.json",
    "golden_record_version": "1.0.0"
  },
  "golden_record": {
    "metadata": { ... },
    "mps": [ ... ],
    "deceased_mps": [ ... ],
    "senate_cabinet_members": [ ... ],
    "alias_collisions": [ ... ]
  }
}
```

**Use Cases:**
- Backup and versioning
- Integration with other systems
- Independent analysis
- Archival

### 2. CSV Export

The CSV export provides a flattened, human-readable format with one row per MP.

**Usage:**

```bash
python scripts/export_golden_record.py --format csv
```

**Columns:**
- `node_id` - Unique identifier
- `full_name` - Legal full name
- `common_name` - Name in common usage
- `party` - Political party (PLP, FNM, COI, IND)
- `constituency` - Electoral district
- `is_cabinet` - Cabinet member (True/False)
- `is_opposition_frontbench` - Opposition frontbench (True/False)
- `gender` - Gender (M/F/X)
- `node_type` - Node type (debater/control)
- `seat_status` - Seat status (active/resigned/deceased/suspended)
- `current_portfolio` - Current portfolio (if any)
- `total_aliases` - Total number of aliases
- `sample_aliases` - First 5 aliases (pipe-separated)

**Header Comments:**
```csv
# Golden Record Export - 14th Parliament of The Bahamas
# Version: 1.0.0
# Exported: 2026-02-12T14:00:00.000000+00:00
# Total MPs: 39
```

**Example Row:**
```csv
mp_davis_brave,"Philip Edward Davis, K.C.",Brave Davis,PLP,"Cat Island, Rum Cay and San Salvador",True,False,M,debater,active,Prime Minister,13,Brave | Papa | Brave Davis | Philip Davis | Davis KC
```

**Use Cases:**
- Spreadsheet analysis (Excel, Google Sheets)
- Quick reference lookup
- Data visualization
- Public distribution

### 3. Alias Index Export

The alias index export provides an inverted index mapping normalized aliases to MP node IDs.

**Usage:**

```bash
python scripts/export_golden_record.py --format alias_index
```

**Structure:**

```json
{
  "metadata": {
    "exported_at": "2026-02-12T14:00:00.000000+00:00",
    "export_format": "alias_index",
    "golden_record_version": "1.0.0",
    "parliament": "14th Parliament of The Bahamas",
    "parliament_start": "2021-09-16",
    "total_aliases": 386,
    "alias_collisions": 15
  },
  "alias_index": {
    "brave": ["mp_davis_brave"],
    "papa": ["mp_davis_brave"],
    "prime minister": ["mp_davis_brave"],
    "the prime minister": ["mp_davis_brave"],
    ...
  }
}
```

**Notes:**
- All aliases are normalized (lowercase, trimmed)
- Multiple node IDs indicate alias collisions
- Includes all aliases (manual + generated)

**Use Cases:**
- Entity resolution testing
- Alias lookup services
- Collision detection
- Integration with NLP pipelines

## Advanced Usage

### Custom Output Directory

Specify a custom output directory:

```bash
python scripts/export_golden_record.py --output-dir /path/to/exports
```

### Custom Filename Prefix

Use a custom prefix for filenames:

```bash
python scripts/export_golden_record.py --prefix my_export
```

This creates:
- `my_export_YYYYMMDD_HHMMSS.json`
- `my_export_YYYYMMDD_HHMMSS.csv`
- `my_export_alias_index_YYYYMMDD_HHMMSS.json`

### Export Single Format

Export only one format:

```bash
# JSON only
python scripts/export_golden_record.py --format json

# CSV only
python scripts/export_golden_record.py --format csv

# Alias index only
python scripts/export_golden_record.py --format alias_index
```

## Programmatic Usage

You can also use the exporter in Python code:

```python
from graphhansard.golden_record.exporter import GoldenRecordExporter

# Create exporter
exporter = GoldenRecordExporter("golden_record/mps.json")

# Export all formats
exports = exporter.export_all("exports/")
print(exports)  # {'json': '...', 'csv': '...', 'alias_index': '...'}

# Export individual formats
exporter.export_json("output.json")
exporter.export_csv("output.csv")
exporter.export_alias_index("alias_index.json")
```

## Data Versioning

Each export includes version metadata from the Golden Record:

- **golden_record_version**: Version of the Golden Record schema/data
- **parliament**: Current parliament (e.g., "14th Parliament of The Bahamas")
- **parliament_start**: Start date of the current parliament
- **exported_at**: Timestamp of when the export was created

This enables:
- Tracking changes over time
- Version compatibility checking
- Historical analysis
- Reproducible research

## Export File Naming

Files are automatically timestamped to prevent overwrites:

```
<prefix>_YYYYMMDD_HHMMSS.<extension>
```

Example:
```
golden_record_20260212_140530.json
golden_record_20260212_140530.csv
golden_record_alias_index_20260212_140530.json
```

## Data License

All exported data is licensed under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). When using this data:

- **Attribution Required**: Credit "GraphHansard / Carib Digital Labs"
- **Commercial Use Allowed**: You can use this data for any purpose
- **Modifications Allowed**: You can build on this data
- **Share Alike NOT Required**: Your derivatives don't need to use CC-BY-4.0

## Automated Exports

To automate exports (e.g., nightly builds):

```bash
#!/bin/bash
# Export to dated directory
export_dir="exports/$(date +%Y-%m-%d)"
python scripts/export_golden_record.py --output-dir "$export_dir"
```

## Integration Examples

### Load JSON Export in Python

```python
import json

with open("exports/golden_record_20260212_140530.json") as f:
    data = json.load(f)

golden_record = data["golden_record"]
mps = golden_record["mps"]

for mp in mps:
    print(f"{mp['common_name']} ({mp['party']}) - {mp['constituency']}")
```

### Load CSV Export in Python

```python
import csv

with open("exports/golden_record_20260212_140530.csv") as f:
    reader = csv.DictReader(
        (row for row in f if row.strip() and not row.startswith("#"))
    )
    
    for row in reader:
        print(f"{row['common_name']} - {row['total_aliases']} aliases")
```

### Load in R

```r
library(jsonlite)
library(readr)

# Load JSON
data <- fromJSON("exports/golden_record_20260212_140530.json")
mps <- data$golden_record$mps

# Load CSV
df <- read_csv("exports/golden_record_20260212_140530.csv", 
               comment = "#")
```

### Load in Excel

1. Open Excel
2. Go to Data → From Text/CSV
3. Select the CSV file
4. Choose "Delimited" with comma separator
5. Check "My data has headers"
6. Import

## Questions?

- Check the [SRD v1.0](SRD_v1.0.md) for technical details
- Review the source data in `golden_record/mps.json`
- See the [Community Contributions Guide](community_contributions.md) for adding aliases

---

**Last updated:** February 2026  
**Implements:** GR-10 (Data Export)  
**License:** CC-BY-4.0 (data), MIT (code)
