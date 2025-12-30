# Plan: MK-8 Frontend Contracts

Establishing the data structures and API schemas between the backend and frontend to enable parallel development.

## Phase 1: Backend Domain Models & Schema [checkpoint: 57c212a]
Define the Pydantic models in the FastAPI server that will serve as the contract source of truth.

- [x] **Task: TDD - Define Transcription & Audio Models** [b0902eb]
    - Write unit tests in `ipa_server/tests/test_contracts.py` that validate the expected structure of Audio Upload requests and Transcription responses.
    - Implement the Pydantic models in `ipa_server/models.py` (or similar) to make the tests pass.
- [x] **Task: TDD - Define Comparison & Error Models** [b0902eb]
    - Write unit tests for Comparison result structures (IPA diffs, scores) and standard Error response schemas.
    - Implement the corresponding Pydantic models.
- [ ] **Task: Conductor - User Manual Verification 'Backend Domain Models & Schema' (Protocol in workflow.md)**

## Phase 2: Frontend Type Synchronization & Mocks
Translate the backend contracts into TypeScript and create sample data for UI prototyping.

- [x] **Task: Create Scenarios Mock Data** [a7b41b9]
    - Create `frontend/src/mocks/` directory.
    - Generate `success_transcription.json`, `comparison_result.json`, and `error_invalid_audio.json`.
- [ ] **Task: Define TypeScript Interfaces**
    - Create `frontend/src/types/api.ts`.
    - Manually or via tooling (e.g., extracting from FastAPI's `/openapi.json`), define the TS interfaces matching the backend models.
- [ ] **Task: Verify Type-Mock Consistency**
    - Create a small test utility or script to ensure the created JSON mocks strictly follow the TypeScript interfaces.
- [ ] **Task: Conductor - User Manual Verification 'Frontend Type Synchronization & Mocks' (Protocol in workflow.md)**

## Phase 3: Documentation & Integration Guide
Finalize the contract documentation and provide clear instructions for future updates.

- [ ] **Task: Create API Contracts Documentation**
    - Create `docs/api_contracts.md`.
    - Document the endpoints, data flow, and the process for updating types when backend models change.
- [ ] **Task: Final Contract Validation**
    - Run the backend server, fetch the OpenAPI JSON, and perform a final check against the frontend types.
- [ ] **Task: Conductor - User Manual Verification 'Documentation & Integration Guide' (Protocol in workflow.md)**
