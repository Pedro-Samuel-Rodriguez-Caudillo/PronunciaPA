# Plan - CLI Skeleton & UX (MK-3)

## Phase 1: Foundation & Registry Commands [checkpoint: d41b958]
Establishing the full command structure and implementing metadata commands.

- [x] Task: Refactor `ipa_core/api/cli.py` to use a cleaner sub-command structure if needed, or refine existing commands. (d04236f)
- [x] Task: Implement `pronunciapa config show` to display the active YAML/Env configuration. (d04236f)
- [x] Task: Implement `pronunciapa plugin list` command to display registered plugins from `ipa_core/plugins/registry.py`. (d04236f)
- [x] Task: Write contract tests for CLI command discovery and help messages. (d04236f)
- [x] Task: Conductor - User Manual Verification 'Foundation & Registry Commands' (Protocol in workflow.md) (d41b958)


## Phase 2: Rich Output & Pipeline Commands [checkpoint: de04e9c]
Enhancing core commands with polished visual feedback.

- [x] Task: Refactor `compare` command to use `rich.table` for displaying phonetic alignments by default. (0c4a6c6)
- [x] Task: Implement `--format` flag in `compare` to support `raw` (JSON) and `aligned` (text-only) views. (0c4a6c6)
- [x] Task: Add a loading spinner (via `rich.console.status`) for `transcribe` and `compare` long-running operations. (0c4a6c6)
- [x] Task: Create integration tests for `compare` output formatting. (0c4a6c6)
- [x] Task: Conductor - User Manual Verification 'Rich Output & Pipeline Commands' (Protocol in workflow.md) (de04e9c)


## Phase 3: Implicit Download UX [checkpoint: 3d0a164]
Implementing the model management flow with progress indicators.

- [x] Task: Create a `ModelManager` or utility in `ipa_core/plugins/base.py` to handle "Missing Model" detection. (0c4a6c6)
- [x] Task: Integrate `rich.progress` into the `Kernel.setup()` or plugin initialization flow to show a progress bar during (mocked) downloads. (0c4a6c6)
- [x] Task: Update `AllosaurusASR` (or a stub) to trigger this download flow if assets are missing. (0c4a6c6)
- [x] Task: Verify the download UX by simulating a missing model in a controlled test environment. (0c4a6c6)
- [x] Task: Conductor - User Manual Verification 'Implicit Download UX' (Protocol in workflow.md) (3d0a164)

