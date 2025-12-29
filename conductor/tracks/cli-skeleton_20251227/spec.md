# Specification - CLI Skeleton & UX (MK-3)

## Overview
This track focuses on building the functional skeleton of the PronunciaPA Command Line Interface (CLI) using `Typer`. It aims to define the command structure, argument parsing, and output formatting for the core workflows: transcription, comparison, configuration management, and plugin inspection. It also introduces user-friendly output using `rich` tables and implicit model downloading with progress bars.

## Functional Requirements
*   **Command Structure:** Implement the following top-level commands:
    *   `transcribe`: Convert audio to IPA.
    *   `compare`: Calculate PER and align audio against reference text.
    *   `config`: View current configuration.
    *   `plugin`: List available/loaded plugins.
*   **Output Formatting:**
    *   Default `compare` output: Use `rich` to display a colorful alignment table (Ref vs. Hyp).
    *   Advanced flag: `--format raw` or `--format aligned` for power users.
*   **Model Management:**
    *   Implement "Implicit Download" logic. If a backend model is missing during execution, auto-download it with a visible progress bar (using `tqdm` or `rich.progress`).
*   **Integration:** Ensure the CLI uses the `Kernel` and `AppConfig` (from MK-1/MK-2) to execute logic, rather than calling plugins directly.

## Non-Functional Requirements
*   **Type Safety:** Use `Typer` and Python type hints throughout.
*   **UX:** Error messages must be clean (no raw tracebacks for expected errors).
*   **Responsiveness:** Long-running tasks (transcription) should show a spinner or progress indicator.

## Acceptance Criteria
*   [ ] `pronunciapa --help` lists all commands.
*   [ ] `pronunciapa compare --audio ... --text ...` outputs a colorful table by default.
*   [ ] `pronunciapa config show` prints the active configuration.
*   [ ] `pronunciapa plugin list` shows registered plugins.
*   [ ] Simulating a missing model triggers a mock download progress bar before execution proceeds.

## Out of Scope
*   Implementation of the actual deep learning model download logic (we will mock the *downloader interface* and progress bar behavior, connecting it to the existing `StubASR` or `AllosaurusASR` setup logic).
