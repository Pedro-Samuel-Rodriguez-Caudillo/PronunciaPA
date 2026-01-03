# Benchmarks - PronunciaPA

Last Updated: 2026-01-02

## Baseline Performance (Stub Backend)
Measured using a synthetic silent audio file.

| Metric | Value |
| :--- | :--- |
| Samples | 1 |
| Avg PER | 300.00% (Stub mismatch) |
| Avg RTF | 0.007x |

## Notes
- This benchmark was run using the `asr_stub` backend.
- PER is high because the stub always returns "h o l a" regardless of input.
- RTF reflects the overhead of the pipeline infrastructure without actual model inference.
