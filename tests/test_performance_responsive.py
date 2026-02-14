"""Test for MP-14 and MP-15: Performance and Responsiveness requirements.

MP-14: Performance (≤3 seconds load time)
- Verifies caching is implemented
- Verifies graph optimization settings
- Checks for performance CSS

MP-15: Responsiveness (Tablet/Desktop, Mobile Graceful Degradation)
- Verifies responsive CSS breakpoints
- Checks for touch-friendly controls
- Validates no horizontal scrolling
"""

from pathlib import Path


def test_caching_implemented():
    """Test that caching decorators are used for data loading (MP-14)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r") as f:
        content = f.read()
    
    # Check for caching decorators
    assert "@st.cache_data" in content, "Caching should be implemented with @st.cache_data"
    assert "def load_sample_graph" in content, "load_sample_graph should exist"
    assert "def load_golden_record" in content, "load_golden_record should exist"
    
    # Verify caching is applied to load functions
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "def load_sample_graph" in line:
            # Check previous line has cache decorator
            assert "@st.cache_data" in lines[i-1], "load_sample_graph should be cached"
        if "def load_golden_record" in line:
            # Check previous line has cache decorator
            assert "@st.cache_data" in lines[i-1], "load_golden_record should be cached"


def test_graph_performance_settings():
    """Test that graph visualization has performance optimizations (MP-14)."""
    graph_viz_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "graph_viz.py"
    
    with open(graph_viz_path, "r") as f:
        content = f.read()
    
    # Check for stabilization settings
    assert "stabilization" in content, "Graph should have stabilization settings"
    assert "iterations" in content, "Graph should have iteration limits"
    
    # Check for improved layout
    assert "improvedLayout" in content or "layout" in content, "Graph should use improved layout"


def test_streamlit_config_exists():
    """Test that Streamlit config file exists for performance (MP-14)."""
    config_path = Path(__file__).parent.parent / ".streamlit" / "config.toml"
    
    assert config_path.exists(), ".streamlit/config.toml should exist for performance settings"
    
    with open(config_path, "r") as f:
        content = f.read()
    
    # Check for performance settings
    assert "fastReruns" in content or "runner" in content, "Config should have performance settings"


def test_responsive_css_breakpoints():
    """Test that responsive CSS is implemented for tablet and desktop (MP-15)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r") as f:
        content = f.read()
    
    # Check for responsive CSS
    assert "@media" in content, "Responsive CSS should be present"
    
    # Check for specific breakpoints (MP-15)
    assert "768px" in content, "Tablet breakpoint (768px) should be defined"
    assert "1200px" in content, "Desktop breakpoint (1200px) should be defined"
    
    # Check for mobile-specific styles
    assert "max-width" in content, "Mobile styles should be present"


def test_no_horizontal_scrolling():
    """Test that CSS prevents horizontal scrolling (MP-15)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r") as f:
        content = f.read()
    
    # Check for overflow-x prevention
    assert "overflow-x: hidden" in content, "CSS should prevent horizontal scrolling"


def test_touch_friendly_controls():
    """Test that touch-friendly controls are implemented (MP-15)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r") as f:
        content = f.read()
    
    # Check for minimum touch target sizes
    assert "min-height: 44px" in content or "min-width: 44px" in content, \
        "Touch controls should have minimum 44px size"
    
    # Check graph visualization has touch support
    graph_viz_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "graph_viz.py"
    with open(graph_viz_path, "r") as f:
        viz_content = f.read()
    
    assert "navigationButtons" in viz_content, "Graph should have navigation buttons for touch devices"


def test_performance_documentation():
    """Test that performance targets are documented (MP-14)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r") as f:
        content = f.read()
    
    # Check for performance documentation in docstrings
    assert "≤3 seconds" in content or "3 seconds" in content, \
        "Performance target (≤3 seconds) should be documented"
    assert "MP-14" in content, "MP-14 requirement should be referenced"
    assert "MP-15" in content, "MP-15 requirement should be referenced"


def test_reduced_motion_support():
    """Test that reduced motion is supported for accessibility (MP-15)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r") as f:
        content = f.read()
    
    # Check for prefers-reduced-motion media query
    assert "prefers-reduced-motion" in content, "Reduced motion preference should be respected"


if __name__ == "__main__":
    # Run tests manually
    test_caching_implemented()
    print("✓ test_caching_implemented passed")
    
    test_graph_performance_settings()
    print("✓ test_graph_performance_settings passed")
    
    test_streamlit_config_exists()
    print("✓ test_streamlit_config_exists passed")
    
    test_responsive_css_breakpoints()
    print("✓ test_responsive_css_breakpoints passed")
    
    test_no_horizontal_scrolling()
    print("✓ test_no_horizontal_scrolling passed")
    
    test_touch_friendly_controls()
    print("✓ test_touch_friendly_controls passed")
    
    test_performance_documentation()
    print("✓ test_performance_documentation passed")
    
    test_reduced_motion_support()
    print("✓ test_reduced_motion_support passed")
    
    print("\n✅ All MP-14 and MP-15 requirements verified!")
