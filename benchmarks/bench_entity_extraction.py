"""Benchmark for NF-2: Entity extraction processing time.

Target: ≤30 seconds per hour of transcribed text

This script measures the performance of the entity extraction pipeline
on synthetic or real transcript data to validate NF-2 compliance.
"""

import sys
import time
from pathlib import Path

# Import directly to avoid heavy dependencies from brain/__init__.py
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Direct import to avoid loading pipeline module with heavy deps
import importlib.util
spec = importlib.util.spec_from_file_location(
    "entity_extractor",
    Path(__file__).parent.parent / "src" / "graphhansard" / "brain" / "entity_extractor.py"
)
entity_extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entity_extractor_module)
EntityExtractor = entity_extractor_module.EntityExtractor

from graphhansard.golden_record.resolver import AliasResolver


def generate_sample_transcript(duration_hours: float = 1.0) -> list[dict]:
    """Generate a synthetic transcript for benchmarking.
    
    Approximate speech rate: 150 words/minute or 9000 words/hour.
    Each segment is ~30 seconds with ~75 words.
    
    Args:
        duration_hours: Duration of transcript to simulate
        
    Returns:
        List of transcript segments with speaker, text, timestamps
    """
    words_per_hour = 9000
    total_words = int(words_per_hour * duration_hours)
    words_per_segment = 75
    num_segments = total_words // words_per_segment
    
    # Sample parliamentary text patterns
    sample_texts = [
        "Madam Speaker, I rise to address the Member for Cat Island on this important matter. "
        "The Minister of Finance has made it clear that we must proceed with caution. "
        "I commend the Prime Minister for his leadership on this issue. "
        "The Honourable Member opposite should know better than to make such claims. "
        "Let me be clear about our position on this legislation.",
        
        "Thank you, Madam Speaker. I want to respond to the Member for Englerston. "
        "The Minister of Education has done an excellent job with this reform. "
        "We cannot ignore what the Member for Marathon said earlier. "
        "The Leader of the Opposition continues to mislead the public. "
        "I ask the Deputy Prime Minister to clarify the government's position.",
        
        "Madam Speaker, with your permission. The Minister of Health outlined this clearly. "
        "I agree with the Member for Golden Isles on this point. "
        "The Attorney General has provided sound legal advice. "
        "The Member for Fort Charlotte raises a valid concern. "
        "I thank the Prime Minister for addressing this matter urgently.",
    ]
    
    segments = []
    for i in range(num_segments):
        segment = {
            "speaker": f"SPEAKER_{i % 5 + 1}",
            "text": sample_texts[i % len(sample_texts)],
            "start": i * 30.0,
            "end": (i + 1) * 30.0,
            "segment_index": i,
        }
        segments.append(segment)
    
    return segments


def benchmark_entity_extraction(duration_hours: float = 1.0) -> dict:
    """Benchmark entity extraction performance.
    
    Args:
        duration_hours: Hours of transcript to process
        
    Returns:
        Dictionary with benchmark results
    """
    print(f"\n{'='*60}")
    print(f"NF-2: Entity Extraction Performance Benchmark")
    print(f"{'='*60}")
    print(f"Duration: {duration_hours} hour(s) of transcript")
    print(f"Target: ≤30 seconds processing time per hour")
    print()
    
    # Generate sample transcript
    print("Generating sample transcript...")
    transcript = generate_sample_transcript(duration_hours)
    print(f"Generated {len(transcript)} segments")
    
    # Initialize extractor
    print("Initializing entity extractor...")
    golden_record_path = Path(__file__).parent.parent / "golden_record" / "mps.json"
    resolver = AliasResolver(str(golden_record_path))
    extractor = EntityExtractor(resolver=resolver)
    
    # Run benchmark
    print("\nRunning extraction benchmark...")
    start_time = time.perf_counter()
    
    session_id = "benchmark_session"
    mentions = []
    
    for segment in transcript:
        segment_mentions = extractor.extract_mentions_from_segment(
            session_id=session_id,
            speaker_id="mp_unknown",  # In real pipeline, would be resolved
            text=segment["text"],
            timestamp_start=segment["start"],
            timestamp_end=segment["end"],
            segment_index=segment["segment_index"],
        )
        mentions.extend(segment_mentions)
    
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    
    # Calculate metrics
    processing_time_per_hour = elapsed / duration_hours
    throughput = (duration_hours / elapsed) if elapsed > 0 else float('inf')
    
    # Results
    results = {
        "duration_hours": duration_hours,
        "total_segments": len(transcript),
        "total_mentions_extracted": len(mentions),
        "elapsed_seconds": elapsed,
        "processing_time_per_hour": processing_time_per_hour,
        "throughput_hours_per_second": throughput,
        "target_seconds_per_hour": 30.0,
        "passes": processing_time_per_hour <= 30.0,
    }
    
    # Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Total segments processed: {results['total_segments']}")
    print(f"Total mentions extracted: {results['total_mentions_extracted']}")
    print(f"Elapsed time: {elapsed:.2f} seconds")
    print(f"Processing time per hour: {processing_time_per_hour:.2f} seconds")
    print(f"Throughput: {throughput:.2f} hours/second")
    print()
    print(f"Target: ≤30 seconds per hour")
    print(f"Status: {'✅ PASS' if results['passes'] else '❌ FAIL'}")
    print("="*60)
    
    return results


if __name__ == "__main__":
    # Benchmark 1 hour of transcript
    results = benchmark_entity_extraction(duration_hours=1.0)
    
    # Optional: Test with longer transcript
    # results = benchmark_entity_extraction(duration_hours=3.0)
