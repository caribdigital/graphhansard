"""Tests for interactive graph utilities (MP-5, MP-6).

Tests helper functions for YouTube timestamp links and sentiment badges.
"""

import pytest

from graphhansard.dashboard.interactive_graph import (
    format_youtube_timestamp_link,
    format_sentiment_badge,
)


class TestYouTubeTimestampLinks:
    """Test MP-6: YouTube timestamp link generation."""
    
    def test_basic_timestamp_link(self):
        """Should generate link with timestamp parameter."""
        url = "https://www.youtube.com/watch?v=abc123"
        link = format_youtube_timestamp_link(url, 120.5)
        
        assert "?t=120" in link or "&t=120" in link
        assert "[2:00]" in link  # 120 seconds = 2:00
    
    def test_timestamp_with_existing_params(self):
        """Should append timestamp to existing URL parameters."""
        url = "https://www.youtube.com/watch?v=abc123&feature=share"
        link = format_youtube_timestamp_link(url, 60.0)
        
        assert "&t=60" in link
        assert "feature=share" in link
    
    def test_custom_label(self):
        """Should use custom label when provided."""
        url = "https://www.youtube.com/watch?v=abc123"
        link = format_youtube_timestamp_link(url, 45.5, label="Jump to quote")
        
        assert "[Jump to quote]" in link
        assert "&t=45" in link or "?t=45" in link
    
    def test_timestamp_rounding(self):
        """Should round timestamp to integer seconds."""
        url = "https://www.youtube.com/watch?v=test"
        link = format_youtube_timestamp_link(url, 123.7)
        
        assert "&t=123" in link or "?t=123" in link
    
    def test_zero_timestamp(self):
        """Should handle timestamp at start of video."""
        url = "https://www.youtube.com/watch?v=test"
        link = format_youtube_timestamp_link(url, 0.0)
        
        assert "&t=0" in link or "?t=0" in link


class TestSentimentBadges:
    """Test MP-6: Sentiment badge formatting."""
    
    def test_positive_badge(self):
        """Positive sentiment should have green indicator."""
        badge = format_sentiment_badge("positive")
        
        assert "🟢" in badge
        assert "Positive" in badge
    
    def test_negative_badge(self):
        """Negative sentiment should have red indicator."""
        badge = format_sentiment_badge("negative")
        
        assert "🔴" in badge
        assert "Negative" in badge
    
    def test_neutral_badge(self):
        """Neutral sentiment should have grey indicator."""
        badge = format_sentiment_badge("neutral")
        
        assert "⚫" in badge
        assert "Neutral" in badge
    
    def test_none_sentiment(self):
        """None sentiment should default to neutral."""
        badge = format_sentiment_badge(None)
        
        assert "⚫" in badge
        assert "Neutral" in badge
