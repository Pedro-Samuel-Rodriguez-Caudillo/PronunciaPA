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

- [x] **Task: TDD - CLI 'benchmark' Command** [2318299]

- [x] **Task: Run & Document Baseline** [3911927]
- [~] **Task: Conductor - User Manual Verification 'Quality & Benchmarks' (Protocol in workflow.md)**

## Phase 3: Baseline Report [checkpoint: 3911927]
