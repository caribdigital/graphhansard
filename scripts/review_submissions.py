#!/usr/bin/env python3
"""Review and manage community contributions for the Golden Record.

Implements GR-9: Review queue for community submissions.

Usage:
    # List all pending submissions
    python scripts/review_submissions.py --list

    # Review a specific submission
    python scripts/review_submissions.py --review sub_20260212_140530_123456

    # Approve a submission
    python scripts/review_submissions.py --approve sub_20260212_140530_123456 --notes "Valid, confirmed in video"

    # Reject a submission
    python scripts/review_submissions.py --reject sub_20260212_140530_123456 --notes "Alias already exists"

    # Show statistics
    python scripts/review_submissions.py --stats
"""

import argparse
from pathlib import Path

from graphhansard.golden_record.contributions import SubmissionQueue
from graphhansard.golden_record.models import GoldenRecord


def list_submissions(queue: SubmissionQueue, status_filter: str | None = None) -> None:
    """List submissions in the queue.

    Args:
        queue: The submission queue
        status_filter: Optional filter by status (pending, approved, rejected)
    """
    submissions = queue.submissions

    if status_filter:
        submissions = [s for s in submissions if s.status.value == status_filter]

    if not submissions:
        print(f"No submissions found{f' with status {status_filter}' if status_filter else ''}.")
        return

    print(f"\n{'=' * 80}")
    print(f"Submissions ({len(submissions)} total):")
    print(f"{'=' * 80}\n")

    for sub in submissions:
        print(f"ID: {sub.submission_id}")
        print(f"  Type: {sub.contribution_type.value}")
        print(f"  Alias: '{sub.proposed_alias}' → {sub.target_node_id}")
        print(f"  Evidence: {sub.source_evidence[:60]}{'...' if len(sub.source_evidence) > 60 else ''}")
        print(f"  Submitter: {sub.submitter_name}")
        print(f"  Submitted: {sub.submitted_at}")
        print(f"  Status: {sub.status.value}")
        if sub.reviewer_notes:
            print(f"  Reviewer notes: {sub.reviewer_notes}")
        print()


def show_stats(queue: SubmissionQueue) -> None:
    """Show queue statistics.

    Args:
        queue: The submission queue
    """
    print("\n=== Submission Queue Statistics ===\n")
    print(f"Total submissions: {queue.metadata['total_submissions']}")
    print(f"Pending review: {queue.metadata['pending_count']}")
    print(f"Approved: {queue.metadata['approved_count']}")
    print(f"Rejected: {queue.metadata['rejected_count']}")
    print(f"\nQueue created: {queue.metadata['queue_created']}")


def review_submission(
    submission_id: str, queue: SubmissionQueue, golden_record: GoldenRecord
) -> None:
    """Display detailed information about a submission for review.

    Args:
        submission_id: The submission ID to review
        queue: The submission queue
        golden_record: The GoldenRecord instance
    """
    sub = queue.get_by_id(submission_id)
    if not sub:
        print(f"❌ Submission {submission_id} not found.")
        return

    # Get MP details
    mp = next((m for m in golden_record.mps if m.node_id == sub.target_node_id), None)

    print(f"\n{'=' * 80}")
    print(f"Submission Review: {sub.submission_id}")
    print(f"{'=' * 80}\n")

    print(f"Type: {sub.contribution_type.value}")
    print(f"Status: {sub.status.value}")
    print(f"Submitted: {sub.submitted_at}")
    print()
    print(f"Proposed Alias: '{sub.proposed_alias}'")
    print(f"Target MP: {sub.target_node_id}")
    if mp:
        print(f"  → {mp.full_name} ({mp.common_name})")
        print(f"  → {mp.party.value} - {mp.constituency}")
        print(f"  → Current aliases: {len(mp.all_aliases)}")
        print(f"  → Sample aliases: {', '.join(mp.all_aliases[:5])}")
    print()
    print(f"Evidence:\n  {sub.source_evidence}")
    print()
    print(f"Submitter: {sub.submitter_name}")
    if sub.submitter_email:
        print(f"Email: {sub.submitter_email}")
    if sub.notes:
        print(f"Notes: {sub.notes}")
    print()

    if sub.reviewer_notes:
        print(f"Reviewer Notes: {sub.reviewer_notes}")
        print()


def main():
    """Review and manage community contributions."""
    parser = argparse.ArgumentParser(
        description="Review community contributions for Golden Record (GR-9)"
    )
    parser.add_argument(
        "--queue-file",
        default="contributions_queue.json",
        help="Path to submissions queue file (default: contributions_queue.json)",
    )
    parser.add_argument("--list", action="store_true", help="List all submissions")
    parser.add_argument(
        "--status",
        choices=["pending", "approved", "rejected"],
        help="Filter by status (use with --list)",
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show queue statistics"
    )
    parser.add_argument("--review", help="Review a specific submission by ID")
    parser.add_argument(
        "--approve", help="Approve a submission by ID (requires --notes)"
    )
    parser.add_argument(
        "--reject", help="Reject a submission by ID (requires --notes)"
    )
    parser.add_argument("--notes", help="Reviewer notes for approve/reject")

    args = parser.parse_args()

    queue_path = Path(args.queue_file)

    # Check if queue file exists
    if not queue_path.exists():
        print(f"❌ Queue file not found: {queue_path}")
        print("   Use submit_alias.py to create submissions first.")
        return

    # Load queue
    print(f"Loading submission queue from {queue_path}...")
    queue = SubmissionQueue.load_from_file(str(queue_path))

    # Load Golden Record for validation
    repo_root = Path(__file__).parent.parent
    golden_record_path = repo_root / "golden_record" / "mps.json"
    data = golden_record_path.read_text(encoding="utf-8")
    golden_record = GoldenRecord.model_validate_json(data)

    # Execute command
    if args.stats:
        show_stats(queue)

    elif args.list:
        list_submissions(queue, args.status)

    elif args.review:
        review_submission(args.review, queue, golden_record)

    elif args.approve:
        if not args.notes:
            print("❌ --notes is required when approving a submission")
            return

        sub = queue.get_by_id(args.approve)
        if not sub:
            print(f"❌ Submission {args.approve} not found.")
            return

        sub.approve(args.notes)
        queue.save_to_file(str(queue_path))
        print(f"✅ Submission {args.approve} approved.")
        print(f"   Reviewer notes: {args.notes}")

    elif args.reject:
        if not args.notes:
            print("❌ --notes is required when rejecting a submission")
            return

        sub = queue.get_by_id(args.reject)
        if not sub:
            print(f"❌ Submission {args.reject} not found.")
            return

        sub.reject(args.notes)
        queue.save_to_file(str(queue_path))
        print(f"✅ Submission {args.reject} rejected.")
        print(f"   Reason: {args.notes}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
