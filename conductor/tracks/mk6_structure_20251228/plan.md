# Plan: MK-6 Estructura de Paquetes

## Phase 1: Preparation & Directory Setup [checkpoint: 75a8b13]
- [x] Task: Create new top-level directories for plugins and interfaces.
    - Create `plugins/allosaurus/ipa_plugin_allosaurus`
    - Create `ipa_server/`
- [x] Task: Initialize new packages with basic `__init__.py` and metadata.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Preparation & Directory Setup' (Protocol in workflow.md)

## Phase 2: Code Migration [checkpoint: b6e6135]
- [x] Task: Move `ipa_core/backends/asr_allosaurus.py` to `plugins/allosaurus/ipa_plugin_allosaurus/backend.py`.
- [x] Task: Move `ipa_core/api/http.py` to `ipa_server/main.py`.
- [x] Task: Refactor `ipa_core/api/cli.py` to `ipa_core/interfaces/cli.py` and update entry points.
- [x] Task: Clean up `ipa_core/backends` (keeping only stubs/built-ins).
- [x] Task: Conductor - User Manual Verification 'Phase 2: Code Migration' (Protocol in workflow.md)

## Phase 3: Decoupling & Integration [checkpoint: fd6c2c7]
- [x] Task: Update `ipa_core/plugins/registry.py` to remove hardcoded imports of Allosaurus.
- [x] Task: Configure `plugins/allosaurus/pyproject.toml` or update main `pyproject.toml` to register the Allosaurus entry point.
- [x] Task: Update imports across the entire project to reflect new structure.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Decoupling & Integration' (Protocol in workflow.md)

## Phase 4: Verification & Finalization
- [x] Task: Verify that `ipa_core` unit tests run successfully without `allosaurus` dependencies.
- [x] Task: Verify `ipa_core` + `ipa-plugin-allosaurus` works together via dynamic discovery.
- [x] Task: Update project-level documentation (`README.md`, `ARCHITECTURE.md`) with the new structure.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Verification & Finalization' (Protocol in workflow.md)
