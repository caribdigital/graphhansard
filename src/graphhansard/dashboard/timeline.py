"""Session Timeline component for GraphHansard dashboard.

Implements MP-12: Horizontal timeline of sessions for temporal exploration.

See SRD §9.2 (MP-12) for specification.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import streamlit as st


class SessionInfo:
    """Information about a parliamentary session."""
    
    def __init__(
        self,
        session_id: str,
        date: str,
        has_data: bool = False,
        file_path: str | None = None,
    ):
        """Initialize session info.
        
        Args:
            session_id: Unique session identifier
            date: Session date (ISO format YYYY-MM-DD)
            has_data: Whether graph data is available for this session
            file_path: Optional path to session data file
        """
        self.session_id = session_id
        self.date = date
        self.has_data = has_data
        self.file_path = file_path
    
    @property
    def date_obj(self) -> datetime:
        """Parse date string to datetime object."""
        try:
            return datetime.fromisoformat(self.date)
        except (ValueError, TypeError):
            # Fallback for invalid dates
            return datetime.now()
    
    @property
    def display_date(self) -> str:
        """Human-readable date string."""
        try:
            dt = self.date_obj
            return dt.strftime("%b %d, %Y")
        except (ValueError, AttributeError):
            return self.date

    def __eq__(self, other):
        if not isinstance(other, SessionInfo):
            return NotImplemented
        return self.session_id == other.session_id

    def __hash__(self):
        return hash(self.session_id)


def discover_sessions(
    sessions_dir: str = "output",
    graphs_dir: str = "graphs/sessions",
) -> list[SessionInfo]:
    """Discover available sessions from output and graphs directories.
    
    Args:
        sessions_dir: Directory containing session JSON files
        graphs_dir: Directory containing session GraphML files
        
    Returns:
        List of SessionInfo objects sorted by date
    """
    sessions = []
    
    # Check output directory for JSON files
    output_path = Path(sessions_dir)
    if output_path.exists():
        for json_file in output_path.glob("*_session_*.json"):
            # Parse session ID and date from filename
            # Expected format: {session_id}_metrics.json or {date}_session_{id}.json
            session_id = json_file.stem.replace("_metrics", "")
            
            # Try to extract date from session_id
            parts = session_id.split("_")
            if len(parts) >= 3 and parts[1] == "session":
                date = parts[2].replace("_", "-")  # Convert to ISO format
            else:
                # Fallback: use file modification time
                date = datetime.fromtimestamp(json_file.stat().st_mtime).strftime("%Y-%m-%d")
            
            sessions.append(SessionInfo(
                session_id=session_id,
                date=date,
                has_data=True,
                file_path=str(json_file),
            ))
    
    # Check graphs/sessions directory for GraphML files
    graphs_path = Path(graphs_dir)
    if graphs_path.exists():
        for graphml_file in graphs_path.glob("*.graphml"):
            session_id = graphml_file.stem
            
            # Skip if already discovered from JSON
            if any(s.session_id == session_id for s in sessions):
                continue
            
            # Extract date from session_id
            parts = session_id.split("_")
            if len(parts) >= 2:
                date = parts[1] if parts[1].count("-") == 2 else datetime.now().strftime("%Y-%m-%d")
            else:
                date = datetime.fromtimestamp(graphml_file.stat().st_mtime).strftime("%Y-%m-%d")
            
            sessions.append(SessionInfo(
                session_id=session_id,
                date=date,
                has_data=True,
                file_path=str(graphml_file),
            ))
    
    # Sort by date (most recent first)
    sessions.sort(key=lambda s: s.date, reverse=True)
    
    return sessions


def render_timeline(
    sessions: list[SessionInfo],
    selected_session: SessionInfo | None = None,
    on_session_select: callable | None = None,
) -> SessionInfo | None:
    """Render horizontal session timeline with selection.
    
    Implements MP-12 acceptance criteria:
    1. Horizontal timeline bar showing all available sessions by date
    2. Clicking a session loads that session's graph
    3. Visual indicators for sessions with data vs. pending processing
    4. Navigation: previous/next session buttons
    
    Args:
        sessions: List of SessionInfo objects
        selected_session: Currently selected session
        on_session_select: Optional callback when session is selected
        
    Returns:
        Selected SessionInfo or None
    """
    if not sessions:
        st.info("📅 No sessions available. Generate sample data with `python examples/build_session_graph.py`")
        return None
    
    st.markdown("### 📅 Session Timeline")
    st.markdown(f"**{len(sessions)}** sessions available")
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 6, 1])
    
    current_index = 0
    if selected_session:
        try:
            current_index = sessions.index(selected_session)
        except ValueError:
            current_index = 0
    
    with col1:
        prev_disabled = current_index >= len(sessions) - 1
        if st.button("◀️ Prev", disabled=prev_disabled, key="timeline_prev"):
            new_index = current_index + 1
            selected_session = sessions[new_index]
            if on_session_select:
                on_session_select(selected_session)
    
    with col3:
        next_disabled = current_index <= 0
        if st.button("Next ▶️", disabled=next_disabled, key="timeline_next"):
            new_index = current_index - 1
            selected_session = sessions[new_index]
            if on_session_select:
                on_session_select(selected_session)
    
    # Timeline visualization
    st.markdown("---")
    
    # Display sessions in a grid (most recent first)
    cols_per_row = 4
    for i in range(0, len(sessions), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for col_idx, session in enumerate(sessions[i:i + cols_per_row]):
            with cols[col_idx]:
                # Visual indicator
                indicator = "✅" if session.has_data else "⏳"
                status = "Data Available" if session.has_data else "Pending"
                
                # Highlight selected session
                is_selected = selected_session and session.session_id == selected_session.session_id
                button_type = "primary" if is_selected else "secondary"
                
                # Session button
                button_label = f"{indicator} {session.display_date}"
                if st.button(
                    button_label,
                    key=f"session_{session.session_id}",
                    help=f"{session.session_id}\nStatus: {status}",
                    type=button_type,
                    disabled=not session.has_data,
                ):
                    selected_session = session
                    if on_session_select:
                        on_session_select(session)
    
    return selected_session


def render_timeline_compact(
    sessions: list[SessionInfo],
    max_display: int = 10,
) -> SessionInfo | None:
    """Render a compact session selector dropdown.
    
    Args:
        sessions: List of SessionInfo objects
        max_display: Maximum number of sessions to show (default: 10)
        
    Returns:
        Selected SessionInfo or None
    """
    if not sessions:
        st.info("No sessions available.")
        return None
    
    # Filter to sessions with data
    available_sessions = [s for s in sessions if s.has_data]
    
    if not available_sessions:
        st.warning("No session data available.")
        return None
    
    # Create display options
    display_sessions = available_sessions[:max_display]
    options = [f"{s.display_date} — {s.session_id}" for s in display_sessions]
    
    # Selectbox
    selected_idx = st.selectbox(
        "Select Session",
        range(len(options)),
        format_func=lambda i: options[i],
        key="timeline_compact_select",
    )
    
    return display_sessions[selected_idx] if selected_idx is not None else None


def get_session_navigation(
    sessions: list[SessionInfo],
    current_session: SessionInfo,
) -> tuple[SessionInfo | None, SessionInfo | None]:
    """Get previous and next sessions for navigation.
    
    Args:
        sessions: List of SessionInfo objects (sorted by date, most recent first)
        current_session: Currently selected session
        
    Returns:
        Tuple of (previous_session, next_session), either can be None
    """
    try:
        current_index = sessions.index(current_session)
    except ValueError:
        return None, None
    
    # In our sorted order (most recent first):
    # - Previous = older session (higher index)
    # - Next = newer session (lower index)
    previous_session = sessions[current_index + 1] if current_index + 1 < len(sessions) else None
    next_session = sessions[current_index - 1] if current_index > 0 else None
    
    return previous_session, next_session


def load_session_data(session: SessionInfo) -> dict | None:
    """Load session data from file.
    
    Args:
        session: SessionInfo with file_path
        
    Returns:
        Session data dict or None if loading fails
    """
    if not session.has_data or not session.file_path:
        return None
    
    try:
        import json
        from pathlib import Path
        
        file_path = Path(session.file_path)
        
        if file_path.suffix == ".json":
            with open(file_path, "r") as f:
                return json.load(f)
        else:
            # For GraphML files, would need to parse with NetworkX
            return None
    
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
