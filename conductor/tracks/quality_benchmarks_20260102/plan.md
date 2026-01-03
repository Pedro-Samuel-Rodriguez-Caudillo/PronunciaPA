# Plan: Quality & Benchmarking

Objective: Establish a baseline for system performance by measuring accuracy (Phone Error Rate) and speed (Real-Time Factor) of the offline ASR pipeline.

## Phase 1: Benchmark Infrastructure
Create the tools necessary to run reproducible performance tests.

- [x] **Task: TDD - Dataset Loader** [c3722f0]
    - Implement a utility to load a "golden set" of audio/transcript pairs (e.g., from Common Voice or a local folder).
    - Support standard formats (CSV/JSON manifest).
- [x] **Task: TDD - Metrics Calculator** [b5de80b]

## Phase 2: CLI Benchmark Command [checkpoint: b5de80b]
Expose the benchmarking tools to the user.

- [ ] **Task: TDD - CLI 'benchmark' Command**
    - Implement `pronunciapa benchmark --dataset <path> --model <name>`.
    - Output a rich table with PER (min/max/avg), RTF, and total duration.

## Phase 3: Baseline Report
Run the benchmark on a standard sample and document the results.

- [ ] **Task: Run & Document Baseline**
    - Create a small sample dataset (or download one).
    - Run the benchmark.
    - Commit a `BENCHMARKS.md` file with the results.
- [ ] **Task: Conductor - User Manual Verification 'Quality & Benchmarks' (Protocol in workflow.md)**
