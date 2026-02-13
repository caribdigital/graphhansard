"""Example: Session Graph Construction & Analysis

Demonstrates how to build session graphs from mention data and compute
network centrality metrics.

Usage:
    python examples/build_session_graph.py
"""

from graphhansard.brain.entity_extractor import MentionRecord, ResolutionMethod
from graphhansard.brain.graph_builder import GraphBuilder


def main():
    """Build a sample session graph and display metrics."""
    
    # Step 1: Create sample mention records (typically from EntityExtractor)
    print("Creating sample mention records...")
    mentions = [
        MentionRecord(
            session_id="sample_session_2024_01_15",
            source_node_id="mp_davis_brave",
            target_node_id="mp_cooper_chester",
            raw_mention="The Deputy Prime Minister",
            resolution_method=ResolutionMethod.EXACT,
            resolution_score=1.0,
            timestamp_start=10.5,
            timestamp_end=12.0,
            context_window="I commend the Deputy Prime Minister for his excellent work.",
            segment_index=0,
        ),
        MentionRecord(
            session_id="sample_session_2024_01_15",
            source_node_id="mp_davis_brave",
            target_node_id="mp_pintard_michael",
            raw_mention="The Leader of the Opposition",
            resolution_method=ResolutionMethod.EXACT,
            resolution_score=1.0,
            timestamp_start=45.2,
            timestamp_end=47.1,
            context_window="The Leader of the Opposition raised a valid point.",
            segment_index=1,
        ),
        MentionRecord(
            session_id="sample_session_2024_01_15",
            source_node_id="mp_pintard_michael",
            target_node_id="mp_davis_brave",
            raw_mention="The Prime Minister",
            resolution_method=ResolutionMethod.EXACT,
            resolution_score=1.0,
            timestamp_start=120.8,
            timestamp_end=122.3,
            context_window="The Prime Minister has not addressed this issue properly.",
            segment_index=2,
        ),
        MentionRecord(
            session_id="sample_session_2024_01_15",
            source_node_id="mp_cooper_chester",
            target_node_id="mp_davis_brave",
            raw_mention="The PM",
            resolution_method=ResolutionMethod.FUZZY,
            resolution_score=0.95,
            timestamp_start=200.0,
            timestamp_end=201.5,
            context_window="The PM has shown strong leadership on this bill.",
            segment_index=3,
        ),
    ]
    
    # Step 2: Convert to graph dict format with sentiment and timestamps
    # (In practice, sentiment would come from SentimentScorer)
    print("\nConverting mentions to graph format...")
    mention_dicts = [
        {
            **mentions[0].to_graph_dict(sentiment_label="positive"),
            "timestamp_start": mentions[0].timestamp_start,
            "timestamp_end": mentions[0].timestamp_end,
            "raw_mention": mentions[0].raw_mention,
        },
        {
            **mentions[1].to_graph_dict(sentiment_label="neutral"),
            "timestamp_start": mentions[1].timestamp_start,
            "timestamp_end": mentions[1].timestamp_end,
            "raw_mention": mentions[1].raw_mention,
        },
        {
            **mentions[2].to_graph_dict(sentiment_label="negative"),
            "timestamp_start": mentions[2].timestamp_start,
            "timestamp_end": mentions[2].timestamp_end,
            "raw_mention": mentions[2].raw_mention,
        },
        {
            **mentions[3].to_graph_dict(sentiment_label="positive"),
            "timestamp_start": mentions[3].timestamp_start,
            "timestamp_end": mentions[3].timestamp_end,
            "raw_mention": mentions[3].raw_mention,
        },
    ]
    
    # Step 3: Build the session graph
    print("\nBuilding session graph...")
    builder = GraphBuilder()
    
    # Provide expanded MP registry with constituency and portfolio for MP-5
    mp_registry = {
        "mp_davis_brave": {
            "common_name": "Brave Davis",
            "party": "PLP",
            "constituency": "Cat Island, Rum Cay and San Salvador",
            "current_portfolio": "Prime Minister",
        },
        "mp_cooper_chester": {
            "common_name": "Chester Cooper",
            "party": "PLP",
            "constituency": "Exuma and Ragged Island",
            "current_portfolio": "Deputy Prime Minister",
        },
        "mp_pintard_michael": {
            "common_name": "Michael Pintard",
            "party": "FNM",
            "constituency": "Marco City",
            "current_portfolio": "Leader of the Opposition",
        },
    }
    
    session_graph = builder.build_session_graph(
        mentions=mention_dicts,
        session_id="sample_session_2024_01_15",
        date="2024-01-15",
        mp_registry=mp_registry,
    )
    
    # Step 4: Display graph metrics
    print(f"\n{'='*70}")
    print(f"Session Graph: {session_graph.session_id}")
    print(f"Date: {session_graph.date}")
    print(f"Nodes: {session_graph.node_count} MPs")
    print(f"Edges: {session_graph.edge_count} interaction edges")
    print(f"{'='*70}")
    
    print("\nNode Metrics:")
    print(f"{'MP':<25} {'Party':<8} {'In':<6} {'Out':<6} {'Between':<10} {'Eigen':<10} {'Roles'}")
    print("-" * 90)
    for node in session_graph.nodes:
        roles = ", ".join(node.structural_role) if node.structural_role else "None"
        print(
            f"{node.common_name:<25} {node.party:<8} "
            f"{node.degree_in:<6} {node.degree_out:<6} "
            f"{node.betweenness:<10.3f} {node.eigenvector:<10.3f} "
            f"{roles}"
        )
    
    print("\nEdge Details:")
    print(f"{'Source':<25} {'Target':<25} {'Mentions':<10} {'Net Sentiment':<15}")
    print("-" * 80)
    for edge in session_graph.edges:
        source_name = next(
            n.common_name for n in session_graph.nodes 
            if n.node_id == edge.source_node_id
        )
        target_name = next(
            n.common_name for n in session_graph.nodes 
            if n.node_id == edge.target_node_id
        )
        sentiment_str = f"{edge.net_sentiment:+.2f} ({edge.positive_count}+, {edge.neutral_count}=, {edge.negative_count}-)"
        print(
            f"{source_name:<25} {target_name:<25} "
            f"{edge.total_mentions:<10} {sentiment_str:<15}"
        )
    
    # Step 5: Export to files
    print("\nExporting graph data...")
    
    # Export as JSON metrics
    builder.export_json(session_graph, "output/sample_session_metrics.json")
    print("✓ Exported JSON metrics to output/sample_session_metrics.json")
    
    # Export as CSV edge list
    builder.export_csv(session_graph, "output/sample_session_edges.csv")
    print("✓ Exported CSV edge list to output/sample_session_edges.csv")
    
    # Reconstruct NetworkX graph for GraphML export
    nx_graph = builder.build_graph_from_session(session_graph)
    builder.export_graphml(nx_graph, "output/sample_session.graphml")
    print("✓ Exported GraphML to output/sample_session.graphml")
    
    print("\n✅ Session graph construction complete!")
    print("\nNext steps:")
    print("  - Open output/sample_session.graphml in Gephi or yEd for visualization")
    print("  - Use output/sample_session_metrics.json for further analysis")
    print("  - Import output/sample_session_edges.csv into your favorite analytics tool")


if __name__ == "__main__":
    main()
