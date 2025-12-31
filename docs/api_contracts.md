# API Contracts Documentation

This document defines the interface between the PronunciaPA Backend (`ipa_server`) and the Frontend.

## Source of Truth
The API is defined using **FastAPI** and **Pydantic** models in `ipa_server/models.py`. 
The OpenAPI schema is automatically generated at `/openapi.json` when the server is running.

## Key Endpoints

### 1. Transcribe Audio
*   **Path:** `POST /v1/transcribe`
*   **Request:** `multipart/form-data`
    *   `audio`: Audio file (Binary)
    *   `lang`: String (e.g., "es", "en")
*   **Response:** `TranscriptionResponse`

### 2. Compare Audio
*   **Path:** `POST /v1/compare`
*   **Request:** `multipart/form-data`
    *   `audio`: Audio file (Binary)
    *   `text`: Reference text string
    *   `lang`: String
*   **Response:** `CompareResponse`

## Data Structures (TypeScript)
Located in `frontend/src/types/api.ts`.

### TranscriptionResponse
```typescript
export interface TranscriptionResponse {
  ipa: string;
  tokens: string[];
  lang: string;
  meta: Record<string, any>;
}
```

### CompareResponse
```typescript
export interface CompareResponse {
  per: number;
  ops: EditOp[];
  alignment: Array<[string | null, string | null]>;
  meta: Record<string, any>;
}
```

## How to Update Contracts

When a change is needed in the data structures:
1.  **Backend:** Modify the Pydantic models in `ipa_server/models.py`.
2.  **Verify:** Run backend tests `python -m pytest ipa_server/tests/`.
3.  **Frontend:** Manually update `frontend/src/types/api.ts` to reflect the changes.
4.  **Sync Check:** Update the mocks in `frontend/src/mocks/` and run the verification script:
    ```bash
    cd frontend
    npx tsc src/verify_contracts.ts --noEmit --esModuleInterop --skipLibCheck --target esnext --moduleResolution node --resolveJsonModule
    ```

## Mock Data
Example JSONs for development are located in `frontend/src/mocks/`:
*   `success_transcription.json`
*   `comparison_result.json`
*   `error_invalid_audio.json`
