# Plan: MK-7 Plan de Pruebas

## Phase 1: Shared Contract Suites [checkpoint: 605288d]
- [x] Task: Create the `ipa_core.testing` package structure.
- [x] Task: Implement `ASRBackend` contract tests in `ipa_core.testing.contracts.asr`.
- [x] Task: Implement `TextRefProvider` and `Comparator` contract tests.
- [x] Task: Refactor `plugins/allosaurus` tests to inherit from the shared contract suite.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Shared Contract Suites' (Protocol in workflow.md)

## Phase 2: Kernel & Integration Consolidation
- [x] Task: Create `ipa_core/tests/integration/test_kernel_orchestration.py`.
- [x] Task: Implement tests for `Kernel.run` with various stub configurations (success, failures, edge cases).
- [x] Task: Ensure 100% coverage of the `Kernel` class logic.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Kernel & Integration Consolidation' (Protocol in workflow.md)

## Phase 3: Performance Benchmarking
- [ ] Task: Add `pytest-benchmark` or a custom RTF measurement utility.
- [ ] Task: Create `ipa_core/tests/performance/test_latency.py`.
- [ ] Task: Implement RTF baseline for `StubASR` and (if possible) `AllosaurusASR`.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Performance Benchmarking' (Protocol in workflow.md)

## Phase 4: E2E Smoke Tests & Finalization
- [ ] Task: Implement CLI smoke tests in `ipa_core/interfaces/tests/test_cli_smoke.py`.
- [ ] Task: Implement API smoke tests in `ipa_server/tests/test_api_smoke.py`.
- [ ] Task: Update `README.md` with instructions on how to run the different test layers.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: E2E Smoke Tests & Finalization' (Protocol in workflow.md)
