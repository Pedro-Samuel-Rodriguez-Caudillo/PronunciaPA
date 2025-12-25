# Track Plan: Establish Core Microkernel Foundations and API Contracts

## Phase 1: Core Types and Ports Definition [checkpoint: d15f97e]
- [x] Task: Define Shared Data Types fdec09d
- [x] Task: Define Port Protocols e20a197
- [x] Task: Conductor - User Manual Verification 'Core Types and Ports Definition' (Protocol in workflow.md)

## Phase 2: Configuration and Plugin Infrastructure [checkpoint: 0136f68]
- [x] Task: Define Configuration Schema a89af02
- [x] Task: Implement Configuration Loader 14ab013
- [x] Task: Define Plugin Registry/Discovery 83ea74a
- [x] Task: Conductor - User Manual Verification 'Configuration and Plugin Infrastructure' (Protocol in workflow.md)

## Phase 3: API Contracts (CLI & HTTP) [checkpoint: 706d404]
- [x] Task: Implement CLI Skeleton fae9282
- [x] Task: Implement HTTP API Skeleton 42e9587
- [x] Task: Conductor - User Manual Verification 'API Contracts (CLI & HTTP)' (Protocol in workflow.md)

## Phase 4: Integration and Final Verification
- [ ] Task: Create "Stub" Implementations
    - **Goal:** Create simple "No-Op" or "Echo" implementations of the ports to prove the wiring works.
    - **Verification:** Tests can instantiate these stubs via the plugin registry.
- [ ] Task: End-to-End Contract Test
    - **Goal:** A test that loads a config using stubs, initializes the kernel (mocked), and calls a CLI command.
    - **Verification:** `pytest` passes the end-to-end flow.
- [ ] Task: Conductor - User Manual Verification 'Integration and Final Verification' (Protocol in workflow.md)
