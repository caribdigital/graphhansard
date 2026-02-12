#!/usr/bin/env python3
"""Submit community contributions for the Golden Record.

Implements GR-9: Community contribution mechanism for alias additions/corrections.

Usage:
    # Interactive mode (prompts for all fields)
    python scripts/submit_alias.py

    # Command-line mode (provide all fields)
    python scripts/submit_alias.py \\
        --type alias_addition \\
        --alias "Papa" \\
        --target mp_davis_brave \\
        --evidence "Used in House debate 2024-01-15, video at 1:23:45" \\
        --submitter "Jane Doe"

    # With optional fields
    python scripts/submit_alias.py \\
        --type alias_addition \\
        --alias "Papa" \\
        --target mp_davis_brave \\
        --evidence "https://youtube.com/watch?v=..." \\
        --submitter "Jane Doe" \\
        --email "jane@example.com" \\
        --notes "Heard this nickname used multiple times"
"""

import argparse
import sys
from pathlib import Path

from graphhansard.golden_record.contributions import (
    AliasSubmission,
    ContributionType,
    SubmissionQueue,
)
from graphhansard.golden_record.models import GoldenRecord


def validate_node_id(node_id: str, golden_record: GoldenRecord) -> bool:
    """Validate that the node_id exists in the Golden Record.

    Args:
        node_id: The node ID to validate
        golden_record: The GoldenRecord instance

    Returns:
        True if valid, False otherwise
    """
    return any(mp.node_id == node_id for mp in golden_record.mps)


def interactive_submission() -> AliasSubmission:
    """Prompt user interactively for submission details.

    Returns:
        AliasSubmission instance
    """
    print("\n=== Golden Record Alias Submission ===\n")

    # Contribution type
    print("Contribution Type:")
    print("  1. alias_addition (add a new alias)")
    print("  2. alias_correction (correct an existing alias)")
    type_choice = input("Enter choice (1 or 2): ").strip()

    if type_choice == "1":
        contribution_type = ContributionType.ALIAS_ADDITION
    elif type_choice == "2":
        contribution_type = ContributionType.ALIAS_CORRECTION
    else:
        print("Invalid choice. Defaulting to alias_addition.")
        contribution_type = ContributionType.ALIAS_ADDITION

    # Proposed alias
    proposed_alias = input("\nProposed alias (e.g., 'Papa', 'The PM'): ").strip()

    # Target node ID
    target_node_id = input(
        "Target node_id (e.g., 'mp_davis_brave'): "
    ).strip()

    # Source/evidence
    print("\nSource/Evidence (provide URL, citation, or description):")
    source_evidence = input("  > ").strip()

    # Submitter
    submitter_name = input("\nYour name (or 'Anonymous'): ").strip()
    if not submitter_name:
        submitter_name = "Anonymous"

    # Optional fields
    submitter_email = input("Your email (optional, press Enter to skip): ").strip()
    if not submitter_email:
        submitter_email = None

    notes = input("Additional notes (optional, press Enter to skip): ").strip()
    if not notes:
        notes = None

    # Create submission
    return AliasSubmission(
        contribution_type=contribution_type,
        proposed_alias=proposed_alias,
        target_node_id=target_node_id,
        source_evidence=source_evidence,
        submitter_name=submitter_name,
        submitter_email=submitter_email,
        notes=notes,
    )


def main():
    """Submit a community contribution."""
    parser = argparse.ArgumentParser(
        description="Submit community contributions for Golden Record aliases (GR-9)"
    )
    parser.add_argument(
        "--type",
        choices=["alias_addition", "alias_correction"],
        help="Type of contribution",
    )
    parser.add_argument("--alias", help="Proposed alias")
    parser.add_argument(
        "--target", help="Target node_id (e.g., 'mp_davis_brave')"
    )
    parser.add_argument(
        "--evidence", help="Source/evidence (URL, citation, description)"
    )
    parser.add_argument("--submitter", help="Your name")
    parser.add_argument("--email", help="Your email (optional)")
    parser.add_argument("--notes", help="Additional notes (optional)")
    parser.add_argument(
        "--queue-file",
        default="contributions_queue.json",
        help="Path to submissions queue file (default: contributions_queue.json)",
    )

    args = parser.parse_args()

    # Paths
    repo_root = Path(__file__).parent.parent
    golden_record_path = repo_root / "golden_record" / "mps.json"
    queue_path = Path(args.queue_file)

    # Load Golden Record for validation
    print(f"Loading Golden Record from {golden_record_path}...")
    data = golden_record_path.read_text(encoding="utf-8")
    golden_record = GoldenRecord.model_validate_json(data)

    # Get submission (interactive or command-line)
    if args.alias and args.target and args.evidence and args.submitter:
        # Command-line mode
        submission = AliasSubmission(
            contribution_type=ContributionType(args.type or "alias_addition"),
            proposed_alias=args.alias,
            target_node_id=args.target,
            source_evidence=args.evidence,
            submitter_name=args.submitter,
            submitter_email=args.email,
            notes=args.notes,
        )
    else:
        # Interactive mode
        submission = interactive_submission()

    # Validate node_id
    if not validate_node_id(submission.target_node_id, golden_record):
        print(f"\n❌ Error: node_id '{submission.target_node_id}' not found in Golden Record.")
        print(f"   Available node_ids: {', '.join(mp.node_id for mp in golden_record.mps[:5])}...")
        sys.exit(1)

    # Load or create submission queue
    if queue_path.exists():
        print(f"\nLoading existing queue from {queue_path}...")
        queue = SubmissionQueue.load_from_file(str(queue_path))
    else:
        print("\nCreating new submission queue...")
        queue = SubmissionQueue()

    # Add submission to queue
    queue.add_submission(submission)

    # Save queue
    queue.save_to_file(str(queue_path))

    print(f"\n✅ Submission added to queue!")
    print(f"   Submission ID: {submission.submission_id}")
    print(f"   Status: {submission.status.value}")
    print(f"   Queue file: {queue_path}")
    print(f"\n   Total submissions in queue: {queue.metadata['total_submissions']}")
    print(f"   Pending review: {queue.metadata['pending_count']}")


if __name__ == "__main__":
    main()
