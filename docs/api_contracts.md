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

### 2. Convert Text to IPA
*   **Path:** `POST /v1/textref`
*   **Request:** `multipart/form-data`
    *   `text`: String (texto a convertir)
    *   `lang`: String (e.g., "es", "en")
    *   `textref`: Optional string (nombre del proveedor texto→IPA)
*   **Response:** `TextRefResponse`

### 3. Compare Audio
*   **Path:** `POST /v1/compare`
*   **Request:** `multipart/form-data`
    *   `audio`: Audio file (Binary)
    *   `text`: Reference text string
    *   `lang`: String
*   **Response:** `CompareResponse`

### 4. Feedback (LLM Local)
*   **Path:** `POST /v1/feedback`
*   **Request:** `multipart/form-data`
    *   `audio`: Audio file (Binary)
    *   `text`: Reference text string
    *   `lang`: String
    *   `model_pack`: Optional model pack id/path
    *   `llm`: Optional LLM adapter override
    *   `prompt_path`: Optional prompt override path
    *   `output_schema_path`: Optional schema override path
    *   `persist`: Optional boolean to save locally
*   **Response:** `FeedbackResponse`

## Error Contract

Los endpoints HTTP deben devolver errores estructurados con el mismo shape base:

```json
{
  "detail": "Human readable message",
  "type": "error-category",
  "code": "optional-machine-code"
}
```

Notas operativas:
- `detail` es obligatorio y debe ser apto para logs y UI.
- `type` clasifica el origen (`validation_error`, `kernel_error`, `audio_error`, etc.).
- `code` es opcional y sirve para clientes que necesiten decisiones mas estables que el texto.
- Los cambios en este contrato deben actualizar las pruebas HTTP de `ipa_server/tests/` antes de tocar el frontend.

## Operational Notes

- `GET /health` es un chequeo de disponibilidad liviano: no debe forzar cargas pesadas de modelos para responder.
- El backend asume `ffmpeg` disponible como dependencia operativa base para normalizacion de audio.
- La resolucion de idioma solicitada se centraliza para que `transcribe`, `compare` y `feedback` compartan el mismo comportamiento.

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

### TextRefResponse
```typescript
export interface TextRefResponse {
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

### FeedbackResponse
```typescript
export interface FeedbackResponse {
  report: ErrorReport;
  compare: CompareResponse;
  feedback: FeedbackPayload;
}
```

### ErrorReport
```typescript
export interface ErrorReport {
  target_text: string;
  target_ipa: string;
  observed_ipa: string;
  metrics: Record<string, any>;
  ops: EditOp[];
  alignment: Array<[string | null, string | null]>;
  lang: string;
  meta: Record<string, any>;
}
```

### FeedbackPayload
```typescript
export interface FeedbackPayload {
  summary: string;
  advice_short: string;
  advice_long: string;
  drills: Array<{ type: string; text: string }>;
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
  5.  **Error Paths:** If the change affects error handling, verify that the response keeps the shared `detail/type/code` contract and update API smoke tests if needed.

## Mock Data
Example JSONs for development are located in `frontend/src/mocks/`:
*   `success_transcription.json`
*   `comparison_result.json`
*   `feedback_result.json`
*   `error_invalid_audio.json`
