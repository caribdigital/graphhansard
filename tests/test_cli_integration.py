"""Integration test for CLI commands with mocked dependencies.

Tests the CLI argument parsing and command routing
without requiring actual ML models to be installed.

All heavy dependency mocking is scoped inside each test function
to avoid poisoning sys.modules for the entire pytest session.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from graphhansard.brain.entity_extractor import EntityExtractor, MentionRecord, ResolutionMethod
from graphhansard.brain.graph_builder import GraphBuilder


def _mock_heavy_modules():
    """Return a dict of heavy modules to mock for CLI imports."""
    return {
        "numpy": MagicMock(),
        "librosa": MagicMock(),
        "torch": MagicMock(),
        "torchaudio": MagicMock(),
        "transformers": MagicMock(),
        "faster_whisper": MagicMock(),
        "pyannote": MagicMock(),
        "pyannote.audio": MagicMock(),
        "whisperx": MagicMock(),
        "spacy": MagicMock(),
    }


def _create_test_data(temp_dir):
    """Create test data files."""
    transcript = {
        "session_id": "test_session_001",
        "segments": [
            {
                "speaker_label": "SPEAKER_00",
                "speaker_node_id": "mp_davis_brave",
                "start_time": 0.0,
                "end_time": 5.5,
                "text": "I thank the honourable Member for Marco City.",
                "confidence": 0.95,
                "words": [],
            }
        ],
    }

    transcript_path = temp_dir / "transcript.json"
    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f)

    golden_record = {
        "mps": [
            {
                "node_id": "mp_davis_brave",
                "common_name": "Brave Davis",
                "party": "PLP",
                "constituency": "Cat Island",
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

    golden_path = temp_dir / "mps.json"
    with open(golden_path, "w", encoding="utf-8") as f:
        json.dump(golden_record, f)

    return transcript_path, golden_path


def test_extract_command():
    """Test extract command with mocked EntityExtractor."""
    import argparse

    from graphhansard.brain.cli import extract_command

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        transcript_path, golden_path = _create_test_data(temp_path)

        with patch("graphhansard.brain.entity_extractor.EntityExtractor") as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor

            mock_mention = MentionRecord(
                session_id="test_session_001",
                source_node_id="mp_davis_brave",
                target_node_id="mp_pintard_michael",
                raw_mention="honourable Member for Marco City",
                resolution_method=ResolutionMethod.EXACT,
                resolution_score=1.0,
                timestamp_start=0.0,
                timestamp_end=5.5,
                context_window="I thank the honourable Member for Marco City.",
                segment_index=0,
                is_self_reference=False,
            )
            mock_extractor.extract_mentions.return_value = [mock_mention]

            args = argparse.Namespace(
                transcript=str(transcript_path),
                golden_record=str(golden_path),
                output=str(temp_path / "mentions.json"),
                date=None,
                use_spacy=False,
            )

            result = extract_command(args)

            assert result is None, "Extract command should return None on success"
            assert mock_extractor.extract_mentions.called, "extract_mentions should be called"

            output_file = temp_path / "mentions.json"
            assert output_file.exists(), "Output file should be created"

            with open(output_file, encoding="utf-8") as f:
                mentions = json.load(f)
                assert len(mentions) == 1, "Should have 1 mention"
                assert mentions[0]["source_node_id"] == "mp_davis_brave"


def test_sentiment_command():
    """Test sentiment command with mocked SentimentScorer."""
    import argparse

    from graphhansard.brain.cli import sentiment_command

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        mentions = [
            {
                "session_id": "test_session_001",
                "source_node_id": "mp_davis_brave",
                "target_node_id": "mp_pintard_michael",
                "raw_mention": "honourable Member",
                "resolution_method": "exact",
                "resolution_score": 1.0,
                "timestamp_start": 0.0,
                "timestamp_end": 5.5,
                "context_window": "I thank the honourable Member.",
                "segment_index": 0,
                "is_self_reference": False,
            }
        ]

        mentions_path = temp_path / "mentions.json"
        with open(mentions_path, "w", encoding="utf-8") as f:
            json.dump(mentions, f)

        with patch("graphhansard.brain.sentiment.SentimentScorer") as mock_scorer_class:
            mock_scorer = Mock()
            mock_scorer_class.return_value = mock_scorer

            mock_sentiment = Mock()
            mock_sentiment.label.value = "positive"
            mock_sentiment.confidence = 0.85
            mock_sentiment.parliamentary_markers = []
            mock_scorer.score.return_value = mock_sentiment

            args = argparse.Namespace(
                mentions=str(mentions_path),
                output=str(temp_path / "scored.json"),
                model="facebook/bart-large-mnli",
            )

            result = sentiment_command(args)

            assert result is None, "Sentiment command should return None on success"
            assert mock_scorer.score.called, "score should be called"

            output_file = temp_path / "scored.json"
            assert output_file.exists(), "Output file should be created"

            with open(output_file, encoding="utf-8") as f:
                scored = json.load(f)
                assert len(scored) == 1
                assert scored[0]["sentiment_label"] == "positive"


def test_build_graph_command():
    """Test build-graph command with mocked GraphBuilder."""
    import argparse

    from graphhansard.brain.cli import build_graph_command

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        mentions = [
            {
                "session_id": "test_session_001",
                "source_node_id": "mp_davis_brave",
                "target_node_id": "mp_pintard_michael",
                "raw_mention": "honourable Member",
                "resolution_method": "exact",
                "resolution_score": 1.0,
                "timestamp_start": 0.0,
                "timestamp_end": 5.5,
                "context_window": "I thank the honourable Member.",
                "segment_index": 0,
                "is_self_reference": False,
                "sentiment_label": "positive",
                "sentiment_confidence": 0.85,
            }
        ]

        mentions_path = temp_path / "scored.json"
        with open(mentions_path, "w", encoding="utf-8") as f:
            json.dump(mentions, f)

        with patch("graphhansard.brain.graph_builder.GraphBuilder") as mock_builder_class:
            mock_builder = Mock()
            mock_builder_class.return_value = mock_builder

            mock_graph = Mock()
            mock_graph.node_count = 2
            mock_graph.edge_count = 1
            mock_builder.build_session_graph.return_value = mock_graph

            args = argparse.Namespace(
                mentions=str(mentions_path),
                session_id="test_session_001",
                date="2024-01-15",
                output=str(temp_path / "graph.json"),
                golden_record=None,
                graphml=False,
                csv=False,
                skip_validation=True,
            )

            result = build_graph_command(args)

            assert result is None, "Build-graph command should return None on success"
            assert mock_builder.build_session_graph.called, "build_session_graph should be called"
            assert mock_builder.export_json.called, "export_json should be called"
