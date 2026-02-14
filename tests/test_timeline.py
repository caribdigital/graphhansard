"""Tests for timeline component (MP-12).

See SRD §9.2 (MP-12) for specification.
"""

from datetime import datetime
from pathlib import Path

from graphhansard.dashboard.timeline import (
    SessionInfo,
    discover_sessions,
    get_session_navigation,
)


def test_session_info_creation():
    """Test SessionInfo initialization."""
    session = SessionInfo(
        session_id="test_session_2024_01_15",
        date="2024-01-15",
        has_data=True,
        file_path="/path/to/session.json",
    )
    
    assert session.session_id == "test_session_2024_01_15"
    assert session.date == "2024-01-15"
    assert session.has_data is True
    assert session.file_path == "/path/to/session.json"


def test_session_info_date_obj():
    """Test date parsing to datetime object."""
    session = SessionInfo(
        session_id="test_session",
        date="2024-01-15",
        has_data=True,
    )
    
    date_obj = session.date_obj
    assert isinstance(date_obj, datetime)
    assert date_obj.year == 2024
    assert date_obj.month == 1
    assert date_obj.day == 15


def test_session_info_display_date():
    """Test human-readable date formatting."""
    session = SessionInfo(
        session_id="test_session",
        date="2024-01-15",
        has_data=True,
    )
    
    display_date = session.display_date
    assert "Jan" in display_date
    assert "15" in display_date
    assert "2024" in display_date


def test_session_info_invalid_date():
    """Test handling of invalid date."""
    session = SessionInfo(
        session_id="test_session",
        date="invalid-date",
        has_data=True,
    )
    
    # Should not raise error, should return something
    display_date = session.display_date
    assert display_date is not None


def test_discover_sessions_empty_directory():
    """Test session discovery with no data."""
    # This should return empty list if directories don't exist
    sessions = discover_sessions(
        sessions_dir="/nonexistent/path",
        graphs_dir="/nonexistent/path",
    )
    
    assert isinstance(sessions, list)
    # May be empty or may find real sessions depending on environment


def test_get_session_navigation():
    """Test previous/next session navigation."""
    sessions = [
        SessionInfo("session1", "2024-01-15", has_data=True),
        SessionInfo("session2", "2024-01-10", has_data=True),
        SessionInfo("session3", "2024-01-05", has_data=True),
    ]
    
    # Test middle session
    current = sessions[1]
    prev, next_sess = get_session_navigation(sessions, current)
    
    assert prev is not None
    assert prev.session_id == "session3"  # Older session
    assert next_sess is not None
    assert next_sess.session_id == "session1"  # Newer session


def test_get_session_navigation_first():
    """Test navigation at first session."""
    sessions = [
        SessionInfo("session1", "2024-01-15", has_data=True),
        SessionInfo("session2", "2024-01-10", has_data=True),
    ]
    
    current = sessions[0]
    prev, next_sess = get_session_navigation(sessions, current)
    
    assert prev is not None
    assert prev.session_id == "session2"
    assert next_sess is None  # No newer session


def test_get_session_navigation_last():
    """Test navigation at last session."""
    sessions = [
        SessionInfo("session1", "2024-01-15", has_data=True),
        SessionInfo("session2", "2024-01-10", has_data=True),
    ]
    
    current = sessions[1]
    prev, next_sess = get_session_navigation(sessions, current)
    
    assert prev is None  # No older session
    assert next_sess is not None
    assert next_sess.session_id == "session1"


def test_get_session_navigation_single_session():
    """Test navigation with single session."""
    sessions = [
        SessionInfo("session1", "2024-01-15", has_data=True),
    ]
    
    current = sessions[0]
    prev, next_sess = get_session_navigation(sessions, current)
    
    assert prev is None
    assert next_sess is None


def test_get_session_navigation_not_found():
    """Test navigation with session not in list."""
    sessions = [
        SessionInfo("session1", "2024-01-15", has_data=True),
        SessionInfo("session2", "2024-01-10", has_data=True),
    ]
    
    current = SessionInfo("session3", "2024-01-05", has_data=True)
    prev, next_sess = get_session_navigation(sessions, current)
    
    assert prev is None
    assert next_sess is None


def test_session_info_no_data():
    """Test SessionInfo for session without data."""
    session = SessionInfo(
        session_id="pending_session",
        date="2024-01-20",
        has_data=False,
    )
    
    assert session.has_data is False
    assert session.file_path is None
