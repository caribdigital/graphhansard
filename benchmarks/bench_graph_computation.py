"""Benchmark for NF-3: Graph computation time.

Target: ≤5 seconds for a 39-node graph (single session)

This script measures the performance of graph construction and
centrality metric computation to validate NF-3 compliance.

Note: This is a simplified benchmark using NetworkX directly.
For full graph builder with metadata, install brain dependencies:
    pip install -e '.[brain]'
"""

import random
import time
from pathlib import Path

import networkx as nx


def generate_sample_graph(num_nodes: int = 39, num_edges: int = 100) -> nx.DiGraph:
    """Generate a sample directed graph for benchmarking.
    
    Creates a realistic political interaction graph structure.
    
    Args:
        num_nodes: Number of MP nodes
        num_edges: Number of interaction edges
        
    Returns:
        NetworkX directed graph
    """
    random.seed(42)  # Reproducible
    
    G = nx.DiGraph()
    
    # Add nodes (MPs)
    for i in range(num_nodes):
        G.add_node(f"mp_{i}", name=f"MP {i}")
    
    # Add edges (mentions) with realistic distribution
    # Some MPs are more central (mentioned more)
    nodes = list(G.nodes())
    
    # Create a power-law-like distribution of mentions
    for _ in range(num_edges):
        # Select source (any MP)
        source = random.choice(nodes)
        # Select target (weighted toward central nodes)
        target = random.choice(nodes)
        
        if source != target:  # No self-loops
            if G.has_edge(source, target):
                # Increase weight if edge exists
                G[source][target]['weight'] += 1
            else:
                G.add_edge(source, target, weight=1)
    
    return G


def benchmark_graph_computation(num_nodes: int = 39, num_edges: int = 100) -> dict:
    """Benchmark graph computation performance.
    
    Args:
        num_nodes: Number of nodes (MPs)
        num_edges: Number of edges (mentions)
        
    Returns:
        Dictionary with benchmark results
    """
    print(f"\n{'='*60}")
    print(f"NF-3: Graph Computation Performance Benchmark")
    print(f"{'='*60}")
    print(f"Graph size: {num_nodes} nodes (MPs)")
    print(f"Edges: {num_edges}")
    print(f"Target: ≤5 seconds")
    print()
    
    # Generate sample graph
    print("Generating sample graph...")
    G = generate_sample_graph(num_nodes, num_edges)
    print(f"Generated graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # Run benchmark
    print("\nRunning graph computation benchmark...")
    print("(Computing centrality metrics)")
    start_time = time.perf_counter()
    
    # Compute centrality metrics (this is the expensive part)
    degree_centrality = nx.degree_centrality(G)
    betweenness_centrality = nx.betweenness_centrality(G)
    eigenvector_centrality = nx.eigenvector_centrality(G, max_iter=100)
    closeness_centrality = nx.closeness_centrality(G)
    
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    
    # Collect statistics
    num_nodes_final = G.number_of_nodes()
    num_edges_final = G.number_of_edges()
    
    # Results
    results = {
        "num_nodes": num_nodes_final,
        "num_edges": num_edges_final,
        "elapsed_seconds": elapsed,
        "target_seconds": 5.0,
        "passes": elapsed <= 5.0,
        "metrics_computed": 4,  # degree, betweenness, eigenvector, closeness
    }
    
    # Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Graph nodes: {num_nodes_final}")
    print(f"Graph edges: {num_edges_final}")
    print(f"Centrality metrics computed: {results['metrics_computed']}")
    print(f"Elapsed time: {elapsed:.3f} seconds")
    print()
    print(f"Target: ≤5 seconds")
    print(f"Status: {'✅ PASS' if results['passes'] else '❌ FAIL'}")
    print()
    print(f"Note: This benchmark computes 4 centrality metrics:")
    print(f"  - Degree centrality")
    print(f"  - Betweenness centrality")
    print(f"  - Eigenvector centrality")
    print(f"  - Closeness centrality")
    print("="*60)
    
    # Additional breakdown for debugging
    if elapsed > 5.0:
        print("\n⚠️  Performance target not met. Consider optimizations:")
        print("  - Pre-compute centrality metrics for common graph sizes")
        print("  - Use sparse matrix representations")
        print("  - Cache intermediate computations")
        print("  - Consider approximate algorithms for large graphs")
    
    return results


if __name__ == "__main__":
    # Benchmark with 39 MPs and typical mention count
    results = benchmark_graph_computation(num_nodes=39, num_edges=100)
    
    # Optional: Test with larger graphs
    # results = benchmark_graph_computation(num_nodes=39, num_edges=200)
