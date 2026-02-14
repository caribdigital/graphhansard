"""Benchmark for NF-3: Graph computation time.

Target: ≤5 seconds for a 39-node graph (single session)

This script measures the performance of graph construction and
centrality metric computation to validate NF-3 compliance.
"""

import json
import sys
import time
from pathlib import Path

import networkx as nx

# Import directly to avoid heavy dependencies from brain/__init__.py
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Direct import to avoid loading pipeline module with heavy deps
import importlib.util
spec = importlib.util.spec_from_file_location(
    "graph_builder",
    Path(__file__).parent.parent / "src" / "graphhansard" / "brain" / "graph_builder.py"
)
graph_builder_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(graph_builder_module)
GraphBuilder = graph_builder_module.GraphBuilder

from graphhansard.golden_record import GoldenRecord


def load_golden_record(path: str) -> GoldenRecord:
    """Load golden record from JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return GoldenRecord(**data)


def generate_sample_mentions(num_mentions: int = 200) -> list[dict]:
    """Generate sample mention data for benchmarking.
    
    Creates a realistic distribution of mentions across all 39 MPs.
    
    Args:
        num_mentions: Number of mentions to generate
        
    Returns:
        List of mention dictionaries for GraphBuilder
    """
    # Load actual MP IDs from golden record
    golden_record_path = Path(__file__).parent.parent / "golden_record" / "mps.json"
    golden_record = load_golden_record(str(golden_record_path))
    mp_ids = [mp.node_id for mp in golden_record.mps]
    
    import random
    random.seed(42)  # Reproducible benchmarks
    
    mentions = []
    sentiment_labels = ["positive", "neutral", "negative"]
    
    for i in range(num_mentions):
        source = random.choice(mp_ids)
        target = random.choice([mp for mp in mp_ids if mp != source])
        
        mention = {
            "source_node_id": source,
            "target_node_id": target,
            "context_window": f"Sample context for mention {i}",
            "sentiment_label": random.choice(sentiment_labels),
            "timestamp_start": i * 10.0,
            "timestamp_end": i * 10.0 + 5.0,
        }
        mentions.append(mention)
    
    return mentions


def benchmark_graph_computation(num_mentions: int = 200) -> dict:
    """Benchmark graph computation performance.
    
    Args:
        num_mentions: Number of mentions to include in graph
        
    Returns:
        Dictionary with benchmark results
    """
    print(f"\n{'='*60}")
    print(f"NF-3: Graph Computation Performance Benchmark")
    print(f"{'='*60}")
    print(f"Graph size: 39 nodes (MPs)")
    print(f"Mentions: {num_mentions}")
    print(f"Target: ≤5 seconds")
    print()
    
    # Generate sample mentions
    print("Generating sample mentions...")
    mentions = generate_sample_mentions(num_mentions)
    print(f"Generated {len(mentions)} mentions")
    
    # Load golden record
    print("Loading golden record...")
    golden_record_path = Path(__file__).parent.parent / "golden_record" / "mps.json"
    golden_record = load_golden_record(str(golden_record_path))
    
    # Initialize graph builder
    print("Initializing graph builder...")
    builder = GraphBuilder()
    
    # Run benchmark
    print("\nRunning graph computation benchmark...")
    start_time = time.perf_counter()
    
    # Build graph
    session_graph = builder.build_session_graph(
        session_id="benchmark_session",
        date="2024-01-01",
        mentions=mentions,
        mp_registry=None,  # Will use default from golden record
    )
    
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    
    # Collect graph statistics
    num_nodes = session_graph.number_of_nodes()
    num_edges = session_graph.number_of_edges()
    
    # Results
    results = {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "num_mentions": len(mentions),
        "elapsed_seconds": elapsed,
        "target_seconds": 5.0,
        "passes": elapsed <= 5.0,
    }
    
    # Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Graph nodes: {num_nodes}")
    print(f"Graph edges: {num_edges}")
    print(f"Mentions processed: {len(mentions)}")
    print(f"Elapsed time: {elapsed:.3f} seconds")
    print()
    print(f"Target: ≤5 seconds")
    print(f"Status: {'✅ PASS' if results['passes'] else '❌ FAIL'}")
    print("="*60)
    
    # Additional breakdown for debugging
    if elapsed > 5.0:
        print("\n⚠️  Performance target not met. Consider optimizations:")
        print("  - Pre-compute centrality metrics for common graph sizes")
        print("  - Use sparse matrix representations")
        print("  - Cache intermediate computations")
    
    return results


if __name__ == "__main__":
    # Benchmark with typical session mention count
    results = benchmark_graph_computation(num_mentions=200)
    
    # Optional: Test with larger graphs
    # results = benchmark_graph_computation(num_mentions=500)
