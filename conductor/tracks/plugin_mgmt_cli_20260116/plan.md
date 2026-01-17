# Implementation Plan: Plugin Management CLI

This plan outlines the steps to integrate plugin management commands into the `pronunciapa` CLI, leveraging `importlib.metadata` and the existing configuration system.

## Phase 1: Foundation & Discovery
Focus on the core logic for finding and identifying installed plugins.

- [~] Task: Create `ipa_core/plugins/manager.py` to handle plugin discovery using `importlib.metadata`.
- [ ] Task: Define a standard `PluginMetadata` dataclass/type to unify metadata extracted from packages.
- [ ] Task: Implement `get_installed_plugins()` to filter entry points by the `pronunciapa.plugins` group.
- [ ] Task: Write tests for plugin discovery using a mock entry point.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Foundation & Discovery' (Protocol in workflow.md)

## Phase 2: CLI Integration
Integrate the management logic into the command-line interface.

- [ ] Task: Identify the current CLI entry point (checking `ipa_core/interfaces/cli.py`).
- [ ] Task: Implement `pronunciapa plugins list` command with formatted table output.
- [ ] Task: Implement `pronunciapa plugins info <name>` command to show detailed metadata.
- [ ] Task: Implement logic to check "Enabled" status against `configs/local.yaml`.
- [ ] Task: Write tests for the CLI subcommands using a CLI runner (e.g., Click's CliRunner).
- [ ] Task: Conductor - User Manual Verification 'Phase 2: CLI Integration' (Protocol in workflow.md)

## Phase 3: Lifecycle Management
Implement the ability to install and remove plugins.

- [ ] Task: Implement `pronunciapa plugins install <source>` using `subprocess` to call `pip`.
- [ ] Task: Implement `pronunciapa plugins uninstall <name>` using `subprocess` to call `pip`.
- [ ] Task: Add safety checks (e.g., preventing uninstallation of core system plugins).
- [ ] Task: Write integration tests for install/uninstall using a temporary virtual environment or dummy package.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Lifecycle Management' (Protocol in workflow.md)

## Phase 4: Final Polish & Documentation
Ensure the system is robust and well-documented.

- [ ] Task: Add error handling for common `pip` failures (no network, package not found).
- [ ] Task: Update the project's README or create a dedicated `PLUGINS.md` with usage instructions.
- [ ] Task: Verify overall code coverage for the new `plugins` module.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Polish & Documentation' (Protocol in workflow.md)