# Plan - Core Interfaces Definition (MK-1)

## Phase 1: Foundation (Types & Lifecycle) [checkpoint: de16d7f]
Establishing the shared vocabulary and the base behavior for all plugins.

- [x] Task: Define/Refine core types in `ipa_core/types.py` (Token, AudioInput, CompareResult, etc.) (141c5ab)
- [x] Task: Implement `BasePlugin` lifecycle class with `async setup()` and `async teardown()` (885a265)
- [x] Task: Conductor - User Manual Verification 'Foundation' (Protocol in workflow.md)

## Phase 2: Core Port Protocols
Defining the asynchronous contracts for the primary microkernel ports.

- [x] Task: Define `ASRBackend` protocol in `ipa_core/ports/asr.py` (bb89c9a)
- [~] Task: Define `TextRefProvider` protocol in `ipa_core/ports/textref.py`
- [ ] Task: Define `Comparator` protocol in `ipa_core/ports/compare.py`
- [ ] Task: Define `Preprocessor` protocol in `ipa_core/ports/preprocess.py`
- [ ] Task: Conductor - User Manual Verification 'Core Port Protocols' (Protocol in workflow.md)

## Phase 3: Integration and Validation
Ensuring all interfaces are correctly typed and can be implemented.

- [ ] Task: Create contract tests in `ipa_core/ports/tests/` to verify protocol compliance
- [ ] Task: Verify project-wide type safety with `mypy`
- [ ] Task: Conductor - User Manual Verification 'Integration and Validation' (Protocol in workflow.md)
