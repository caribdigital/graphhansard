"""Master benchmark runner for all performance and reliability tests.

Runs all available benchmarks and generates a summary report.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path


def run_benchmark(name: str, module_path: str, *args) -> dict:
    """Run a single benchmark and return results.
    
    Args:
        name: Human-readable benchmark name
        module_path: Path to benchmark module
        *args: Additional arguments to pass
        
    Returns:
        Dictionary with benchmark results
    """
    print(f"\n{'='*70}")
    print(f"Running: {name}")
    print(f"{'='*70}")
    
    start_time = time.time()
    
    try:
        # Import and run the benchmark
        spec = __import__('importlib.util').util.spec_from_file_location(
            "benchmark", module_path
        )
        module = __import__('importlib.util').util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Run the benchmark function
        if hasattr(module, 'benchmark_entity_extraction'):
            results = module.benchmark_entity_extraction()
        elif hasattr(module, 'benchmark_graph_computation'):
            results = module.benchmark_graph_computation()
        elif hasattr(module, 'benchmark_dashboard_load'):
            results = module.benchmark_dashboard_load()
        elif hasattr(module, 'test_miner_idempotency'):
            results = {"passes": module.test_miner_idempotency()}
        elif hasattr(module, 'test_entity_extraction_error_handling'):
            results = {"passes": module.test_entity_extraction_error_handling()}
        else:
            results = {"error": "No benchmark function found"}
        
        elapsed = time.time() - start_time
        results["elapsed_time"] = elapsed
        results["benchmark_name"] = name
        return results
        
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "benchmark_name": name,
            "error": str(e),
            "elapsed_time": elapsed,
            "passes": False,
        }


def run_all_benchmarks(include_gpu: bool = False, audio_path: str = None) -> dict:
    """Run all performance and reliability benchmarks.
    
    Args:
        include_gpu: Whether to run GPU-dependent benchmarks
        audio_path: Path to audio file for transcription benchmark
        
    Returns:
        Dictionary with all benchmark results
    """
    print("="*70)
    print("GraphHansard Performance & Reliability Benchmark Suite")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")
    print()
    
    base_dir = Path(__file__).parent
    results = {
        "timestamp": datetime.now().isoformat(),
        "benchmarks": {},
        "summary": {},
    }
    
    # NF-2: Entity Extraction
    print("\n🔍 NF-2: Entity Extraction Processing Time")
    nf2_results = run_benchmark(
        "Entity Extraction",
        base_dir / "bench_entity_extraction.py"
    )
    results["benchmarks"]["NF-2"] = nf2_results
    
    # NF-3: Graph Computation
    print("\n📊 NF-3: Graph Computation Time")
    nf3_results = run_benchmark(
        "Graph Computation",
        base_dir / "bench_graph_computation.py"
    )
    results["benchmarks"]["NF-3"] = nf3_results
    
    # NF-4: Dashboard Load Time
    print("\n🌐 NF-4: Dashboard Load Time")
    try:
        nf4_results = run_benchmark(
            "Dashboard Load Time",
            base_dir / "bench_dashboard_load.py"
        )
        results["benchmarks"]["NF-4"] = nf4_results
    except Exception as e:
        print(f"⚠️  Skipping NF-4: {e}")
        results["benchmarks"]["NF-4"] = {"error": str(e), "passes": False}
    
    # NF-1: Transcription (optional, requires GPU)
    if include_gpu and audio_path:
        print("\n🎤 NF-1: Audio Transcription Throughput")
        print(f"Audio file: {audio_path}")
        try:
            # Note: This requires audio file and GPU
            print("⚠️  NF-1 requires GPU and audio file. Skipping by default.")
            print("   Run with: python benchmarks/run_all.py --include-gpu path/to/audio.wav")
            results["benchmarks"]["NF-1"] = {"skipped": True}
        except Exception as e:
            print(f"⚠️  Skipping NF-1: {e}")
            results["benchmarks"]["NF-1"] = {"error": str(e), "passes": False}
    else:
        print("\n⚠️  Skipping NF-1 (GPU benchmark). Use --include-gpu to run.")
        results["benchmarks"]["NF-1"] = {"skipped": True}
    
    # NF-5: Dashboard Interaction (requires manual testing or Playwright)
    print("\n🖱️  NF-5: Dashboard Interaction Latency")
    print("⚠️  NF-5 requires manual testing or Playwright automation.")
    print("   Run: python benchmarks/bench_dashboard_interaction.py --automated")
    results["benchmarks"]["NF-5"] = {"manual_test_required": True}
    
    # NF-6: Miner Idempotency
    print("\n🔄 NF-6: Miner Pipeline Idempotency")
    nf6_results = run_benchmark(
        "Miner Idempotency",
        base_dir.parent / "tests" / "test_idempotency.py"
    )
    results["benchmarks"]["NF-6"] = nf6_results
    
    # NF-7: Error Resilience
    print("\n🛡️  NF-7: Pipeline Error Handling")
    nf7_results = run_benchmark(
        "Error Resilience",
        base_dir.parent / "tests" / "test_error_resilience.py"
    )
    results["benchmarks"]["NF-7"] = nf7_results
    
    # NF-8: Uptime Monitoring
    print("\n📈 NF-8: Dashboard Uptime Monitoring")
    print("⚠️  NF-8 requires uptime monitoring service setup.")
    print("   See: docs/uptime_monitoring.md")
    results["benchmarks"]["NF-8"] = {"documentation_provided": True}
    
    # Generate summary
    passed = sum(
        1 for r in results["benchmarks"].values()
        if r.get("passes", False)
    )
    failed = sum(
        1 for r in results["benchmarks"].values()
        if r.get("passes") == False and "error" in r
    )
    skipped = sum(
        1 for r in results["benchmarks"].values()
        if r.get("skipped", False) or r.get("manual_test_required", False) or r.get("documentation_provided", False)
    )
    
    results["summary"] = {
        "total": 8,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }
    
    return results


def print_summary(results: dict):
    """Print benchmark summary."""
    
    print("\n" + "="*70)
    print("BENCHMARK SUMMARY")
    print("="*70)
    
    for nf_id, result in results["benchmarks"].items():
        status = "❓"
        if result.get("passes"):
            status = "✅"
        elif result.get("error"):
            status = "❌"
        elif result.get("skipped") or result.get("manual_test_required") or result.get("documentation_provided"):
            status = "⏭️ "
        
        name = result.get("benchmark_name", nf_id)
        print(f"{status} {nf_id}: {name}")
        
        if "elapsed_time" in result:
            print(f"   Elapsed: {result['elapsed_time']:.2f}s")
        if "error" in result:
            print(f"   Error: {result['error']}")
    
    print()
    print(f"Total: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Skipped: {results['summary']['skipped']}")
    print("="*70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run all GraphHansard performance and reliability benchmarks"
    )
    parser.add_argument(
        "--include-gpu",
        action="store_true",
        help="Include GPU-dependent benchmarks (requires CUDA)",
    )
    parser.add_argument(
        "--audio-path",
        type=str,
        help="Path to audio file for transcription benchmark",
    )
    parser.add_argument(
        "--save-results",
        type=str,
        help="Save results to JSON file",
    )
    
    args = parser.parse_args()
    
    # Run benchmarks
    results = run_all_benchmarks(
        include_gpu=args.include_gpu,
        audio_path=args.audio_path,
    )
    
    # Print summary
    print_summary(results)
    
    # Save results if requested
    if args.save_results:
        output_path = Path(args.save_results)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_path}")
    
    # Exit with error code if any benchmarks failed
    if results["summary"]["failed"] > 0:
        sys.exit(1)
