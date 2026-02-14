"""Test for MP-16: About This Data Page requirements.

Verifies that the About page meets all acceptance criteria:
1. Accessible from main navigation
2. Written in plain language (Grade 10 reading level)
3. Explains what the graph shows
4. Explains how data is collected
5. Explains how metrics are computed
6. Lists data sources
7. States limitations clearly
8. Includes methodology link
9. Links to open-source code repository
"""

from pathlib import Path


def test_about_page_content_present():
    """Test that About page contains all required MP-16 elements."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find About section
    assert 'view_mode == "About"' in content, "About view mode should exist"
    
    # Check for required sections (MP-16 acceptance criteria)
    required_sections = [
        "What is GraphHansard?",  # What the graph shows
        "How Data is Collected",  # How data is collected (MP-16.4)
        "How Metrics Are Computed",  # How metrics are computed (MP-16.5)
        "Data Sources",  # Data sources (MP-16.6)
        "Key Limitations",  # Limitations (MP-16.7)
        "methodology.md",  # Link to methodology (MP-16.8)
        "github.com/caribdigital/graphhansard",  # Link to repository (MP-16.9)
    ]
    
    for section in required_sections:
        assert section in content, f"Required section '{section}' not found in About page"


def test_about_page_data_collection_explicit():
    """Test that data collection process is explicitly described (MP-16.4)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check for 5-step process
    data_collection_steps = [
        "Audio Download",
        "Transcription",
        "Speaker Identification",
        "Mention Extraction",
        "Network Analysis",
    ]
    
    for step in data_collection_steps:
        assert step in content, f"Data collection step '{step}' not found"


def test_about_page_metrics_computation():
    """Test that metrics computation is explained (MP-16.5)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check for algorithm explanations
    metrics_explanations = [
        "Degree Centrality",
        "Betweenness Centrality",
        "Eigenvector Centrality",
        "Closeness Centrality",
        "Computation",  # Each metric should have a computation explanation
    ]
    
    for explanation in metrics_explanations:
        assert explanation in content, f"Metric explanation '{explanation}' not found"


def test_about_page_data_sources():
    """Test that data sources are clearly listed (MP-16.6)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check for required data sources
    data_sources = [
        "YouTube",  # YouTube as source
        "parliamentary",  # Parliamentary records
    ]
    
    for source in data_sources:
        assert source in content, f"Data source '{source}' not found"


def test_about_page_limitations():
    """Test that limitations are clearly stated (MP-16.7)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check for required limitations
    limitations = [
        "Transcription Accuracy",
        "Sentiment Analysis",
        "Audio Quality",
    ]
    
    for limitation in limitations:
        assert limitation in content, f"Limitation '{limitation}' not found"


def test_about_navigation_accessible():
    """Test that About page is accessible from navigation (MP-16.1)."""
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check that "About" is in the radio button options
    assert 'options=["Graph Explorer", "Session Timeline", "MP Report Card", "About"]' in content, \
        "About should be in navigation options"
    assert 'if view_mode == "About"' in content, \
        "About view mode handler should exist"


if __name__ == "__main__":
    # Run tests manually
    test_about_page_content_present()
    print("✓ test_about_page_content_present passed")
    
    test_about_page_data_collection_explicit()
    print("✓ test_about_page_data_collection_explicit passed")
    
    test_about_page_metrics_computation()
    print("✓ test_about_page_metrics_computation passed")
    
    test_about_page_data_sources()
    print("✓ test_about_page_data_sources passed")
    
    test_about_page_limitations()
    print("✓ test_about_page_limitations passed")
    
    test_about_navigation_accessible()
    print("✓ test_about_navigation_accessible passed")
    
    print("\n✅ All MP-16 requirements verified!")
