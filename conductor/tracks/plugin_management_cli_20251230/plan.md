# Plan: Plugin Management CLI

Implementation of a comprehensive CLI toolset for discovering, inspecting, and managing the PronunciaPA plugin ecosystem.

## Phase 1: Enhanced Discovery & Listing [checkpoint: e568007]
Improve the internal discovery engine to provide the rich metadata required for the CLI.

- [x] **Task: TDD - Metadata Extraction in Discovery** [e9fef02]
    - Write unit tests for `ipa_core/plugins/discovery.py` to ensure it can extract metadata (Author, Description, Version) from installed packages.
    - Implement metadata extraction using `importlib.metadata`.
- [x] **Task: TDD - CLI 'plugins list' Command** [e9fef02]
    - Write tests for the new `plugins list` command in `ipa_core/interfaces/cli.py`.
    - Implement the command to show grouped plugins by type (ASR, TextRef, etc.).
- [ ] **Task: Conductor - User Manual Verification 'Enhanced Discovery & Listing' (Protocol in workflow.md)**

## Phase 2: Inspection & Validation
Implement commands to dive deep into specific plugins and verify their integrity.

- [ ] **Task: TDD - CLI 'plugins inspect' Command**
    - Write tests for `plugins inspect <name>`.
    - Implement detailed metadata view (Dependencies, entry points).
- [ ] **Task: TDD - CLI 'plugins validate' Command**
    - Write tests that check a mock "bad plugin" against its interface.
    - Implement validation logic in `ipa_core/plugins/registry.py` or similar, then expose via CLI.
- [ ] **Task: Conductor - User Manual Verification 'Inspection & Validation' (Protocol in workflow.md)**

## Phase 3: Package Management (Pip Wrappers)
Add the ability to install and uninstall plugins with safety checks.

- [ ] **Task: TDD - CLI 'plugins install' with Post-Check**
    - Write tests (mocking `subprocess`) for `plugins install`.
    - Implement the pip wrapper and the post-installation discovery check.
- [ ] **Task: TDD - CLI 'plugins uninstall' Command**
    - Write tests for `plugins uninstall`.
    - Implement the command with a confirmation prompt.
- [ ] **Task: Conductor - User Manual Verification 'Package Management (Pip Wrappers)' (Protocol in workflow.md)**

## Phase 4: Finalization
Polish the CLI experience and update documentation.

- [ ] **Task: CLI Help & Documentation Update**
    - Ensure all new commands have clear help strings.
    - Update `README.md` or dedicated docs with plugin management instructions.
- [ ] **Task: Conductor - User Manual Verification 'Finalization' (Protocol in workflow.md)**
