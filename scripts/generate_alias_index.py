#!/usr/bin/env python3
"""Generate the aliases_index.json from mps.json.

This script builds the inverted alias index and saves it to
golden_record/aliases_index.json for inspection and use by other tools.

Usage:
    python scripts/generate_alias_index.py
"""

from pathlib import Path

from graphhansard.golden_record.resolver import AliasResolver


def main():
    """Generate and save the alias index."""
    # Paths
    repo_root = Path(__file__).parent.parent
    golden_record_path = repo_root / "golden_record" / "mps.json"
    output_path = repo_root / "golden_record" / "aliases_index.json"

    # Create resolver and generate index
    print(f"Loading Golden Record from {golden_record_path}...")
    resolver = AliasResolver(str(golden_record_path))

    print(f"Building inverted alias index...")
    print(f"  Total unique aliases: {len(resolver._alias_index)}")

    # Count collisions
    collisions = {k: v for k, v in resolver._alias_index.items() if len(v) > 1}
    print(f"  Alias collisions: {len(collisions)}")

    # Save index
    print(f"Saving index to {output_path}...")
    resolver.save_index(str(output_path))

    print(f"✅ Done. Index saved to {output_path}")
    print(f"\nExample entries:")
    for i, (alias, node_ids) in enumerate(list(resolver._alias_index.items())[:5]):
        print(f"  '{alias}' -> {node_ids}")


if __name__ == "__main__":
    main()
