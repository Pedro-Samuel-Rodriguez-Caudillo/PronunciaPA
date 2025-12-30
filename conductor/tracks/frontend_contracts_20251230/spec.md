# Specification: MK-8 Frontend Contracts

## Overview
Establish and formalize the API contracts between the `ipa_server` (Backend) and the `frontend` application. This track aims to freeze the data structures and communication protocols required for future UI development, ensuring that frontend work can proceed with clear, typed expectations.

The "Source of Truth" will be the OpenAPI schema generated from Backend Pydantic models.

## Functional Requirements

### 1. Backend Schema Definitions (Pydantic)
Define the core data models in `ipa_server` to support key user flows. These models will drive the OpenAPI schema generation.
*   **Audio Input:** structures for handling file uploads or raw audio data.
*   **Transcription:** structures for returning recognized text and IPA tokens.
*   **Comparison/Feedback:** structures for returning comparison results (User IPA vs. Reference IPA), including diffs or scores.
*   **Errors:** Standardized error response format.

### 2. Frontend Type Synchronization (TypeScript)
Establish the TypeScript interfaces in the `frontend` that correspond to the backend models.
*   Generate or manually create TypeScript `interface` or `type` definitions based on the OpenAPI schema.
*   Ensure types cover Request payloads and Response bodies.

### 3. Mock Data Assets
Create static JSON files representing real-world usage scenarios.
*   `mock_transcription_success.json`
*   `mock_comparison_result.json`
*   `mock_error_invalid_format.json`

### 4. Contract Documentation
Create a reference document (e.g., `docs/api_contracts.md`) that outlines:
*   The key endpoints defined.
*   The data flow between Frontend and Backend.
*   Instructions on how to update the contracts (e.g., "If you change a Pydantic model, run X to update TS types").

## Non-Functional Requirements
*   **Naming Conventions:** Ensure clear mapping between Python `snake_case` and JavaScript/JSON conventions.
*   **Type Safety:** TypeScript types must be strict (avoiding `any` where possible).

## Acceptance Criteria
*   [ ] Pydantic models defined in `ipa_server` for Audio, Transcription, and Comparison domains.
*   [ ] Corresponding TypeScript interfaces exist in `frontend`.
*   [ ] At least 3 mock data JSON files created for key scenarios.
*   [ ] `docs/api_contracts.md` created and populated.

## Out of Scope
*   Implementation of the actual UI components (React/HTML/CSS).
*   Implementation of the heavy-lifting ASR or Comparison logic (Stubs/Mocks are sufficient).
