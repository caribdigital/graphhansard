"""Tests for GraphHansard Brain CLI commands.

Covers: extract, sentiment, build-graph, and process commands.
Tests CLI argument parsing and command routing.

Note: These tests mock the actual command functions to avoid requiring
all brain dependencies (numpy, transformers, etc.) to be installed.
"""

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call
import sys

import pytest


@pytest.fixture
def sample_transcript(tmp_path):
    """Create a sample transcript JSON file for testing."""
    transcript = {
        "session_id": "test_session_001",
        "segments": [
            {
                "speaker_label": "SPEAKER_00",
                "speaker_node_id": "mp_davis_brave",
                "start_time": 0.0,
                "end_time": 5.0,
                "text": "The Prime Minister spoke about the bill.",
                "confidence": 0.95,
                "words": [],
            },
            {
                "speaker_label": "SPEAKER_01",
                "speaker_node_id": "mp_pintard_michael",
                "start_time": 5.0,
                "end_time": 10.0,
                "text": "I commend the Minister of Finance for his work.",
                "confidence": 0.92,
                "words": [],
            },
        ],
    }
    
    transcript_path = tmp_path / "test_transcript.json"
    with open(transcript_path, "w") as f:
        json.dump(transcript, f)
    
    return transcript_path


@pytest.fixture
def sample_mentions(tmp_path):
    """Create sample mention records for testing."""
    mentions = [
        {
            "session_id": "test_session_001",
            "source_node_id": "mp_davis_brave",
            "target_node_id": "mp_pintard_michael",
            "raw_mention": "The Leader of the Opposition",
            "resolution_method": "exact",
            "resolution_score": 1.0,
            "timestamp_start": 0.0,
            "timestamp_end": 2.0,
            "context_window": "The Leader of the Opposition raised a valid point.",
            "segment_index": 0,
            "is_self_reference": False,
        },
        {
            "session_id": "test_session_001",
            "source_node_id": "mp_pintard_michael",
            "target_node_id": "mp_davis_brave",
            "raw_mention": "The Prime Minister",
            "resolution_method": "exact",
            "resolution_score": 1.0,
            "timestamp_start": 5.0,
            "timestamp_end": 7.0,
            "context_window": "I commend the Prime Minister for his leadership.",
            "segment_index": 1,
            "is_self_reference": False,
        },
    ]
    
    mentions_path = tmp_path / "test_mentions.json"
    with open(mentions_path, "w") as f:
        json.dump(mentions, f)
    
    return mentions_path


@pytest.fixture
def sample_golden_record(tmp_path):
    """Create a sample golden record file for testing."""
    golden_record = {
        "mps": [
            {
                "node_id": "mp_davis_brave",
                "common_name": "Brave Davis",
                "party": "PLP",
                "constituency": "Cat Island, Rum Cay and San Salvador",
                "current_portfolio": "Prime Minister",
            },
            {
                "node_id": "mp_pintard_michael",
                "common_name": "Michael Pintard",
                "party": "FNM",
                "constituency": "Marco City",
                "current_portfolio": "Leader of the Opposition",
            },
        ]
    }
    
    golden_path = tmp_path / "mps.json"
    with open(golden_path, "w") as f:
        json.dump(golden_record, f)
    
    return golden_path


class TestExtractCommand:
    """Test the extract CLI command argument parsing."""

    def test_extract_command_help_available(self):
        """Test that extract command help is available."""
        with patch("sys.argv", ["cli.py", "extract", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                with patch.dict(sys.modules, {"numpy": MagicMock()}):
                    from graphhansard.brain.cli import main
                    main()
            assert exc_info.value.code == 0  # Help exits successfully


class TestSentimentCommand:
    """Test the sentiment CLI command argument parsing."""

    def test_sentiment_command_help_available(self):
        """Test that sentiment command help is available."""
        with patch("sys.argv", ["cli.py", "sentiment", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                with patch.dict(sys.modules, {"numpy": MagicMock()}):
                    from graphhansard.brain.cli import main
                    main()
            assert exc_info.value.code == 0


class TestBuildGraphCommand:
    """Test the build-graph CLI command argument parsing."""

    def test_build_graph_command_help_available(self):
        """Test that build-graph command help is available."""
        with patch("sys.argv", ["cli.py", "build-graph", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                with patch.dict(sys.modules, {"numpy": MagicMock()}):
                    from graphhansard.brain.cli import main
                    main()
            assert exc_info.value.code == 0


class TestProcessCommand:
    """Test the process CLI command argument parsing."""

    def test_process_command_help_available(self):
        """Test that process command help is available."""
        with patch("sys.argv", ["cli.py", "process", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                with patch.dict(sys.modules, {"numpy": MagicMock()}):
                    from graphhansard.brain.cli import main
                    main()
            assert exc_info.value.code == 0


class TestCLIMain:
    """Test the main CLI entry point and argument parsing."""

    def test_main_has_extract_command(self):
        """Test that extract command is available."""
        with patch("sys.argv", ["cli.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                # We need to import inside the test after patching dependencies
                with patch.dict(sys.modules, {"numpy": MagicMock()}):
                    from graphhansard.brain.cli import main
                    main()
            # Help exits with 0
            assert exc_info.value.code == 0

    def test_extract_command_requires_transcript(self):
        """Test that extract command requires a transcript argument."""
        with patch("sys.argv", ["cli.py", "extract"]):
            with pytest.raises(SystemExit) as exc_info:
                with patch.dict(sys.modules, {"numpy": MagicMock()}):
                    from graphhansard.brain.cli import main
                    main()
            # Missing required argument should exit with error
            assert exc_info.value.code != 0

    def test_sentiment_command_exists(self):
        """Test that sentiment command exists."""
        # Just check that the command can be parsed
        with patch("sys.argv", ["cli.py", "sentiment", "/tmp/test.json"]):
            with patch.dict(sys.modules, {"numpy": MagicMock()}):
                from graphhansard.brain.cli import main
                # Mock the actual command function to avoid execution
                with patch("graphhansard.brain.cli.sentiment_command", return_value=0):
                    result = main()
                    assert result == 0

    def test_build_graph_command_exists(self):
        """Test that build-graph command exists with required args."""
        with patch("sys.argv", ["cli.py", "build-graph", "/tmp/test.json", "--session-id", "test", "--date", "2024-01-15"]):
            with patch.dict(sys.modules, {"numpy": MagicMock()}):
                from graphhansard.brain.cli import main
                # Mock the actual command function
                with patch("graphhansard.brain.cli.build_graph_command", return_value=0):
                    result = main()
                    assert result == 0

    def test_process_command_exists(self):
        """Test that process command exists with required args."""
        with patch("sys.argv", ["cli.py", "process", "/tmp/audio.mp3", "--session-id", "test", "--golden-record", "/tmp/mps.json"]):
            with patch.dict(sys.modules, {"numpy": MagicMock()}):
                from graphhansard.brain.cli import main
                # Mock the actual command function
                with patch("graphhansard.brain.cli.process_command", return_value=0):
                    result = main()
                    assert result == 0

    def test_info_command_exists(self):
        """Test that info command exists."""
        with patch("sys.argv", ["cli.py", "info"]):
            with patch.dict(sys.modules, {"numpy": MagicMock()}):
                from graphhansard.brain.cli import main
                # Info command should work without any mocking
                # It just prints information
                with patch("builtins.print"):  # Suppress output
                    result = main()
                    assert result is None or result == 0
