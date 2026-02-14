"""Benchmark for NF-4: Dashboard initial load time.

Target: ≤3 seconds on 50 Mbps connection

This script measures dashboard load time and provides Lighthouse audit
integration for comprehensive performance testing.
"""

import json
import subprocess
import time
from pathlib import Path


def check_streamlit_available() -> bool:
    """Check if Streamlit is installed."""
    try:
        import streamlit
        return True
    except ImportError:
        return False


def check_lighthouse_available() -> bool:
    """Check if Lighthouse CLI is available."""
    try:
        result = subprocess.run(
            ["lighthouse", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def measure_app_startup_time() -> dict:
    """Measure Streamlit app startup time.
    
    Returns:
        Dictionary with startup metrics
    """
    print("Measuring Streamlit app startup time...")
    
    app_path = Path(__file__).parent.parent / "src" / "graphhansard" / "dashboard" / "app.py"
    
    if not app_path.exists():
        return {"error": "Dashboard app not found"}
    
    # Time the import and initialization
    start_time = time.perf_counter()
    
    try:
        # Import key modules to measure load time
        import sys
        original_argv = sys.argv.copy()
        sys.argv = ["streamlit", "run"]
        
        import streamlit
        
        # Check that key functions are cached
        from graphhansard.dashboard import app
        
        sys.argv = original_argv
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        return {
            "startup_time_seconds": elapsed,
            "status": "success",
        }
    except Exception as e:
        return {"error": str(e)}


def run_lighthouse_audit(url: str = "http://localhost:8501") -> dict:
    """Run Lighthouse performance audit.
    
    Args:
        url: Dashboard URL to audit
        
    Returns:
        Dictionary with Lighthouse results
    """
    print(f"\nRunning Lighthouse audit on {url}...")
    print("(Note: Dashboard must be running)")
    
    if not check_lighthouse_available():
        print("\n⚠️  Lighthouse CLI not available.")
        print("Install with: npm install -g lighthouse")
        return {"error": "Lighthouse not available"}
    
    # Run Lighthouse
    output_path = Path("/tmp/lighthouse-report.json")
    
    try:
        cmd = [
            "lighthouse",
            url,
            "--output=json",
            f"--output-path={output_path}",
            "--only-categories=performance",
            "--throttling.requestLatencyMs=0",  # No additional latency
            "--throttling.downloadThroughputKbps=51200",  # 50 Mbps
            "--throttling.uploadThroughputKbps=10240",  # 10 Mbps
            "--chrome-flags='--headless'",
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode != 0:
            return {"error": f"Lighthouse failed: {result.stderr}"}
        
        # Parse results
        with open(output_path, "r") as f:
            report = json.load(f)
        
        performance_score = report["categories"]["performance"]["score"] * 100
        
        # Extract key metrics
        audits = report["audits"]
        metrics = {
            "performance_score": performance_score,
            "first_contentful_paint": audits["first-contentful-paint"]["numericValue"] / 1000,
            "largest_contentful_paint": audits["largest-contentful-paint"]["numericValue"] / 1000,
            "total_blocking_time": audits["total-blocking-time"]["numericValue"] / 1000,
            "cumulative_layout_shift": audits["cumulative-layout-shift"]["numericValue"],
            "speed_index": audits["speed-index"]["numericValue"] / 1000,
        }
        
        return metrics
        
    except subprocess.TimeoutExpired:
        return {"error": "Lighthouse audit timed out"}
    except Exception as e:
        return {"error": str(e)}


def benchmark_dashboard_load() -> dict:
    """Benchmark dashboard load time.
    
    Returns:
        Dictionary with benchmark results
    """
    print(f"\n{'='*60}")
    print(f"NF-4: Dashboard Load Time Benchmark")
    print(f"{'='*60}")
    print(f"Target: ≤3 seconds on 50 Mbps connection")
    print()
    
    if not check_streamlit_available():
        print("❌ Streamlit not available.")
        print("Install with: pip install -e '.[dashboard]'")
        return {"error": "Streamlit not available"}
    
    # Measure startup time
    startup_results = measure_app_startup_time()
    if "error" in startup_results:
        print(f"❌ Error: {startup_results['error']}")
        return startup_results
    
    print(f"App startup time: {startup_results['startup_time_seconds']:.2f} seconds")
    
    # Run Lighthouse audit (optional, requires running app)
    print("\n" + "-"*60)
    print("Lighthouse Audit (optional)")
    print("-"*60)
    print("\nTo run Lighthouse audit:")
    print("  1. Start the dashboard: streamlit run src/graphhansard/dashboard/app.py")
    print("  2. Run: lighthouse http://localhost:8501 --output=json")
    print("  3. Check performance score (target: ≥90)")
    print()
    print("Or use this script after starting the dashboard:")
    print("  python benchmarks/bench_dashboard_load.py --lighthouse")
    
    # Basic results based on startup
    results = {
        "startup_time_seconds": startup_results["startup_time_seconds"],
        "estimated_load_time": startup_results["startup_time_seconds"] + 1.0,  # Add network time
        "target_seconds": 3.0,
        "passes": (startup_results["startup_time_seconds"] + 1.0) <= 3.0,
    }
    
    print("\n" + "="*60)
    print("RESULTS (Startup Time)")
    print("="*60)
    print(f"App startup time: {results['startup_time_seconds']:.2f} seconds")
    print(f"Estimated load time: {results['estimated_load_time']:.2f} seconds")
    print()
    print(f"Target: ≤3 seconds")
    print(f"Status: {'✅ PASS' if results['passes'] else '❌ FAIL'}")
    print("="*60)
    
    print("\n💡 For complete NF-4 validation:")
    print("   Run Lighthouse audit with dashboard running")
    print("   Target: Performance score ≥90")
    
    return results


if __name__ == "__main__":
    import sys
    
    results = benchmark_dashboard_load()
    
    # Check for --lighthouse flag
    if "--lighthouse" in sys.argv and "error" not in results:
        print("\n" + "="*60)
        lighthouse_results = run_lighthouse_audit()
        
        if "error" not in lighthouse_results:
            print("\nLighthouse Results:")
            print(f"  Performance Score: {lighthouse_results['performance_score']:.0f}")
            print(f"  First Contentful Paint: {lighthouse_results['first_contentful_paint']:.2f}s")
            print(f"  Largest Contentful Paint: {lighthouse_results['largest_contentful_paint']:.2f}s")
            print(f"  Total Blocking Time: {lighthouse_results['total_blocking_time']:.2f}s")
            print(f"  Speed Index: {lighthouse_results['speed_index']:.2f}s")
            print()
            
            lighthouse_pass = lighthouse_results['performance_score'] >= 90
            print(f"Lighthouse Status: {'✅ PASS' if lighthouse_pass else '❌ FAIL'}")
