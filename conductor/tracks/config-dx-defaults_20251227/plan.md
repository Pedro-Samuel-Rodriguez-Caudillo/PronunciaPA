# Plan - Configuration DX and Defaults (MK-2)

## Phase 1: Robust Loading & Defaults [checkpoint: 9b1522f]
Implement the search strategy and in-memory defaults.

- [x] Task: Refine `AppConfig` schema in `ipa_core/config/schema.py` to ensure all fields have factory defaults. (a9e692e)
- [x] Task: Implement `load_config(path=None)` in `ipa_core/config/loader.py` with search path logic (Env -> CWD -> Defaults). (e2935c8)
- [x] Task: Create unit tests in `ipa_core/config/tests/` to verify search order and fallback behavior. (e2935c8)
- [x] Task: Conductor - User Manual Verification 'Robust Loading & Defaults' (Protocol in workflow.md) (9b1522f)


## Phase 2: Error Handling & CLI Integration
Make errors friendly and connect it to the CLI.

- [x] Task: Implement `format_validation_error` utility to transform Pydantic errors into user-friendly strings. (b6a5fdd)
- [x] Task: Integrate `load_config` into `ipa_core/api/cli.py` (replacing the current temporary logic). (ea80cf5)
- [~] Task: Verify handling of malformed config files via CLI integration tests.
- [ ] Task: Conductor - User Manual Verification 'Error Handling & CLI Integration' (Protocol in workflow.md)
