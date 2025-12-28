# Specification - Configuration DX and Defaults (MK-2)

## Overview
This track aims to complete the configuration module (`ipa_core/config`) by focusing on User Experience (DX). We will implement a robust search path for configuration files, provide sane internal fallbacks so the system works "out of the box," and ensure that configuration errors are reported to the user in a clear, human-readable format.

## Functional Requirements
*   **Configuration Search Path:** Implement logic to look for `config.yaml` or `configs/local.yaml` in the current directory, and allow overrides via the `PRONUNCIAPA_CONFIG` environment variable.
*   **In-Memory Defaults:** If no configuration file is found, the system must instantiate a default `AppConfig` using "stub" or "default" plugins (ASR: allosaurus, TextRef: grapheme, Comparator: levenshtein, Preprocessor: basic).
*   **Friendly Error Reporting:** Wrap configuration loading in a try-except block to catch Pydantic `ValidationError`. Instead of a raw traceback, print a concise summary identifying the problematic field and the reason for the failure.
*   **Configuration Schema Sync:** Ensure `ipa_core/config/schema.py` accurately reflects the requirements of the `Kernel` (e.g., correct field names for plugin parameters).

## Non-Functional Requirements
*   **Minimal Dependencies:** Keep the loading logic lightweight, relying primarily on `PyYAML` and `Pydantic`.
*   **No Clutter:** Do not automatically create physical files on the user's disk unless explicitly requested.

## Acceptance Criteria
*   [ ] Running the CLI without a `config.yaml` file works using default stubs.
*   [ ] Specifying a non-existent config file via `PRONUNCIAPA_CONFIG` results in a clear error message.
*   [ ] A malformed YAML file (e.g., wrong field names) produces a human-readable error summary instead of a traceback.
*   [ ] Unit tests verify the search precedence (Env Var > Local File > Defaults).

## Out of Scope
*   Implementation of complex validation logic (e.g., cross-referencing plugin names with the registry during the *loading* phase).
*   A `config init` command (this can be a future chore).
