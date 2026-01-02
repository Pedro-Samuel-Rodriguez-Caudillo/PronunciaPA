# Specification: Quality & Benchmarking

## Overview
As PronunciaPA moves towards a production-ready state, we need to quantify its performance. This track focuses on adding a benchmarking suite that allows developers and users to measure:
1.  **Accuracy:** How well does the model transcribe speech? (Metric: PER - Phone Error Rate)
2.  **Speed:** How fast does it run compared to real-time audio? (Metric: RTF - Real-Time Factor)

## Functional Requirements

### 1. Dataset Management
*   **Format:** The system must accept a standard manifest format (e.g., JSONL) where each line contains:
    *   `audio_path`: Path to WAV file.
    *   `text`: Reference text (orthographic or IPA).
    *   `lang`: Language code.

### 2. Metrics
*   **PER (Phone Error Rate):** $(S + D + I) / N$ where $N$ is the number of reference phones.
*   **RTF (Real-Time Factor):** $Processing Time / Audio Duration$. Ideally < 1.0 (faster than real-time).

### 3. CLI Command
*   New command: `pronunciapa benchmark`
*   **Arguments:**
    *   `--dataset`: Path to the manifest file.
    *   `--limit`: (Optional) Number of samples to process.
    *   `--output`: (Optional) Save detailed results to JSON/CSV.

## Non-Functional Requirements
*   **Reproducibility:** The benchmark should produce consistent results on the same hardware.
*   **Isolation:** Benchmarks should not be affected by debug logging (should auto-suppress console noise).

## Acceptance Criteria
*   [ ] A `benchmark` command is available in the CLI.
*   [ ] Running the command against a sample dataset produces a summary table.
*   [ ] A `BENCHMARKS.md` file exists in the root, documenting the current baseline performance of the ONNX model.
