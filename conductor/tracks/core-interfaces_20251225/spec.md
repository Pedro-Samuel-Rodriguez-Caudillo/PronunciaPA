# Specification - Core Interfaces Definition (MK-1)

## Overview
This track focuses on defining the foundational Python protocols (interfaces) that will drive the PronunciaPA microkernel. By establishing strict, asynchronous contracts for ASR, Text-to-IPA, Comparison, and Preprocessing, we ensure the system remains modular, extensible, and high-performance.

## Functional Requirements
*   Define the following Python Protocols in `ipa_core/ports/`:
    *   `ASRBackend`: Transcribes audio to IPA tokens.
    *   `TextRefProvider`: Converts reference text to IPA tokens.
    *   `Comparator`: Aligns and compares two sequences of IPA tokens.
    *   `Preprocessor`: Handles audio normalization and token cleanup.
*   **Async Support:** All primary processing methods (e.g., `transcribe`, `to_ipa`, `compare`, `process_audio`) must be defined as `async`.
*   **Lifecycle Management:** Implement a base class or mixin providing optional `async setup()` and `async teardown()` methods with default no-op implementations.
*   **Data Types:** Use the types defined in `ipa_core/types.py` (or define them if missing) to ensure consistency (e.g., `Token`, `AudioInput`, `CompareResult`).

## Non-Functional Requirements
*   **Strict Typing:** Use Python type hints throughout.
*   **Documentation:** Every protocol and method must have clear docstrings explaining inputs, outputs, and expected behavior.
*   **Zero Logic:** These files should contain only interface definitions and type hints, no functional implementation.

## Acceptance Criteria
*   [ ] Files created/updated in `ipa_core/ports/` for all 4 interfaces.
*   [ ] All primary methods are `async`.
*   [ ] `setup` and `teardown` methods are available and optional for all interfaces.
*   [ ] The code passes `mypy` type checking.
*   [ ] Unit tests verify that "dummy" implementations of these protocols can be instantiated.

## Out of Scope
*   Actual implementation of any backend (Allosaurus, Epitran, etc.).
*   Kernel orchestration logic (Pipeline runner).
*   CLI or API implementation.
