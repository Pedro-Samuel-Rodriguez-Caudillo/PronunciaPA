# Track Specification: Establish Core Microkernel Foundations and API Contracts

## Overview
This track focuses on defining and implementing the architectural skeleton of the PronunciaPA microkernel. The goal is to establish clear interfaces (ports), configuration schemas, and API contracts (CLI/HTTP) without fully implementing the business logic. This prepares the system for modular plugin development and ensures adherence to the "Ports & Adapters" architecture.

## Objectives
1.  **Define Ports:** Formalize Python `Protocol` definitions for `ASRBackend`, `TextRefProvider`, `Comparator`, and `Preprocessor`.
2.  **Configuration Schema:** Implement a Pydantic-based configuration loader for YAML files, including validation and defaults.
3.  **CLI Skeleton:** Define the `pronunciapa` CLI command structure using `Typer` or `argparse`, with stubs for the `transcribe` and `compare` commands.
4.  **API Skeleton:** Define the FastAPI routes for `/transcribe` and `/compare`, including request/response Pydantic models (contract-first).
5.  **Plugin Discovery:** Implement a basic mechanism to discover and load plugins (even if just from a local list for now).
6.  **Contract Tests:** Create tests that verify the defined interfaces and configuration loading work as expected (DoD v0).

## Detailed Requirements

### 1. Ports (Interfaces)
*   **Location:** `ipa_core/ports/`
*   **Requirements:**
    *   Use `typing.Protocol`.
    *   **ASRBackend:** `transcribe(audio: AudioInput, ...) -> ASRResult`
    *   **TextRefProvider:** `to_ipa(text: str, lang: str, ...) -> list[Token]`
    *   **Comparator:** `compare(ref: list[Token], hyp: list[Token], ...) -> CompareResult`
    *   **Preprocessor:** `process_audio(...)`, `normalize_tokens(...)`
*   **Data Structures:** Define shared `TypedDict` or Pydantic models for `AudioInput`, `ASRResult`, `CompareResult` in `ipa_core/types.py`.

### 2. Configuration
*   **Location:** `ipa_core/config/`
*   **Requirements:**
    *   Define a schema that allows selecting backend implementations by name (e.g., `backend: name: allosaurus`).
    *   Support overriding configuration via environment variables or CLI flags.
    *   Validate that referenced plugins exist (if possible at this stage) or at least that the format is correct.

### 3. CLI
*   **Location:** `ipa_core/api/cli.py` (entry point)
*   **Commands:**
    *   `pronunciapa transcribe --audio <path> --lang <lang>`
    *   `pronunciapa compare --audio <path> --text <text> --lang <lang>`
*   **Output:** Support JSON output for machine parsing.

### 4. HTTP API
*   **Location:** `ipa_core/api/http.py`
*   **Routes:**
    *   `POST /v1/transcribe`: Accepts audio file, returns ASR result.
    *   `POST /v1/compare`: Accepts audio file + text, returns comparison result.
    *   `GET /health`: Returns service status.
*   **Documentation:** Auto-generated OpenAPI (Swagger) docs must reflect the contracts.

## Architecture & Design
*   **Microkernel:** The core `ipa_core` package will orchestrate the flow.
*   **Dependency Injection:** The `Kernel` class (to be defined) will wire together the configured implementations of the ports.
*   **Error Handling:** Define a base `IpaCoreError` and specific exceptions for configuration and plugin loading errors.

## Testing Strategy
*   **Unit Tests:** specific tests for the configuration loader and schema validation.
*   **Contract Tests:** Verify that the "stub" implementations of the ports (if created) adhere to the Protocols.
*   **Integration Tests:** Verify that the CLI and API endpoints accept the defined inputs and return the defined structures (even if the values are mock data).
