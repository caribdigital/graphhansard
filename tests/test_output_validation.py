"""Tests for output validation functionality."""

import json
from pathlib import Path

import pytest

from graphhansard.brain.validation import ValidationResult, ValidationReport, validate_output


class TestValidateOutput:
    """Tests for validate_output function."""

    def test_all_checks_pass(self, tmp_path):
        """Test validation when all checks pass."""
        session_graph = {
            "session_id": "test_session_001",
            "date": "2024-01-15",
            "graph_file": "graphs/sessions/test_session_001.graphml",
            "node_count": 10,
            "edge_count": 15,
            "nodes": [
                {
                    "node_id": "mp_001",
                    "common_name": "John Smith",
                    "party": "FNM",
                    "constituency": "Nassau East",
                    "degree_in": 3,
                    "degree_out": 2,
                },
                {
                    "node_id": "mp_002",
                    "common_name": "Jane Doe",
                    "party": "PLP",
                    "constituency": "Grand Bahama West",
                    "degree_in": 2,
                    "degree_out": 3,
                },
                {
                    "node_id": "mp_003",
                    "common_name": "Bob Johnson",
                    "party": "FNM",
                    "degree_in": 1,
                    "degree_out": 1,
                },
                {
                    "node_id": "mp_004",
                    "common_name": "Alice Williams",
                    "party": "PLP",
                    "degree_in": 2,
                    "degree_out": 2,
                },
                {
                    "node_id": "speaker_001",
                    "common_name": "Speaker Robinson",
                    "party": "Independent",
                    "degree_in": 5,
                    "degree_out": 5,
                },
            ],
            "edges": [
                {
                    "source_node_id": "mp_001",
                    "target_node_id": "mp_002",
                    "total_mentions": 5,
                    "positive_count": 2,
                    "neutral_count": 2,
                    "negative_count": 1,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "speaker_001",
                    "target_node_id": "mp_001",
                    "total_mentions": 3,
                    "positive_count": 3,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": True,
                },
                {
                    "source_node_id": "mp_002",
                    "target_node_id": "mp_003",
                    "total_mentions": 4,
                    "positive_count": 1,
                    "neutral_count": 2,
                    "negative_count": 1,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_003",
                    "target_node_id": "mp_004",
                    "total_mentions": 2,
                    "positive_count": 0,
                    "neutral_count": 1,
                    "negative_count": 1,
                    "is_procedural": False,
                },
            ],
        }

        report = validate_output(session_graph, "test_session_001", tmp_path)

        assert report.session_id == "test_session_001"
        assert report.overall_status == "PASS"
        assert len(report.checks) == 6

        for check in report.checks:
            assert check.status == "PASS"

        # Verify report file was created
        report_file = tmp_path / "validation_test_session_001.json"
        assert report_file.exists()

        with open(report_file) as f:
            saved_report = json.load(f)
        assert saved_report["session_id"] == "test_session_001"
        assert saved_report["overall_status"] == "PASS"

    def test_enrichment_check_fails(self):
        """Test enrichment check fails when all nodes have party='Unknown'."""
        session_graph = {
            "session_id": "test_session_002",
            "nodes": [
                {"node_id": "mp_001", "common_name": "John Smith", "party": "Unknown"},
                {"node_id": "mp_002", "common_name": "Jane Doe", "party": "Unknown"},
                {"node_id": "mp_003", "common_name": "Bob Johnson", "party": "Unknown"},
                {"node_id": "mp_004", "common_name": "Alice Williams", "party": "Unknown"},
                {"node_id": "mp_005", "common_name": "Charlie Brown", "party": "Unknown"},
            ],
            "edges": [
                {
                    "source_node_id": "mp_001",
                    "target_node_id": "mp_002",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_002",
                    "target_node_id": "mp_003",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_003",
                    "target_node_id": "mp_004",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
            ],
        }

        report = validate_output(session_graph, "test_session_002")

        enrichment_check = next(c for c in report.checks if c.check_name == "enrichment")
        assert enrichment_check.status == "FAIL"
        assert "No nodes have party information" in enrichment_check.message
        assert enrichment_check.details["enriched_count"] == 0
        assert enrichment_check.details["total_count"] == 5

        assert report.overall_status == "FAIL"

    def test_common_names_check_fails(self):
        """Test common names check fails when node has common_name == node_id."""
        session_graph = {
            "session_id": "test_session_003",
            "nodes": [
                {"node_id": "mp_001", "common_name": "mp_001", "party": "FNM"},  # Invalid
                {"node_id": "mp_002", "common_name": "Jane Doe", "party": "PLP"},
                {"node_id": "mp_003", "common_name": "mp_003", "party": "FNM"},  # Invalid
                {"node_id": "mp_004", "common_name": "Alice Williams", "party": "PLP"},
                {"node_id": "speaker_001", "common_name": "Speaker Robinson", "party": "Independent"},
            ],
            "edges": [
                {
                    "source_node_id": "mp_001",
                    "target_node_id": "mp_002",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_002",
                    "target_node_id": "mp_003",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_003",
                    "target_node_id": "mp_004",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
            ],
        }

        report = validate_output(session_graph, "test_session_003")

        names_check = next(c for c in report.checks if c.check_name == "common_names")
        assert names_check.status == "FAIL"
        assert "2 nodes have unresolved names" in names_check.message
        assert names_check.details["unresolved_count"] == 2
        assert "mp_001" in names_check.details["examples"]
        assert "mp_003" in names_check.details["examples"]

        assert report.overall_status == "FAIL"

    def test_procedural_edges_check_warns(self):
        """Test procedural edges check warns when no procedural edges found."""
        session_graph = {
            "session_id": "test_session_004",
            "nodes": [
                {"node_id": "mp_001", "common_name": "John Smith", "party": "FNM"},
                {"node_id": "mp_002", "common_name": "Jane Doe", "party": "PLP"},
                {"node_id": "mp_003", "common_name": "Bob Johnson", "party": "FNM"},
                {"node_id": "mp_004", "common_name": "Alice Williams", "party": "PLP"},
                {"node_id": "mp_005", "common_name": "Charlie Brown", "party": "Independent"},
            ],
            "edges": [
                {
                    "source_node_id": "mp_001",
                    "target_node_id": "mp_002",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_002",
                    "target_node_id": "mp_003",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_003",
                    "target_node_id": "mp_004",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
            ],
        }

        report = validate_output(session_graph, "test_session_004")

        procedural_check = next(c for c in report.checks if c.check_name == "procedural_edges")
        assert procedural_check.status == "WARN"
        assert "No procedural edges found" in procedural_check.message
        assert procedural_check.details["procedural_count"] == 0
        assert procedural_check.details["total_count"] == 3

        assert report.overall_status == "WARN"

    def test_sentiment_distribution_check_warns(self):
        """Test sentiment distribution check warns when >80% positive."""
        session_graph = {
            "session_id": "test_session_005",
            "nodes": [
                {"node_id": "mp_001", "common_name": "John Smith", "party": "FNM"},
                {"node_id": "mp_002", "common_name": "Jane Doe", "party": "PLP"},
                {"node_id": "mp_003", "common_name": "Bob Johnson", "party": "FNM"},
                {"node_id": "mp_004", "common_name": "Alice Williams", "party": "PLP"},
                {"node_id": "mp_005", "common_name": "Charlie Brown", "party": "Independent"},
            ],
            "edges": [
                {
                    "source_node_id": "mp_001",
                    "target_node_id": "mp_002",
                    "total_mentions": 10,
                    "positive_count": 9,  # 90% positive
                    "neutral_count": 1,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_002",
                    "target_node_id": "mp_003",
                    "total_mentions": 10,
                    "positive_count": 8,  # 80% positive
                    "neutral_count": 2,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "speaker_001",
                    "target_node_id": "mp_001",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": True,
                },
            ],
        }

        report = validate_output(session_graph, "test_session_005")

        sentiment_check = next(c for c in report.checks if c.check_name == "sentiment_distribution")
        assert sentiment_check.status == "WARN"
        assert "Sentiment may be biased" in sentiment_check.message
        # Total: 18 positive out of 21 = 85.7%
        assert sentiment_check.details["positive_percentage"] > 80
        assert sentiment_check.details["positive_count"] == 18
        assert sentiment_check.details["total_count"] == 21

        assert report.overall_status == "WARN"

    def test_node_count_check_fails(self):
        """Test node count check fails when < 5 nodes."""
        session_graph = {
            "session_id": "test_session_006",
            "nodes": [
                {"node_id": "mp_001", "common_name": "John Smith", "party": "FNM"},
                {"node_id": "mp_002", "common_name": "Jane Doe", "party": "PLP"},
                {"node_id": "mp_003", "common_name": "Bob Johnson", "party": "FNM"},
            ],
            "edges": [
                {
                    "source_node_id": "mp_001",
                    "target_node_id": "mp_002",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_002",
                    "target_node_id": "mp_003",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
                {
                    "source_node_id": "mp_003",
                    "target_node_id": "mp_001",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
            ],
        }

        report = validate_output(session_graph, "test_session_006")

        node_count_check = next(c for c in report.checks if c.check_name == "node_count")
        assert node_count_check.status == "FAIL"
        assert "Session has only 3 nodes" in node_count_check.message
        assert node_count_check.details["node_count"] == 3
        assert node_count_check.details["minimum"] == 5

        assert report.overall_status == "FAIL"

    def test_edge_count_check_fails(self):
        """Test edge count check fails when < 3 edges."""
        session_graph = {
            "session_id": "test_session_007",
            "nodes": [
                {"node_id": "mp_001", "common_name": "John Smith", "party": "FNM"},
                {"node_id": "mp_002", "common_name": "Jane Doe", "party": "PLP"},
                {"node_id": "mp_003", "common_name": "Bob Johnson", "party": "FNM"},
                {"node_id": "mp_004", "common_name": "Alice Williams", "party": "PLP"},
                {"node_id": "mp_005", "common_name": "Charlie Brown", "party": "Independent"},
            ],
            "edges": [
                {
                    "source_node_id": "mp_001",
                    "target_node_id": "mp_002",
                    "total_mentions": 1,
                    "positive_count": 1,
                    "neutral_count": 0,
                    "negative_count": 0,
                    "is_procedural": False,
                },
            ],
        }

        report = validate_output(session_graph, "test_session_007")

        edge_count_check = next(c for c in report.checks if c.check_name == "edge_count")
        assert edge_count_check.status == "FAIL"
        assert "Session has only 1 edge" in edge_count_check.message
        assert edge_count_check.details["edge_count"] == 1
        assert edge_count_check.details["minimum"] == 3

        assert report.overall_status == "FAIL"

    def test_empty_graph(self):
        """Test validation with empty graph."""
        session_graph = {
            "session_id": "test_session_008",
            "nodes": [],
            "edges": [],
        }

        report = validate_output(session_graph, "test_session_008")

        assert report.overall_status == "FAIL"

        node_count_check = next(c for c in report.checks if c.check_name == "node_count")
        assert node_count_check.status == "FAIL"

        edge_count_check = next(c for c in report.checks if c.check_name == "edge_count")
        assert edge_count_check.status == "FAIL"

    def test_validation_with_pydantic_model(self, tmp_path):
        """Test validation accepts pydantic model with model_dump()."""

        class MockSessionGraph:
            def model_dump(self):
                return {
                    "session_id": "test_session_009",
                    "nodes": [
                        {"node_id": "mp_001", "common_name": "John Smith", "party": "FNM"},
                        {"node_id": "mp_002", "common_name": "Jane Doe", "party": "PLP"},
                        {"node_id": "mp_003", "common_name": "Bob Johnson", "party": "FNM"},
                        {"node_id": "mp_004", "common_name": "Alice Williams", "party": "PLP"},
                        {"node_id": "mp_005", "common_name": "Charlie Brown", "party": "Independent"},
                    ],
                    "edges": [
                        {
                            "source_node_id": "mp_001",
                            "target_node_id": "mp_002",
                            "total_mentions": 1,
                            "positive_count": 1,
                            "neutral_count": 0,
                            "negative_count": 0,
                            "is_procedural": False,
                        },
                        {
                            "source_node_id": "mp_002",
                            "target_node_id": "mp_003",
                            "total_mentions": 1,
                            "positive_count": 1,
                            "neutral_count": 0,
                            "negative_count": 0,
                            "is_procedural": False,
                        },
                        {
                            "source_node_id": "speaker_001",
                            "target_node_id": "mp_001",
                            "total_mentions": 1,
                            "positive_count": 1,
                            "neutral_count": 0,
                            "negative_count": 0,
                            "is_procedural": True,
                        },
                    ],
                }

        mock_graph = MockSessionGraph()
        report = validate_output(mock_graph, "test_session_009", tmp_path)

        assert report.session_id == "test_session_009"
        assert len(report.checks) == 6
