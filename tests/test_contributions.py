"""Tests for Golden Record community contributions (GR-9)."""

from datetime import datetime
from pathlib import Path

import pytest

from graphhansard.golden_record.contributions import (
    AliasSubmission,
    ContributionStatus,
    ContributionType,
    SubmissionQueue,
)


class TestAliasSubmission:
    """Test AliasSubmission model."""

    def test_valid_submission_creation(self):
        """Create a valid alias submission."""
        submission = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Papa",
            target_node_id="mp_davis_brave",
            source_evidence="Used in House debate 2024-01-15",
            submitter_name="Jane Doe",
        )

        assert submission.proposed_alias == "Papa"
        assert submission.target_node_id == "mp_davis_brave"
        assert submission.status == ContributionStatus.PENDING

    def test_submission_with_optional_fields(self):
        """Create submission with optional fields."""
        submission = AliasSubmission(
            contribution_type=ContributionType.ALIAS_CORRECTION,
            proposed_alias="Papa",
            target_node_id="mp_davis_brave",
            source_evidence="https://youtube.com/watch?v=example",
            submitter_name="Jane Doe",
            submitter_email="jane@example.com",
            notes="Common nickname used frequently",
        )

        assert submission.submitter_email == "jane@example.com"
        assert submission.notes == "Common nickname used frequently"

    def test_alias_validation_rejects_empty(self):
        """Alias validation rejects empty strings."""
        with pytest.raises(ValueError, match="cannot be empty"):
            AliasSubmission(
                contribution_type=ContributionType.ALIAS_ADDITION,
                proposed_alias="   ",  # Only whitespace
                target_node_id="mp_davis_brave",
                source_evidence="Some evidence",
                submitter_name="Jane Doe",
            )

    def test_evidence_validation_requires_length(self):
        """Evidence validation requires minimum length."""
        with pytest.raises(ValueError, match="at least 10 characters"):
            AliasSubmission(
                contribution_type=ContributionType.ALIAS_ADDITION,
                proposed_alias="Papa",
                target_node_id="mp_davis_brave",
                source_evidence="short",  # Too short
                submitter_name="Jane Doe",
            )

    def test_node_id_validation_pattern(self):
        """Node ID must match expected pattern."""
        with pytest.raises(ValueError):
            AliasSubmission(
                contribution_type=ContributionType.ALIAS_ADDITION,
                proposed_alias="Papa",
                target_node_id="invalid_id",  # Doesn't start with mp_
                source_evidence="Valid evidence here",
                submitter_name="Jane Doe",
            )

    def test_assign_id_generates_unique_id(self):
        """assign_id generates a unique submission ID."""
        submission = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Papa",
            target_node_id="mp_davis_brave",
            source_evidence="Valid evidence here",
            submitter_name="Jane Doe",
        )

        assert submission.submission_id is None
        submission.assign_id()
        assert submission.submission_id is not None
        assert submission.submission_id.startswith("sub_")

    def test_set_submitted_at_adds_timestamp(self):
        """set_submitted_at adds ISO timestamp."""
        submission = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Papa",
            target_node_id="mp_davis_brave",
            source_evidence="Valid evidence here",
            submitter_name="Jane Doe",
        )

        assert submission.submitted_at is None
        submission.set_submitted_at()
        assert submission.submitted_at is not None
        assert isinstance(submission.submitted_at, datetime)

    def test_approve_changes_status(self):
        """approve() changes status to APPROVED."""
        submission = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Papa",
            target_node_id="mp_davis_brave",
            source_evidence="Valid evidence here",
            submitter_name="Jane Doe",
        )

        assert submission.status == ContributionStatus.PENDING
        submission.approve("Looks good")
        assert submission.status == ContributionStatus.APPROVED
        assert submission.reviewer_notes == "Looks good"

    def test_reject_changes_status(self):
        """reject() changes status to REJECTED."""
        submission = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Papa",
            target_node_id="mp_davis_brave",
            source_evidence="Valid evidence here",
            submitter_name="Jane Doe",
        )

        assert submission.status == ContributionStatus.PENDING
        submission.reject("Alias already exists")
        assert submission.status == ContributionStatus.REJECTED
        assert submission.reviewer_notes == "Alias already exists"


class TestSubmissionQueue:
    """Test SubmissionQueue functionality."""

    def test_create_empty_queue(self):
        """Create an empty submission queue."""
        queue = SubmissionQueue()

        assert len(queue.submissions) == 0
        assert queue.metadata["total_submissions"] == 0

    def test_add_submission_auto_populates_fields(self):
        """Adding submission auto-populates ID and timestamp."""
        queue = SubmissionQueue()
        submission = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Papa",
            target_node_id="mp_davis_brave",
            source_evidence="Valid evidence here",
            submitter_name="Jane Doe",
        )

        queue.add_submission(submission)

        assert len(queue.submissions) == 1
        assert submission.submission_id is not None
        assert submission.submitted_at is not None
        assert queue.metadata["total_submissions"] == 1

    def test_add_multiple_submissions(self):
        """Add multiple submissions to queue."""
        queue = SubmissionQueue()

        for i in range(3):
            submission = AliasSubmission(
                contribution_type=ContributionType.ALIAS_ADDITION,
                proposed_alias=f"Alias {i}",
                target_node_id="mp_davis_brave",
                source_evidence="Valid evidence here",
                submitter_name=f"Submitter {i}",
            )
            queue.add_submission(submission)

        assert len(queue.submissions) == 3
        assert queue.metadata["total_submissions"] == 3

    def test_get_pending_filters_correctly(self):
        """get_pending returns only pending submissions."""
        queue = SubmissionQueue()

        # Add submissions with different statuses
        sub1 = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Alias 1",
            target_node_id="mp_davis_brave",
            source_evidence="Valid evidence",
            submitter_name="Submitter",
        )
        queue.add_submission(sub1)

        sub2 = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Alias 2",
            target_node_id="mp_davis_brave",
            source_evidence="Valid evidence",
            submitter_name="Submitter",
        )
        queue.add_submission(sub2)

        # Approve one
        sub1.approve("Looks good")

        pending = queue.get_pending()
        assert len(pending) == 1
        assert pending[0].submission_id == sub2.submission_id

    def test_get_by_id_finds_submission(self):
        """get_by_id finds submission by ID."""
        queue = SubmissionQueue()
        submission = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Papa",
            target_node_id="mp_davis_brave",
            source_evidence="Valid evidence",
            submitter_name="Jane Doe",
        )
        queue.add_submission(submission)

        found = queue.get_by_id(submission.submission_id)
        assert found is not None
        assert found.submission_id == submission.submission_id

    def test_get_by_id_returns_none_if_not_found(self):
        """get_by_id returns None if ID not found."""
        queue = SubmissionQueue()

        found = queue.get_by_id("nonexistent_id")
        assert found is None

    def test_status_counts_update(self):
        """Status counts update correctly."""
        queue = SubmissionQueue()

        # Add 3 submissions
        for i in range(3):
            submission = AliasSubmission(
                contribution_type=ContributionType.ALIAS_ADDITION,
                proposed_alias=f"Alias {i}",
                target_node_id="mp_davis_brave",
                source_evidence="Valid evidence",
                submitter_name="Submitter",
            )
            queue.add_submission(submission)

        # All should be pending
        queue._update_status_counts()
        assert queue.metadata["pending_count"] == 3
        assert queue.metadata["approved_count"] == 0
        assert queue.metadata["rejected_count"] == 0

        # Approve one
        queue.submissions[0].approve("Good")
        queue._update_status_counts()
        assert queue.metadata["pending_count"] == 2
        assert queue.metadata["approved_count"] == 1

        # Reject one
        queue.submissions[1].reject("Bad")
        queue._update_status_counts()
        assert queue.metadata["pending_count"] == 1
        assert queue.metadata["rejected_count"] == 1

    def test_save_and_load_queue(self, tmp_path):
        """Save and load queue from file."""
        queue = SubmissionQueue()
        submission = AliasSubmission(
            contribution_type=ContributionType.ALIAS_ADDITION,
            proposed_alias="Papa",
            target_node_id="mp_davis_brave",
            source_evidence="Valid evidence",
            submitter_name="Jane Doe",
        )
        queue.add_submission(submission)

        # Save to file
        output_path = tmp_path / "test_queue.json"
        queue.save_to_file(str(output_path))
        assert output_path.exists()

        # Load from file
        loaded_queue = SubmissionQueue.load_from_file(str(output_path))
        assert len(loaded_queue.submissions) == 1
        assert loaded_queue.submissions[0].proposed_alias == "Papa"
        assert loaded_queue.metadata["total_submissions"] == 1
