# Track Plan: Establish Core Microkernel Foundations and API Contracts

## Phase 1: Core Types and Ports Definition
- [x] Task: Define Shared Data Types fdec09d
    - **Goal:** Create `ipa_core/types.py` with `AudioInput`, `ASRResult`, `CompareResult` and other shared structures using `TypedDict` or Pydantic.
    - **Verification:** `mypy` check passes.
- [ ] Task: Define Port Protocols
    - **Goal:** Create `ipa_core/ports/` modules defining `ASRBackend`, `TextRefProvider`, `Comparator`, and `Preprocessor` protocols.
    - **Verification:** `mypy` check passes; code imports cleanly.
- [ ] Task: Conductor - User Manual Verification 'Core Types and Ports Definition' (Protocol in workflow.md)

## Phase 2: Configuration and Plugin Infrastructure
- [ ] Task: Define Configuration Schema
    - **Goal:** Implement Pydantic models for configuration in `ipa_core/config/schema.py` representing the YAML structure.
    - **Verification:** Unit tests validating valid/invalid YAML examples.
- [ ] Task: Implement Configuration Loader
    - **Goal:** Create `ipa_core/config/loader.py` to read YAML and environment variables into the schema.
    - **Verification:** Unit tests loading a sample config file.
- [ ] Task: Define Plugin Registry/Discovery
    - **Goal:** Create `ipa_core/plugins/registry.py` to handle registration and retrieval of port implementations.
    - **Verification:** Unit test registering and retrieving a dummy plugin.
- [ ] Task: Conductor - User Manual Verification 'Configuration and Plugin Infrastructure' (Protocol in workflow.md)

## Phase 3: API Contracts (CLI & HTTP)
- [ ] Task: Implement CLI Skeleton
    - **Goal:** Set up `ipa_core/api/cli.py` using `Typer` (or similar) with stubs for `transcribe` and `compare`.
    - **Verification:** Running `pronunciapa --help` shows the commands; commands return dummy JSON.
- [ ] Task: Implement HTTP API Skeleton
    - **Goal:** Set up `ipa_core/api/http.py` using FastAPI with stubs for `/transcribe` and `/compare` using the defined Pydantic models.
    - **Verification:** `uvicorn` starts; `/docs` shows the correct schema; requests return dummy 200 OK responses.
- [ ] Task: Conductor - User Manual Verification 'API Contracts (CLI & HTTP)' (Protocol in workflow.md)

## Phase 4: Integration and Final Verification
- [ ] Task: Create "Stub" Implementations
    - **Goal:** Create simple "No-Op" or "Echo" implementations of the ports to prove the wiring works.
    - **Verification:** Tests can instantiate these stubs via the plugin registry.
- [ ] Task: End-to-End Contract Test
    - **Goal:** A test that loads a config using stubs, initializes the kernel (mocked), and calls a CLI command.
    - **Verification:** `pytest` passes the end-to-end flow.
- [ ] Task: Conductor - User Manual Verification 'Integration and Final Verification' (Protocol in workflow.md)
