"""Benchmark for NF-1: Audio transcription throughput.

Target: ≥6x real-time on a consumer GPU (RTX 3080 or equivalent)

This script measures the performance of the Whisper transcription pipeline.
Note: Requires GPU (CUDA) for meaningful results. CPU-only will be much slower.

Real-time factor (RTF) calculation:
    RTF = audio_duration / processing_time
    
Example: 1 hour of audio processed in 10 minutes = RTF of 6.0
"""

import time
from pathlib import Path

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️  Warning: PyTorch not available. This benchmark requires torch.")


def check_gpu_availability() -> dict:
    """Check GPU availability and specs.
    
    Returns:
        Dictionary with GPU information
    """
    gpu_info = {
        "available": False,
        "device_name": None,
        "cuda_version": None,
        "device_count": 0,
    }
    
    if not TORCH_AVAILABLE:
        return gpu_info
    
    if torch.cuda.is_available():
        gpu_info["available"] = True
        gpu_info["device_count"] = torch.cuda.device_count()
        gpu_info["device_name"] = torch.cuda.get_device_name(0)
        gpu_info["cuda_version"] = torch.version.cuda
    
    return gpu_info


def benchmark_transcription(audio_path: str) -> dict:
    """Benchmark transcription performance.
    
    Args:
        audio_path: Path to audio file to transcribe
        
    Returns:
        Dictionary with benchmark results
    """
    print(f"\n{'='*60}")
    print(f"NF-1: Audio Transcription Performance Benchmark")
    print(f"{'='*60}")
    print(f"Target: ≥6x real-time on RTX 3080 or equivalent")
    print()
    
    # Check GPU
    gpu_info = check_gpu_availability()
    print("GPU Status:")
    if gpu_info["available"]:
        print(f"  ✅ GPU Available: {gpu_info['device_name']}")
        print(f"  CUDA Version: {gpu_info['cuda_version']}")
    else:
        print("  ❌ No GPU available. Results will not be meaningful.")
        print("  This benchmark requires CUDA-capable GPU.")
        return {"error": "No GPU available"}
    
    # Check if audio file exists
    audio_file = Path(audio_path)
    if not audio_file.exists():
        print(f"\n❌ Error: Audio file not found: {audio_path}")
        print("\nTo run this benchmark:")
        print("  1. Place a test audio file in the specified path, OR")
        print("  2. Provide a path to an existing audio file")
        return {"error": "Audio file not found"}
    
    # Get audio duration
    try:
        import librosa
        audio_duration = librosa.get_duration(path=audio_path)
        print(f"\nAudio file: {audio_path}")
        print(f"Duration: {audio_duration:.1f} seconds ({audio_duration/60:.1f} minutes)")
    except ImportError:
        print("\n⚠️  librosa not available. Using estimated duration.")
        audio_duration = 600.0  # Assume 10 minutes
    except Exception as e:
        print(f"\n⚠️  Could not determine audio duration: {e}")
        audio_duration = 600.0
    
    # Initialize transcriber
    print("\nInitializing Whisper transcriber...")
    try:
        from graphhansard.brain.transcriber import Transcriber
        
        transcriber = Transcriber(
            model_name="base",  # Use base model for benchmarking
            device="cuda" if gpu_info["available"] else "cpu",
        )
    except Exception as e:
        print(f"\n❌ Error initializing transcriber: {e}")
        print("\nMake sure Whisper dependencies are installed:")
        print("  pip install -e '.[brain]'")
        return {"error": str(e)}
    
    # Run benchmark
    print("\nRunning transcription benchmark...")
    print("(This may take several minutes depending on audio length)\n")
    
    start_time = time.perf_counter()
    
    try:
        result = transcriber.transcribe(
            audio_path=audio_path,
            language="en",
            return_word_timestamps=False,  # Faster without word timestamps
        )
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        # Calculate metrics
        rtf = audio_duration / elapsed if elapsed > 0 else float('inf')
        
        results = {
            "audio_duration_seconds": audio_duration,
            "processing_time_seconds": elapsed,
            "real_time_factor": rtf,
            "target_rtf": 6.0,
            "passes": rtf >= 6.0,
            "gpu_name": gpu_info["device_name"],
            "segments_transcribed": len(result.get("segments", [])),
        }
        
        # Print results
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print(f"Audio duration: {audio_duration:.1f} seconds ({audio_duration/60:.1f} minutes)")
        print(f"Processing time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"Real-Time Factor (RTF): {rtf:.2f}x")
        print(f"Segments transcribed: {results['segments_transcribed']}")
        print()
        print(f"GPU: {gpu_info['device_name']}")
        print(f"Target: ≥6x real-time")
        print(f"Status: {'✅ PASS' if results['passes'] else '❌ FAIL'}")
        print("="*60)
        
        if rtf < 6.0:
            print("\n⚠️  Performance target not met. Consider:")
            print("  - Using a faster GPU (RTX 3080 or better)")
            print("  - Using faster-whisper instead of standard Whisper")
            print("  - Using smaller model (tiny, base) if acceptable")
            print("  - Enabling INT8 quantization")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error during transcription: {e}")
        return {"error": str(e)}


def print_usage():
    """Print usage instructions."""
    print("\nUsage:")
    print("  python benchmarks/bench_transcription.py [audio_path]")
    print("\nExample:")
    print("  python benchmarks/bench_transcription.py examples/sample_audio.wav")
    print("\nNote: This benchmark requires:")
    print("  - CUDA-capable GPU (RTX 3080 or equivalent)")
    print("  - PyTorch with CUDA support")
    print("  - faster-whisper or whisper installed")
    print("  - Test audio file (10+ minutes recommended)")


if __name__ == "__main__":
    import sys
    
    # Default test audio path (may not exist)
    default_audio = "examples/sample_session.wav"
    
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
    else:
        audio_path = default_audio
        print(f"No audio path provided. Using default: {audio_path}")
    
    results = benchmark_transcription(audio_path)
    
    if "error" in results:
        print_usage()
