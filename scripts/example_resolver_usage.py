#!/usr/bin/env python3
"""Example usage of the Alias Resolution API.

This script demonstrates how to use the AliasResolver to resolve
mentions from parliamentary debate to canonical MP node IDs.

Usage:
    python scripts/example_resolver_usage.py
"""

from pathlib import Path

from graphhansard.golden_record.resolver import AliasResolver


def main():
    """Demonstrate alias resolution API."""
    # Initialize the resolver
    golden_record_path = Path(__file__).parent.parent / "golden_record" / "mps.json"
    resolver = AliasResolver(str(golden_record_path))

    print("=" * 70)
    print("GraphHansard Alias Resolution API - Example Usage")
    print("=" * 70)
    print()

    # Example 1: Exact match
    print("Example 1: Exact Match")
    print("-" * 70)
    result = resolver.resolve("Brave Davis")
    print("Mention: 'Brave Davis'")
    print(f"  → Node ID: {result.node_id}")
    print(f"  → Confidence: {result.confidence}")
    print(f"  → Method: {result.method}")
    print()

    # Example 2: Fuzzy match
    print("Example 2: Fuzzy Match (typo)")
    print("-" * 70)
    result = resolver.resolve("Chestor Cooper")
    print("Mention: 'Chestor Cooper' (typo: should be 'Chester')")
    print(f"  → Node ID: {result.node_id}")
    print(f"  → Confidence: {result.confidence:.2f}")
    print(f"  → Method: {result.method}")
    print()

    # Example 3: Temporal disambiguation (before reshuffle)
    print("Example 3: Temporal Disambiguation (Before Sept 2023 Reshuffle)")
    print("-" * 70)
    result = resolver.resolve("Minister of Works", debate_date="2023-08-01")
    print("Mention: 'Minister of Works' on 2023-08-01")
    print(f"  → Node ID: {result.node_id}")
    print(f"  → Confidence: {result.confidence}")
    print(f"  → Method: {result.method}")
    print()

    # Example 4: Temporal disambiguation (after reshuffle)
    print("Example 4: Temporal Disambiguation (After Sept 2023 Reshuffle)")
    print("-" * 70)
    result = resolver.resolve("Minister of Works", debate_date="2023-10-01")
    print("Mention: 'Minister of Works' on 2023-10-01")
    print(f"  → Node ID: {result.node_id}")
    print(f"  → Confidence: {result.confidence}")
    print(f"  → Method: {result.method}")
    print()

    # Example 5: Known collision
    print("Example 5: Known Alias Collision")
    print("-" * 70)
    result = resolver.resolve("Adrian")
    print("Mention: 'Adrian' (collision between two FNM MPs)")
    print(f"  → Node ID: {result.node_id}")
    print(f"  → Confidence: {result.confidence}")
    print(f"  → Method: {result.method}")
    print(f"  → Collision Warning: {result.collision_warning}")
    print()

    # Example 6: Unresolved mention
    print("Example 6: Unresolved Mention")
    print("-" * 70)
    result = resolver.resolve("Some Random Person")
    print("Mention: 'Some Random Person'")
    print(f"  → Node ID: {result.node_id}")
    print(f"  → Confidence: {result.confidence}")
    print(f"  → Method: {result.method}")
    print(f"  → Logged for review: {len(resolver.unresolved_log)} total unresolved")
    print()

    # Example 7: Portfolio alias
    print("Example 7: Portfolio Alias")
    print("-" * 70)
    result = resolver.resolve("The Prime Minister")
    print("Mention: 'The Prime Minister'")
    print(f"  → Node ID: {result.node_id}")
    print(f"  → Confidence: {result.confidence}")
    print(f"  → Method: {result.method}")
    print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Total unique aliases indexed: {len(resolver._alias_index)}")
    collisions = [v for v in resolver._alias_index.values() if len(v) > 1]
    print(f"Total collisions: {len(collisions)}")
    print(f"Fuzzy match threshold: {resolver.fuzzy_threshold}")
    print()


if __name__ == "__main__":
    main()
