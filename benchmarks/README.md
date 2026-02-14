# Performance & Reliability Benchmarks

This directory contains benchmark scripts and tests for validating GraphHansard's non-functional requirements (NF-1 through NF-8).

## Performance Benchmarks

### NF-1: Audio Transcription Throughput
**Target:** ≥6x real-time on RTX 3080 or equivalent

```bash
python benchmarks/bench_transcription.py path/to/audio.wav
```

**Requirements:**
- CUDA-capable GPU (RTX 3080 or equivalent)
- PyTorch with CUDA support
- faster-whisper or Whisper installed
- Test audio file (10+ minutes recommended)

**Expected Output:**
```
Real-Time Factor (RTF): 6.5x
Status: ✅ PASS
```

---

### NF-2: Entity Extraction Processing Time
**Target:** ≤30 seconds per hour of transcribed text

```bash
python benchmarks/bench_entity_extraction.py
```

**Requirements:**
- Core dependencies only (pydantic, rapidfuzz)
- Golden record (mps.json)

**Expected Output:**
```
Processing time per hour: 12.5 seconds
Status: ✅ PASS
```

---

### NF-3: Graph Computation Time
**Target:** ≤5 seconds for 39-node graph

```bash
python benchmarks/bench_graph_computation.py
```

**Requirements:**
- Core dependencies (networkx)
- Golden record (mps.json)

**Expected Output:**
```
Elapsed time: 1.2 seconds
Status: ✅ PASS
```

---

### NF-4: Dashboard Initial Load Time
**Target:** ≤3 seconds on 50 Mbps connection

```bash
# Basic startup benchmark
python benchmarks/bench_dashboard_load.py

# With Lighthouse audit (requires running dashboard)
streamlit run src/graphhansard/dashboard/app.py &
python benchmarks/bench_dashboard_load.py --lighthouse
```

**Requirements:**
- Streamlit installed
- For Lighthouse: Node.js and lighthouse CLI (`npm install -g lighthouse`)

**Expected Output:**
```
App startup time: 0.8 seconds
Estimated load time: 1.8 seconds
Status: ✅ PASS

Lighthouse Performance Score: 92
Status: ✅ PASS
```

---

### NF-5: Dashboard Interaction Latency
**Target:** ≤100ms for node drag, zoom, pan

```bash
# Manual testing instructions
python benchmarks/bench_dashboard_interaction.py

# Automated test (requires Playwright)
pip install playwright
playwright install chromium
streamlit run src/graphhansard/dashboard/app.py &
python benchmarks/bench_dashboard_interaction.py --automated
```

**Requirements:**
- For automated testing: Playwright (`pip install playwright`)
- Running dashboard instance

**Expected Output:**
```
Node drag latency: 45ms
Zoom latency: 32ms
Status: ✅ PASS
```

---

## Reliability Tests

### NF-6: Miner Pipeline Idempotency & Resumability
**Target:** Re-running does not duplicate data

```bash
python tests/test_idempotency.py
```

**Requirements:**
- Miner dependencies (yt-dlp)

**Expected Output:**
```
✅ NF-6: All tests passed - Pipeline is idempotent and resumable
```

---

### NF-7: Pipeline Error Handling
**Target:** No single failure kills a batch

```bash
python tests/test_error_resilience.py
```

**Requirements:**
- Core dependencies
- Brain dependencies (for entity extractor)

**Expected Output:**
```
✅ NF-7: All tests passed - Pipeline handles errors gracefully
```

---

### NF-8: Dashboard Uptime
**Target:** ≥99% (monthly)

See [docs/uptime_monitoring.md](../docs/uptime_monitoring.md) for:
- Monitoring setup instructions (UptimeRobot, Pingdom, etc.)
- Health check endpoint implementation
- Incident response procedures
- Monthly reporting template

---

## Running All Benchmarks

Run all available benchmarks:

```bash
# Run all non-GPU benchmarks
python benchmarks/run_all.py

# Include GPU benchmarks (requires audio file)
python benchmarks/run_all.py --include-gpu path/to/audio.wav
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Performance Benchmarks

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run benchmarks
        run: |
          python benchmarks/bench_entity_extraction.py
          python benchmarks/bench_graph_computation.py
          python tests/test_idempotency.py
          python tests/test_error_resilience.py
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: benchmark_results.json
```

---

## Interpreting Results

### Performance Targets

| Benchmark | Target | Good | Acceptable | Needs Optimization |
|-----------|--------|------|------------|-------------------|
| NF-1: Transcription RTF | ≥6x | >8x | 6-8x | <6x |
| NF-2: Entity Extraction | ≤30s/hr | <15s | 15-30s | >30s |
| NF-3: Graph Computation | ≤5s | <2s | 2-5s | >5s |
| NF-4: Dashboard Load | ≤3s | <2s | 2-3s | >3s |
| NF-5: Interaction Latency | ≤100ms | <50ms | 50-100ms | >100ms |

### Reliability Targets

| Test | Target | Status |
|------|--------|--------|
| NF-6: Idempotency | No duplicates | ✅/❌ |
| NF-6: Resumability | Can resume | ✅/❌ |
| NF-7: Error Handling | Continue on failure | ✅/❌ |
| NF-8: Uptime | ≥99% | Monthly report |

---

## Troubleshooting

### Benchmark Failures

**NF-1: Transcription too slow**
- Verify GPU is available and CUDA is working
- Try faster-whisper instead of standard Whisper
- Use smaller model (base instead of large)
- Enable INT8 quantization

**NF-2: Entity extraction too slow**
- Profile code to find bottlenecks
- Consider caching alias resolver results
- Optimize regex patterns
- Use compiled regex patterns

**NF-3: Graph computation too slow**
- Use sparse matrix representations
- Pre-compute common subgraphs
- Cache centrality calculations
- Consider approximate algorithms for large graphs

**NF-4: Dashboard slow to load**
- Check Streamlit caching is enabled
- Optimize data loading
- Reduce initial graph size
- Compress static assets

**NF-5: High interaction latency**
- Verify graph stabilization settings
- Check browser hardware acceleration
- Reduce graph complexity if needed
- Profile JavaScript performance

---

## Benchmark Results Archive

Store benchmark results for tracking over time:

```bash
# Save results
python benchmarks/run_all.py --save-results results/$(date +%Y%m%d).json

# Compare with previous run
python benchmarks/compare_results.py results/20240115.json results/20240122.json
```

---

## Contributing

When adding new benchmarks:

1. Follow the naming convention: `bench_*.py` for benchmarks, `test_*.py` for tests
2. Include clear documentation of requirements and expected output
3. Make benchmarks reproducible (use fixed seeds for randomness)
4. Output structured results (JSON) for automation
5. Print human-readable summary to stdout

---

## References

- Software Requirements Document (SRD): `docs/SRD_v1.0.md` §12.1-12.2
- See GitHub issue for complete NF-1 through NF-8 requirements
