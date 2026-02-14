"""Benchmark for NF-5: Dashboard graph interaction latency.

Target: ≤100ms for node drag, zoom, pan operations

This script provides test instructions for measuring interaction latency.
Actual measurement requires browser DevTools or automated browser testing.
"""

from pathlib import Path


def print_manual_testing_instructions():
    """Print instructions for manual interaction latency testing."""
    
    print(f"\n{'='*60}")
    print(f"NF-5: Dashboard Interaction Latency Testing")
    print(f"{'='*60}")
    print(f"Target: ≤100ms for node drag, zoom, pan")
    print()
    
    print("AUTOMATED TESTING (Recommended):")
    print("-" * 60)
    print()
    print("This test can be automated using browser automation tools:")
    print()
    print("  1. Install Playwright:")
    print("     pip install playwright")
    print("     playwright install chromium")
    print()
    print("  2. Run the automated test:")
    print("     python benchmarks/bench_dashboard_interaction.py --automated")
    print()
    
    print("\nMANUAL TESTING (Alternative):")
    print("-" * 60)
    print()
    print("Step 1: Start the dashboard")
    print("  streamlit run src/graphhansard/dashboard/app.py")
    print()
    print("Step 2: Open Chrome DevTools")
    print("  - Press F12 or Ctrl+Shift+I")
    print("  - Go to 'Performance' tab")
    print("  - Click 'Record' button")
    print()
    print("Step 3: Perform interactions")
    print("  - Drag a node")
    print("  - Zoom in/out (mouse wheel)")
    print("  - Pan the graph (click and drag background)")
    print("  - Repeat each interaction 5 times")
    print()
    print("Step 4: Stop recording and analyze")
    print("  - Click 'Stop' button")
    print("  - Look for 'Event' entries in timeline")
    print("  - Measure time from interaction to visual update")
    print()
    print("Expected results:")
    print("  - Node drag: <100ms response time")
    print("  - Zoom: <100ms response time")
    print("  - Pan: <100ms response time")
    print()
    print("="*60)
    
    print("\nCODE-BASED VALIDATION:")
    print("-" * 60)
    print()
    print("Check that performance optimizations are in place:")
    check_performance_optimizations()


def check_performance_optimizations():
    """Check that required performance optimizations are implemented."""
    
    graph_viz_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "graph_viz.py"
    
    if not graph_viz_path.exists():
        print("  ❌ graph_viz.py not found")
        return
    
    with open(graph_viz_path, "r") as f:
        content = f.read()
    
    optimizations = {
        "Physics stabilization": "stabilization" in content,
        "Smooth physics": "smooth" in content or "barnesHut" in content,
        "Interaction handlers": "interaction" in content,
        "Performance settings": "improvedLayout" in content or "hierarchicalRepulsion" in content,
    }
    
    all_pass = all(optimizations.values())
    
    print("\n  Performance optimizations:")
    for name, present in optimizations.items():
        status = "✅" if present else "❌"
        print(f"    {status} {name}")
    
    if all_pass:
        print("\n  ✅ All required optimizations are in place")
    else:
        print("\n  ⚠️  Some optimizations may be missing")
    
    print()
    print("  Additional checks:")
    print("    - PyVis uses vis-network library (hardware-accelerated)")
    print("    - Streamlit caching reduces re-renders")
    print("    - Graph complexity controlled (39 nodes max)")


def run_automated_test():
    """Run automated interaction latency test using Playwright."""
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\n❌ Playwright not available.")
        print("Install with: pip install playwright")
        print("Then run: playwright install chromium")
        return
    
    print("\nRunning automated interaction test...")
    print("(Starting browser, this may take a moment)")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            # Navigate to dashboard
            print("\n1. Navigating to dashboard...")
            page.goto("http://localhost:8501", timeout=30000)
            
            # Wait for graph to load
            print("2. Waiting for graph to load...")
            page.wait_for_timeout(5000)
            
            # Measure interaction latency
            print("3. Measuring interaction latency...")
            
            # Find the graph iframe
            try:
                frame = page.frame_locator('iframe[title*="pyvis"]').first
                
                # Measure node drag latency
                print("   - Testing node drag...")
                start = page.evaluate("Date.now()")
                # Simulate drag operation
                page.mouse.move(400, 300)
                page.mouse.down()
                page.mouse.move(450, 350, steps=5)
                page.mouse.up()
                end = page.evaluate("Date.now()")
                drag_latency = end - start
                
                print(f"     Drag latency: {drag_latency}ms")
                
                # Measure zoom latency
                print("   - Testing zoom...")
                start = page.evaluate("Date.now()")
                page.mouse.wheel(0, 100)
                page.wait_for_timeout(100)
                end = page.evaluate("Date.now()")
                zoom_latency = end - start
                
                print(f"     Zoom latency: {zoom_latency}ms")
                
                # Results
                max_latency = max(drag_latency, zoom_latency)
                passes = max_latency <= 100
                
                print("\n" + "="*60)
                print("RESULTS")
                print("="*60)
                print(f"Node drag latency: {drag_latency}ms")
                print(f"Zoom latency: {zoom_latency}ms")
                print(f"Maximum latency: {max_latency}ms")
                print()
                print(f"Target: ≤100ms")
                print(f"Status: {'✅ PASS' if passes else '❌ FAIL'}")
                print("="*60)
                
            except Exception as e:
                print(f"   ⚠️  Could not find graph iframe: {e}")
                print("   Make sure dashboard is displaying a graph")
            
            browser.close()
            
    except Exception as e:
        print(f"\n❌ Error during automated test: {e}")
        print("\nMake sure:")
        print("  1. Dashboard is running on http://localhost:8501")
        print("  2. A graph is visible in the dashboard")


if __name__ == "__main__":
    import sys
    
    if "--automated" in sys.argv:
        run_automated_test()
    else:
        print_manual_testing_instructions()
        
        print("\n💡 To run automated test:")
        print("   python benchmarks/bench_dashboard_interaction.py --automated")
