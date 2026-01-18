# Implementation Plan: Plugin Management CLI

This plan outlines the steps to integrate plugin management commands into the `pronunciapa` CLI, leveraging `importlib.metadata` and the existing configuration system.

## Phase 1: Foundation & Discovery [checkpoint: 572e644]
Focus on the core logic for finding and identifying installed plugins.

- [x] Task: Create `ipa_core/plugins/manager.py` to handle plugin discovery using `importlib.metadata`. 835ed1f
- [x] Task: Define a standard `PluginMetadata` dataclass/type to unify metadata extracted from packages. 835ed1f
- [x] Task: Implement `get_installed_plugins()` to filter entry points by the `pronunciapa.plugins` group. 835ed1f
- [x] Task: Write tests for plugin discovery using a mock entry point. 835ed1f
- [x] Task: Conductor - User Manual Verification 'Phase 1: Foundation & Discovery' (Protocol in workflow.md) 572e644

## Phase 2: CLI Integration [checkpoint: 1c4aad5]
Integrate the management logic into the command-line interface.

- [x] Task: Identify the current CLI entry point (checking `ipa_core/interfaces/cli.py`). 822bae7
- [x] Task: Implement `pronunciapa plugins list` command with formatted table output. 822bae7
- [x] Task: Implement `pronunciapa plugins info <name>` command to show detailed metadata. 822bae7
- [x] Task: Implement logic to check "Enabled" status against `configs/local.yaml`. 822bae7
- [x] Task: Write tests for the CLI subcommands using a CLI runner (e.g., Click's CliRunner). 822bae7
- [x] Task: Conductor - User Manual Verification 'Phase 2: CLI Integration' (Protocol in workflow.md) 1c4aad5

## Phase 3: Lifecycle Management [checkpoint: b8d479b]
Implement the ability to install and remove plugins.

- [x] Task: Implement `pronunciapa plugins install <source>` using `subprocess` to call `pip`. 2413a9e
- [x] Task: Implement `pronunciapa plugins uninstall <name>` using `subprocess` to call `pip`. 2413a9e
- [x] Task: Add safety checks (e.g., preventing uninstallation of core system plugins). 2413a9e
- [x] Task: Write integration tests for install/uninstall using a temporary virtual environment or dummy package. 2413a9e
- [x] Task: Conductor - User Manual Verification 'Phase 3: Lifecycle Management' (Protocol in workflow.md) b8d479b

## Phase 4: Final Polish & Documentation
Ensure the system is robust and well-documented.

- [~] Task: Add error handling for common `pip` failures (no network, package not found).
- [~] Task: Update the project's README or create a dedicated `PLUGINS.md` with usage instructions.
- [~] Task: Verify overall code coverage for the new `plugins` module.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Final Polish & Documentation' (Protocol in workflow.md)
