"""Example usage of the Sentiment Scoring pipeline.

This script demonstrates how to use the SentimentScorer to classify
parliamentary mentions by sentiment.
"""

from graphhansard.brain.sentiment import SentimentLabel, SentimentScorer


def main():
    """Demonstrate sentiment scoring on sample parliamentary contexts."""
    print("=" * 70)
    print("GraphHansard Sentiment Scoring Demo")
    print("=" * 70)
    print()

    # Initialize the scorer
    print("Initializing sentiment scorer...")
    scorer = SentimentScorer()
    print(f"Using model: {scorer.model_name}")
    print()

    # Sample parliamentary contexts (similar to what entity extraction produces)
    contexts = [
        {
            "text": (
                "I commend the Prime Minister for his excellent work on this bill. "
                "His leadership has been exemplary and I fully support his position."
            ),
            "expected": "positive",
        },
        {
            "text": (
                "The Member for Cat Island has completely misunderstood the issue. "
                "His proposal is reckless and would be disastrous for our country."
            ),
            "expected": "negative",
        },
        {
            "text": (
                "The Minister of Finance tabled the report yesterday. "
                "The Member for Fox Hill asked three questions about the budget."
            ),
            "expected": "neutral",
        },
        {
            "text": (
                "On a point of order, Mr. Speaker! The Honourable Member has "
                "misstated the facts and must withdraw those remarks."
            ),
            "expected": "negative with parliamentary markers",
        },
        {
            "text": (
                "Will the Member yield to a question about his proposal? "
                "I believe there are some concerns that need to be addressed."
            ),
            "expected": "neutral with challenge marker",
        },
    ]

    # Score each context
    print("Scoring parliamentary contexts...")
    print("-" * 70)
    
    for i, example in enumerate(contexts, 1):
        print(f"\nExample {i}:")
        print(f"Context: {example['text'][:80]}...")
        print(f"Expected: {example['expected']}")
        print()
        
        # Score the context
        result = scorer.score(example['text'])
        
        print(f"Result:")
        print(f"  Label: {result.label.value}")
        print(f"  Confidence: {result.confidence:.3f}")
        
        if result.parliamentary_markers:
            print(f"  Parliamentary Markers: {', '.join(result.parliamentary_markers)}")
        else:
            print(f"  Parliamentary Markers: None")
        
        print("-" * 70)

    # Demonstrate batch processing
    print("\n" + "=" * 70)
    print("Batch Processing Demo")
    print("=" * 70)
    print()
    
    batch_contexts = [example['text'] for example in contexts[:3]]
    print(f"Processing {len(batch_contexts)} contexts in batch...")
    
    results = scorer.score_batch(batch_contexts)
    
    print("\nBatch results:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.label.value} (confidence: {result.confidence:.3f})")

    print()
    print("=" * 70)
    print("Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
