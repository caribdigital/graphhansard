"""Security and privacy compliance tests.

Implements verification for NF-9, NF-10, and NF-11:
- No personal data beyond public parliamentary record
- Credentials excluded from version control
- No private citizen data stored

These tests ensure the system remains compliant with security and privacy requirements.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


class TestSecurityPrivacy:
    """Test suite for security and privacy requirements (NF-9 through NF-11)."""

    def test_gitignore_excludes_credentials(self):
        """Verify .gitignore excludes credential files (NF-10)."""
        gitignore_path = Path(".gitignore")
        assert gitignore_path.exists(), ".gitignore file must exist"

        content = gitignore_path.read_text()

        # Required patterns per NF-10
        required_patterns = [
            "*.cookies",
            "cookies.txt",
            ".env",
            "*.key",
            "*.pem",
            "credentials.*",
            "secrets.*",
        ]

        for pattern in required_patterns:
            assert pattern in content, f".gitignore must exclude {pattern}"

    def test_no_pii_in_golden_record(self):
        """Verify Golden Record contains no PII beyond public parliamentary data (NF-9, NF-11)."""
        golden_record_path = Path("golden_record/mps.json")
        if not golden_record_path.exists():
            pytest.skip("Golden Record not found")

        with open(golden_record_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Verify only MP data (no private citizens)
        mps = data.get("mps", [])
        for mp in mps:
            # Check that node_id indicates this is an elected MP
            node_id = mp.get("node_id", "")
            assert node_id.startswith("mp_") or node_id.startswith("speaker_"), (
                f"Golden Record should only contain MPs, found: {node_id}"
            )

            # Verify no home addresses
            mp_str = json.dumps(mp)
            assert "home address" not in mp_str.lower(), (
                f"MP {node_id} should not contain home address"
            )

            # Verify no phone numbers (comprehensive patterns)
            # North American format
            phone_pattern_na = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
            # International format
            phone_pattern_intl = r'\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}'
            # Bahamian format
            phone_pattern_bs = r'\b242[-.\s]?\d{3}[-.\s]?\d{4}\b'
            
            assert not re.search(phone_pattern_na, mp_str), (
                f"MP {node_id} should not contain phone numbers (NA format)"
            )
            assert not re.search(phone_pattern_intl, mp_str), (
                f"MP {node_id} should not contain phone numbers (international format)"
            )
            assert not re.search(phone_pattern_bs, mp_str), (
                f"MP {node_id} should not contain phone numbers (Bahamian format)"
            )

    def test_no_pii_in_source_code(self):
        """Verify source code contains no hardcoded PII (NF-9)."""
        src_path = Path("src/graphhansard")
        if not src_path.exists():
            pytest.skip("Source directory not found")

        # Patterns that should NOT appear in production code
        # (Excluding test files and examples)
        sensitive_patterns = [
            # North American format: XXX-XXX-XXXX or (XXX) XXX-XXXX
            (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', "phone number (North American)"),
            # International format: +XX XXX XXX XXXX or similar
            (r'\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}', "phone number (international)"),
            # Bahamian format: 242-XXX-XXXX
            (r'\b242[-.\s]?\d{3}[-.\s]?\d{4}\b', "phone number (Bahamian)"),
        ]

        violations = []

        for py_file in src_path.rglob("*.py"):
            # Skip test files
            if "test_" in py_file.name:
                continue

            content = py_file.read_text(encoding="utf-8")

            for pattern, description in sensitive_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(f"{py_file}: Found {description}: {matches}")

        assert not violations, "Found PII in source code:\n" + "\n".join(violations)

    def test_community_contributions_email_optional(self):
        """Verify email field in contributions is optional (NF-9)."""
        contributions_module = Path("src/graphhansard/golden_record/contributions.py")
        if not contributions_module.exists():
            pytest.skip("Contributions module not found")

        content = contributions_module.read_text()

        # Verify submitter_email is optional (has default=None)
        assert "submitter_email: str | None" in content, (
            "submitter_email must be optional"
        )
        assert "default=None" in content, (
            "submitter_email must have default=None"
        )

    def test_no_private_citizens_in_data(self):
        """Verify no private citizens are assigned node IDs (NF-11)."""
        # This test ensures only MPs (elected officials in public capacity) get node IDs
        golden_record_path = Path("golden_record/mps.json")
        if not golden_record_path.exists():
            pytest.skip("Golden Record not found")

        with open(golden_record_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        mps = data.get("mps", [])

        for mp in mps:
            node_id = mp.get("node_id", "")
            seat_status = mp.get("seat_status", "")

            # Verify all entries are either:
            # 1. Active MPs (seat_status = "active")
            # 2. Former MPs (seat_status might be "resigned", "defeated", etc.)
            # 3. Speaker (node_id starts with "speaker_")
            
            assert node_id.startswith(("mp_", "speaker_")), (
                f"Invalid node_id format: {node_id}"
            )

            # Verify this is an elected official
            assert "constituency" in mp or node_id.startswith("speaker_"), (
                f"{node_id} must have a constituency (elected MPs only)"
            )

    def test_gitignore_excludes_contribution_queue(self):
        """Verify contribution queue (may contain submitter info) is excluded (NF-9)."""
        gitignore_path = Path(".gitignore")
        content = gitignore_path.read_text()

        # Contribution queue file should be excluded as it may contain submitter emails
        assert "contributions_queue.json" in content, (
            "contributions_queue.json must be excluded from git"
        )
