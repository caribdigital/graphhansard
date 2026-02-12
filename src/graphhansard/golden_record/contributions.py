"""Community contribution models and schemas for the Golden Record.

Implements GR-9: Provide a structured mechanism for community-submitted
alias additions and corrections.

Submission format includes:
- Proposed alias
- Target node_id
- Source/evidence
- Submitter information
- Timestamp
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ContributionType(str, Enum):
    """Type of community contribution."""

    ALIAS_ADDITION = "alias_addition"
    ALIAS_CORRECTION = "alias_correction"


class ContributionStatus(str, Enum):
    """Status of a community contribution."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AliasSubmission(BaseModel):
    """Schema for a community-submitted alias addition or correction.

    Per GR-9 acceptance criteria:
    - proposed_alias: The alias to add or correct
    - target_node_id: The MP this alias refers to
    - source_evidence: Documentation/evidence for this alias
    - submitter: Information about who submitted this
    """

    contribution_type: ContributionType = Field(
        description="Type of contribution: addition or correction"
    )
    proposed_alias: str = Field(
        description="The alias being proposed (e.g., 'Papa', 'The PM')",
        min_length=1,
    )
    target_node_id: str = Field(
        description="The node_id this alias refers to (e.g., 'mp_davis_brave')",
        pattern=r"^mp_[a-z_]+$",
    )
    source_evidence: str = Field(
        description=(
            "Evidence for this alias: URL to parliamentary video, "
            "Hansard citation, news article, etc."
        ),
        min_length=10,
    )
    submitter_name: str = Field(
        description="Name of the person submitting (can be anonymous)",
        min_length=1,
    )
    submitter_email: str | None = Field(
        default=None, description="Optional email for follow-up"
    )
    notes: str | None = Field(
        default=None, description="Additional context or notes"
    )

    # System fields (auto-populated)
    submission_id: str | None = Field(
        default=None, description="Unique ID (auto-generated)"
    )
    submitted_at: str | None = Field(
        default=None, description="ISO timestamp (auto-generated)"
    )
    status: ContributionStatus = Field(
        default=ContributionStatus.PENDING, description="Review status"
    )
    reviewer_notes: str | None = Field(
        default=None, description="Notes from reviewer"
    )

    @field_validator("proposed_alias")
    @classmethod
    def validate_alias(cls, v: str) -> str:
        """Validate the proposed alias is not empty after stripping."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Alias cannot be empty or only whitespace")
        return stripped

    @field_validator("source_evidence")
    @classmethod
    def validate_evidence(cls, v: str) -> str:
        """Validate evidence is substantial."""
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError(
                "Evidence must be at least 10 characters "
                "(e.g., URL, citation, description)"
            )
        return stripped

    def assign_id(self) -> None:
        """Assign a unique submission ID based on timestamp."""
        if not self.submission_id:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            self.submission_id = f"sub_{timestamp}"

    def set_submitted_at(self) -> None:
        """Set the submission timestamp."""
        if not self.submitted_at:
            self.submitted_at = datetime.now(timezone.utc).isoformat()

    def approve(self, reviewer_notes: str | None = None) -> None:
        """Mark this submission as approved.

        Args:
            reviewer_notes: Optional notes from the reviewer
        """
        self.status = ContributionStatus.APPROVED
        if reviewer_notes:
            self.reviewer_notes = reviewer_notes

    def reject(self, reviewer_notes: str) -> None:
        """Mark this submission as rejected.

        Args:
            reviewer_notes: Reason for rejection (required)
        """
        self.status = ContributionStatus.REJECTED
        self.reviewer_notes = reviewer_notes


class SubmissionQueue(BaseModel):
    """Container for community submissions (review queue).

    This is the review queue referenced in GR-9:
    'Submissions logged to a review queue (not auto-merged)'
    """

    metadata: dict[str, Any] = Field(
        default_factory=lambda: {
            "queue_created": datetime.now(timezone.utc).isoformat(),
            "total_submissions": 0,
            "pending_count": 0,
            "approved_count": 0,
            "rejected_count": 0,
        }
    )
    submissions: list[AliasSubmission] = Field(default_factory=list)

    def add_submission(self, submission: AliasSubmission) -> None:
        """Add a new submission to the queue.

        Args:
            submission: The submission to add
        """
        # Auto-populate system fields
        submission.assign_id()
        submission.set_submitted_at()

        # Add to queue
        self.submissions.append(submission)

        # Update metadata
        self.metadata["total_submissions"] += 1
        self._update_status_counts()

    def get_pending(self) -> list[AliasSubmission]:
        """Get all pending submissions."""
        return [s for s in self.submissions if s.status == ContributionStatus.PENDING]

    def get_by_id(self, submission_id: str) -> AliasSubmission | None:
        """Get a submission by ID.

        Args:
            submission_id: The submission ID to find

        Returns:
            The submission if found, None otherwise
        """
        return next(
            (s for s in self.submissions if s.submission_id == submission_id),
            None,
        )

    def _update_status_counts(self) -> None:
        """Update status counts in metadata."""
        self.metadata["pending_count"] = sum(
            1 for s in self.submissions if s.status == ContributionStatus.PENDING
        )
        self.metadata["approved_count"] = sum(
            1 for s in self.submissions if s.status == ContributionStatus.APPROVED
        )
        self.metadata["rejected_count"] = sum(
            1 for s in self.submissions if s.status == ContributionStatus.REJECTED
        )

    def save_to_file(self, output_path: str) -> None:
        """Save the submission queue to a JSON file.

        Args:
            output_path: Path to save the queue
        """
        # Update counts before saving
        self._update_status_counts()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load_from_file(cls, file_path: str) -> SubmissionQueue:
        """Load a submission queue from a JSON file.

        Args:
            file_path: Path to the queue file

        Returns:
            SubmissionQueue instance
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return cls.model_validate_json(f.read())
