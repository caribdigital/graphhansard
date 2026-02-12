#!/usr/bin/env python3
"""Validation script for the Golden Record annotated mention corpus.

This script validates the alias resolver's accuracy against a manually
annotated corpus of 50+ MP mentions from real House of Assembly audio.

Metrics calculated:
- Precision: Of all resolutions made, what % were correct?
- Recall: Of all mentions in corpus, what % were correctly resolved?
- F1 Score: Harmonic mean of precision and recall
- Accuracy: Overall correctness rate

Target (SRD §6.5): 90%+ on both Precision and Recall

Usage:
    python scripts/validate_corpus.py
    python scripts/validate_corpus.py --verbose
    python scripts/validate_corpus.py --output-report validation_report.json
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graphhansard.golden_record.resolver import AliasResolver


@dataclass
class ValidationMetrics:
    """Container for validation metrics."""

    total_mentions: int
    correct_resolutions: int
    incorrect_resolutions: int
    unresolved_mentions: int
    precision: float
    recall: float
    f1_score: float
    accuracy: float

    def meets_target(self, target: float = 0.90) -> bool:
        """Check if validation meets target threshold."""
        return self.precision >= target and self.recall >= target


def load_corpus(corpus_path: Path) -> dict[str, Any]:
    """Load the annotated mention corpus."""
    with open(corpus_path, encoding="utf-8") as f:
        return json.load(f)


def validate_corpus(
    resolver: AliasResolver, corpus: dict[str, Any], verbose: bool = False
) -> tuple[ValidationMetrics, list[dict]]:
    """Validate the resolver against the annotated corpus.

    Args:
        resolver: Initialized AliasResolver instance
        corpus: Loaded corpus dictionary
        verbose: Whether to print detailed results

    Returns:
        Tuple of (ValidationMetrics, list of detailed results per mention)
    """
    mentions = corpus["mentions"]
    total_mentions = len(mentions)

    correct_resolutions = 0
    incorrect_resolutions = 0
    unresolved_mentions = 0

    detailed_results = []

    if verbose:
        print(f"\n{'='*80}")
        print(f"VALIDATING {total_mentions} MENTIONS")
        print(f"{'='*80}\n")

    for i, mention in enumerate(mentions, 1):
        raw_mention = mention["raw_mention"]
        expected_node_id = mention["expected_node_id"]
        debate_date = mention.get("debate_date")

        # Resolve the mention
        result = resolver.resolve(raw_mention, debate_date)

        # Determine if resolution was correct
        is_correct = result.node_id == expected_node_id
        was_resolved = result.node_id is not None

        if is_correct:
            correct_resolutions += 1
            status = "✓ CORRECT"
        elif was_resolved:
            incorrect_resolutions += 1
            status = "✗ INCORRECT"
        else:
            unresolved_mentions += 1
            status = "? UNRESOLVED"

        # Store detailed result
        detailed_result = {
            "mention_id": mention["mention_id"],
            "raw_mention": raw_mention,
            "expected_node_id": expected_node_id,
            "resolved_node_id": result.node_id,
            "confidence": result.confidence,
            "method": result.method,
            "is_correct": is_correct,
            "was_resolved": was_resolved,
            "mention_type": mention.get("mention_type"),
            "debate_date": debate_date,
        }
        detailed_results.append(detailed_result)

        if verbose:
            print(f"{i:3d}. {status}")
            print(f"     Raw: '{raw_mention}'")
            print(f"     Expected: {expected_node_id}")
            print(f"     Resolved: {result.node_id}")
            print(f"     Method: {result.method} (confidence: {result.confidence:.2f})")
            if mention.get("notes"):
                print(f"     Notes: {mention['notes']}")
            if result.collision_warning:
                print(f"     ⚠️  {result.collision_warning}")
            print()

    # Calculate metrics
    # True Positives (TP): Correctly resolved mentions
    tp = correct_resolutions

    # False Positives (FP): Incorrectly resolved mentions
    fp = incorrect_resolutions

    # False Negatives (FN): Unresolved mentions (should have been resolved)
    fn = unresolved_mentions

    # Precision: TP / (TP + FP)
    # What percentage of resolutions made were correct?
    total_resolutions = tp + fp
    precision = tp / total_resolutions if total_resolutions > 0 else 0.0

    # Recall: TP / (TP + FN)
    # What percentage of all mentions were correctly resolved?
    total_positives = tp + fn
    recall = tp / total_positives if total_positives > 0 else 0.0

    # F1 Score: Harmonic mean of precision and recall
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    # Accuracy: (TP + TN) / Total
    # Since we don't have true negatives (all mentions should resolve),
    # accuracy = correct / total
    accuracy = correct_resolutions / total_mentions if total_mentions > 0 else 0.0

    metrics = ValidationMetrics(
        total_mentions=total_mentions,
        correct_resolutions=correct_resolutions,
        incorrect_resolutions=incorrect_resolutions,
        unresolved_mentions=unresolved_mentions,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        accuracy=accuracy,
    )

    return metrics, detailed_results


def print_summary(metrics: ValidationMetrics, target: float = 0.90) -> None:
    """Print a formatted summary of validation metrics."""
    print(f"\n{'='*80}")
    print("VALIDATION RESULTS SUMMARY")
    print(f"{'='*80}\n")

    print(f"Total Mentions:         {metrics.total_mentions}")
    print(f"Correct Resolutions:    {metrics.correct_resolutions}")
    print(f"Incorrect Resolutions:  {metrics.incorrect_resolutions}")
    print(f"Unresolved Mentions:    {metrics.unresolved_mentions}")
    print()

    # Key metrics
    print(f"{'METRIC':<20} {'VALUE':>10} {'TARGET':>10} {'STATUS':>10}")
    print(f"{'-'*20} {'-'*10} {'-'*10} {'-'*10}")

    def format_metric_row(name: str, value: float, target: float) -> str:
        value_str = f"{value*100:.1f}%"
        target_str = f"{target*100:.0f}%"
        status = "✓ PASS" if value >= target else "✗ FAIL"
        return f"{name:<20} {value_str:>10} {target_str:>10} {status:>10}"

    print(format_metric_row("Precision", metrics.precision, target))
    print(format_metric_row("Recall", metrics.recall, target))
    print(format_metric_row("F1 Score", metrics.f1_score, target))
    print(format_metric_row("Accuracy", metrics.accuracy, target))
    print()

    # Overall assessment
    if metrics.meets_target(target):
        print("✓ VALIDATION PASSED: Meets SRD §6.5 requirement (90%+ P&R)")
    else:
        print("✗ VALIDATION FAILED: Does not meet SRD §6.5 requirement")
        print(
            f"  Precision: {metrics.precision*100:.1f}% "
            f"({'PASS' if metrics.precision >= target else 'FAIL'})"
        )
        print(
            f"  Recall:    {metrics.recall*100:.1f}% "
            f"({'PASS' if metrics.recall >= target else 'FAIL'})"
        )

    print(f"{'='*80}\n")


def analyze_errors(detailed_results: list[dict], verbose: bool = False) -> None:
    """Analyze error patterns in the validation results."""
    errors = [r for r in detailed_results if not r["is_correct"]]

    if not errors:
        print("No errors found! Perfect validation.")
        return

    print(f"\n{'='*80}")
    print(f"ERROR ANALYSIS ({len(errors)} errors)")
    print(f"{'='*80}\n")

    # Group errors by type
    incorrect = [e for e in errors if e["was_resolved"]]
    unresolved = [e for e in errors if not e["was_resolved"]]

    print(f"Incorrect Resolutions: {len(incorrect)}")
    print(f"Unresolved Mentions:   {len(unresolved)}")
    print()

    # Analyze by mention type
    error_by_type: dict[str, int] = {}
    for error in errors:
        mention_type = error.get("mention_type", "unknown")
        error_by_type[mention_type] = error_by_type.get(mention_type, 0) + 1

    print("Errors by Mention Type:")
    for mention_type, count in sorted(
        error_by_type.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {mention_type}: {count}")
    print()

    if verbose and errors:
        print("Detailed Error List:")
        print(f"{'-'*80}")
        for error in errors:
            print(f"Mention ID: {error['mention_id']}")
            print(f"  Raw: '{error['raw_mention']}'")
            print(f"  Expected: {error['expected_node_id']}")
            print(f"  Resolved: {error['resolved_node_id']}")
            print(f"  Method: {error['method']} (confidence: {error['confidence']:.2f})")
            print(f"  Type: {error.get('mention_type')}")
            print()


def save_report(
    corpus: dict[str, Any],
    metrics: ValidationMetrics,
    detailed_results: list[dict],
    output_path: Path,
) -> None:
    """Save a detailed validation report to JSON."""
    report = {
        "metadata": {
            "corpus_version": corpus["metadata"]["version"],
            "total_mentions": corpus["metadata"]["total_mentions"],
            "validation_date": corpus["metadata"]["created_date"],
        },
        "metrics": {
            "total_mentions": metrics.total_mentions,
            "correct_resolutions": metrics.correct_resolutions,
            "incorrect_resolutions": metrics.incorrect_resolutions,
            "unresolved_mentions": metrics.unresolved_mentions,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1_score": metrics.f1_score,
            "accuracy": metrics.accuracy,
            "meets_target": metrics.meets_target(),
        },
        "detailed_results": detailed_results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Detailed report saved to: {output_path}")


def main() -> int:
    """Main entry point for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate alias resolver against annotated mention corpus"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed results for each mention",
    )
    parser.add_argument(
        "--output-report",
        "-o",
        type=Path,
        help="Save detailed validation report to JSON file",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("golden_record/validation/annotated_mentions.json"),
        help="Path to annotated mention corpus (default: golden_record/validation/annotated_mentions.json)",
    )
    parser.add_argument(
        "--golden-record",
        type=Path,
        default=Path("golden_record/mps.json"),
        help="Path to golden record (default: golden_record/mps.json)",
    )
    parser.add_argument(
        "--target",
        type=float,
        default=0.90,
        help="Target threshold for precision and recall (default: 0.90)",
    )

    args = parser.parse_args()

    # Load corpus and resolver
    print("Loading corpus and initializing resolver...")
    corpus = load_corpus(args.corpus)
    resolver = AliasResolver(str(args.golden_record))

    # Validate
    metrics, detailed_results = validate_corpus(resolver, corpus, args.verbose)

    # Print summary
    print_summary(metrics, args.target)

    # Analyze errors
    if args.verbose:
        analyze_errors(detailed_results, args.verbose)

    # Save report if requested
    if args.output_report:
        save_report(corpus, metrics, detailed_results, args.output_report)

    # Return exit code based on validation result
    return 0 if metrics.meets_target(args.target) else 1


if __name__ == "__main__":
    sys.exit(main())
