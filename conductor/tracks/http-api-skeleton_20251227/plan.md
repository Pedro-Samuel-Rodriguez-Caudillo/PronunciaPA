# Plan - HTTP API Skeleton (MK-4)

## Phase 1: Foundation & Health Check
Setting up the FastAPI app structure, middleware, and basic connectivity.

- [x] Task: Refactor `ipa_core/api/http.py` to initialize the FastAPI app with CORS middleware using `PRONUNCIAPA_ALLOWED_ORIGINS`. (ea80cf5)
- [x] Task: Implement `GET /health` endpoint returning `{ "status": "ok" }`. (ea80cf5)
- [x] Task: Create contract tests for the health endpoint and CORS headers. (ea80cf5)
- [ ] Task: Conductor - User Manual Verification 'Foundation & Health Check' (Protocol in workflow.md)

## Phase 2: Action Endpoints & Kernel Integration
Connecting the HTTP routes to the microkernel processing logic.

- [ ] Task: Implement `POST /v1/transcribe` using `UploadFile` and integrating with `kernel.asr.transcribe`.
- [ ] Task: Implement `POST /v1/compare` using `UploadFile` and `Form`, integrating with `kernel.run`.
- [ ] Task: Implement global exception handlers to map `ValidationError` and `NotReadyError` to HTTP 400/503 responses.
- [ ] Task: Write integration tests for `transcribe` and `compare` using `TestClient` and `stub` plugins.
- [ ] Task: Conductor - User Manual Verification 'Action Endpoints & Kernel Integration' (Protocol in workflow.md)

## Phase 3: OpenAPI Documentation & Refinement
Ensuring the API is self-documenting and follows the established schemas.

- [ ] Task: Refine Pydantic models in `ipa_core/api/http.py` to match the global types and ensure accurate Swagger documentation.
- [ ] Task: Verify that the `/docs` endpoint correctly renders all input/output schemas.
- [ ] Task: Perform a final end-to-end integration test with a real (mocked) audio file.
- [ ] Task: Conductor - User Manual Verification 'OpenAPI Documentation & Refinement' (Protocol in workflow.md)
