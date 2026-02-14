#!/usr/bin/env python3
"""Integration test for CLI commands with mocked dependencies.

This script tests the CLI argument parsing and command routing
without requiring actual ML models to be installed.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Mock all heavy dependencies
sys.modules['numpy'] = MagicMock()
sys.modules['librosa'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['torchaudio'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['faster_whisper'] = MagicMock()
sys.modules['pyannote'] = MagicMock()
sys.modules['pyannote.audio'] = MagicMock()
sys.modules['whisperx'] = MagicMock()
sys.modules['spacy'] = MagicMock()

# Now we can import
from graphhansard.brain.cli import extract_command, sentiment_command, build_graph_command
from graphhansard.brain.entity_extractor import EntityExtractor, MentionRecord, ResolutionMethod
from graphhansard.brain.sentiment import SentimentScorer, SentimentResult, SentimentLabel
from graphhansard.brain.graph_builder import GraphBuilder, SessionGraph, NodeMetrics, EdgeRecord
import argparse


def create_test_data(temp_dir):
    """Create test data files."""
    # Create transcript
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
                "words": []
            }
        ]
    }
    
    transcript_path = temp_dir / "transcript.json"
    with open(transcript_path, "w") as f:
        json.dump(transcript, f)
    
    # Create golden record
    golden_record = {
        "mps": [
            {
                "node_id": "mp_davis_brave",
                "common_name": "Brave Davis",
                "party": "PLP",
                "constituency": "Cat Island",
                "current_portfolio": "Prime Minister"
            },
            {
                "node_id": "mp_pintard_michael",
                "common_name": "Michael Pintard",
                "party": "FNM",
                "constituency": "Marco City",
                "current_portfolio": "Leader of the Opposition"
            }
        ]
    }
    
    golden_path = temp_dir / "mps.json"
    with open(golden_path, "w") as f:
        json.dump(golden_record, f)
    
    return transcript_path, golden_path


def test_extract_command():
    """Test extract command with mocked EntityExtractor."""
    print("Testing extract command...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        transcript_path, golden_path = create_test_data(temp_path)
        
        # Mock EntityExtractor at the point of import
        with patch('graphhansard.brain.entity_extractor.EntityExtractor') as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor_class.return_value = mock_extractor
            
            # Create mock mention
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
                is_self_reference=False
            )
            mock_extractor.extract_mentions.return_value = [mock_mention]
            
            # Create args
            args = argparse.Namespace(
                transcript=str(transcript_path),
                golden_record=str(golden_path),
                output=str(temp_path / "mentions.json"),
                date=None,
                use_spacy=False
            )
            
            # Execute
            result = extract_command(args)
            
            # Verify
            assert result is None, "Extract command should return None on success"
            assert mock_extractor.extract_mentions.called, "extract_mentions should be called"
            
            # Check output file
            output_file = temp_path / "mentions.json"
            assert output_file.exists(), "Output file should be created"
            
            with open(output_file) as f:
                mentions = json.load(f)
                assert len(mentions) == 1, "Should have 1 mention"
                assert mentions[0]["source_node_id"] == "mp_davis_brave"
    
    print("✓ Extract command test passed")


def test_sentiment_command():
    """Test sentiment command with mocked SentimentScorer."""
    print("Testing sentiment command...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create mentions file
        mentions = [{
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
            "is_self_reference": False
        }]
        
        mentions_path = temp_path / "mentions.json"
        with open(mentions_path, "w") as f:
            json.dump(mentions, f)
        
        # Mock SentimentScorer at the point of import
        with patch('graphhansard.brain.sentiment.SentimentScorer') as mock_scorer_class:
            mock_scorer = Mock()
            mock_scorer_class.return_value = mock_scorer
            
            mock_sentiment = Mock()
            mock_sentiment.label.value = "positive"
            mock_sentiment.confidence = 0.85
            mock_sentiment.parliamentary_markers = []
            mock_scorer.score.return_value = mock_sentiment
            
            # Create args
            args = argparse.Namespace(
                mentions=str(mentions_path),
                output=str(temp_path / "scored.json"),
                model="facebook/bart-large-mnli"
            )
            
            # Execute
            result = sentiment_command(args)
            
            # Verify
            assert result is None, "Sentiment command should return None on success"
            assert mock_scorer.score.called, "score should be called"
            
            # Check output
            output_file = temp_path / "scored.json"
            assert output_file.exists(), "Output file should be created"
            
            with open(output_file) as f:
                scored = json.load(f)
                assert len(scored) == 1
                assert scored[0]["sentiment_label"] == "positive"
    
    print("✓ Sentiment command test passed")


def test_build_graph_command():
    """Test build-graph command with mocked GraphBuilder."""
    print("Testing build-graph command...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create scored mentions file
        mentions = [{
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
            "sentiment_confidence": 0.85
        }]
        
        mentions_path = temp_path / "scored.json"
        with open(mentions_path, "w") as f:
            json.dump(mentions, f)
        
        # Mock GraphBuilder at the point of import
        with patch('graphhansard.brain.graph_builder.GraphBuilder') as mock_builder_class:
            mock_builder = Mock()
            mock_builder_class.return_value = mock_builder
            
            mock_graph = Mock()
            mock_graph.node_count = 2
            mock_graph.edge_count = 1
            mock_builder.build_session_graph.return_value = mock_graph
            
            # Create args
            args = argparse.Namespace(
                mentions=str(mentions_path),
                session_id="test_session_001",
                date="2024-01-15",
                output=str(temp_path / "graph.json"),
                golden_record=None,
                graphml=False,
                csv=False
            )
            
            # Execute
            result = build_graph_command(args)
            
            # Verify
            assert result is None, "Build-graph command should return None on success"
            assert mock_builder.build_session_graph.called, "build_session_graph should be called"
            assert mock_builder.export_json.called, "export_json should be called"
    
    print("✓ Build-graph command test passed")


def main():
    """Run all integration tests."""
    print("=" * 70)
    print("CLI Integration Tests")
    print("=" * 70)
    print()
    
    try:
        test_extract_command()
        test_sentiment_command()
        test_build_graph_command()
        
        print()
        print("=" * 70)
        print("✅ All integration tests passed!")
        print("=" * 70)
        return 0
    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ Test failed: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
