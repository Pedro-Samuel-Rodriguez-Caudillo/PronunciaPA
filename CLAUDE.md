# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PronunciaPA** is a phonetic pronunciation evaluation system. It converts audio to IPA (International Phonetic Alphabet) transcriptions and compares them against reference phonemes. Built as a **microkernel** with pluggable backends.

## Development Commands

### Backend Setup
```bash
# Minimal install (stub backends, no external dependencies)
pip install -e '.[dev]'

# Full install (real ASR/TTS models)
pip install -e '.[dev,speech,asr,ollama]'
```

### Running the Server
```bash
# Stub mode (no models needed)
PRONUNCIAPA_ASR=stub PRONUNCIAPA_TEXTREF=grapheme uvicorn ipa_server.main:get_app --reload --port 8000

# With real models
PRONUNCIAPA_ASR=allosaurus PRONUNCIAPA_TEXTREF=espeak uvicorn ipa_server.main:get_app --reload --port 8000

# Docker
docker-compose up --build
```

### Dev Launchers (Windows PowerShell wrappers in Makefile)
```bash
make dev          # Start server + Flutter client
make dev-react    # Start server + React (Vite) frontend
make server       # Server only
make vite         # Vite frontend only
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev       # http://localhost:5173
npm run build
```

### Mobile (Flutter)
```bash
cd pronunciapa_client
flutter pub get
flutter run -d android   # or -d ios, -d chrome
```

### Testing
```bash
# All tests
PYTHONPATH=. pytest

# Unit tests (fast, no external deps)
make test-unit

# Integration tests (stub backends)
make test-int

# Single test file
PRONUNCIAPA_ASR=stub PYTHONPATH=. pytest ipa_core/compare/tests/test_levenshtein.py -v

# With coverage (requires ≥80%)
pytest --cov=ipa_core --cov-report=html
```

### Type Checking
```bash
mypy ipa_core
```

### Sync TypeScript API types from OpenAPI schema
```bash
make sync-types
# or: python scripts/sync_api_types.py
```

## Architecture

### Core Components

```
ipa_core/          Python microkernel + all backends/services
ipa_server/        FastAPI HTTP server (thin wrapper over ipa_core)
frontend/          React 19 + TypeScript + Vite + Tailwind CSS web UI
pronunciapa_client/ Flutter mobile app (Clean Architecture)
plugins/           External plugin packages (e.g., plugins/allosaurus/)
scripts/           Utility scripts (download models, generate test audio, etc.)
```

### Microkernel Pattern

The `Kernel` dataclass (`ipa_core/kernel/core.py`) holds references to all port implementations and orchestrates the pipeline. **All backends communicate through Protocol interfaces** defined in `ipa_core/ports/`:

| Port | Protocol | Default implementations |
|------|----------|------------------------|
| `asr.py` | `ASRBackend` | `asr_stub`, `allosaurus_backend`, `wav2vec2_backend` |
| `textref.py` | `TextRefProvider` | `simple` (grapheme), `espeak`, `epitran` |
| `compare.py` | `Comparator` | `levenshtein`, `articulatory`, `noop` |
| `preprocess.py` | `Preprocessor` | `audio_io`, `audio_processing` |
| `tts.py` | `TTSProvider` | `piper`, `system`, stub adapter |
| `llm.py` | `LLMAdapter` | `llama_cpp`, `onnx`, `stub` |

### Pipeline Execution Flow

```
Audio + Text → Preprocessor → ASRBackend → TextRefProvider → Comparator → CompareResult
```

The two pipeline entry points are in `ipa_core/pipeline/runner.py`:
- `run_pipeline()` — basic, returns `CompareResult` (TypedDict)
- `run_pipeline_with_pack()` — richer, uses `LanguagePack` phonological rules, returns `ComparisonResult`

### Core Types (`ipa_core/types.py`)

```python
Token = str                    # single IPA symbol: "ə", "ʃ"
AudioInput = TypedDict         # {path, sample_rate, channels}
ASRResult = TypedDict          # {tokens, raw_text?, timestamps?, meta}
TextRefResult = TypedDict      # {tokens, meta}
CompareResult = TypedDict      # {per, ops, alignment, meta}
```

`per` (Phone Error Rate) ranges from 0.0 (identical) to 1.0 (completely different). Score = `(1 - per) * 100`.

### Plugin System

Plugins are discovered via Python entry points (`pronunciapa.plugins` group in `pyproject.toml`). The Allosaurus plugin lives in `plugins/allosaurus/` as a separate package registered via the root `pyproject.toml`.

To add a new backend:
1. Implement the relevant Protocol from `ipa_core/ports/`
2. Register it under `[project.entry-points."pronunciapa.plugins"]` in `pyproject.toml`

### Configuration

Priority order (highest wins): API/CLI params → environment variables → YAML file → defaults.

Key env vars:
- `PRONUNCIAPA_ASR` — backend name: `stub`, `allosaurus`, `wav2vec2`, `onnx`
- `PRONUNCIAPA_TEXTREF` — provider: `grapheme`, `espeak`, `epitran`
- `PRONUNCIAPA_STRICT_MODE` — `true` = fail fast, `false` = fall back to stubs
- `PRONUNCIAPA_CONFIG` — path to YAML config file

### HTTP API (`ipa_server/`)

`ipa_server/main.py` contains the FastAPI app factory. Routers in `ipa_server/routers/`:
- `pipeline.py` — `POST /v1/transcribe`, `/v1/compare`, `/v1/textref`
- `tts.py` — `POST /v1/tts`
- `drills.py` — `GET /v1/drills`
- `models.py` — `GET /v1/models`
- `ipa_catalog.py` — `GET/POST /v1/ipa/*`
- `health.py` — `GET /health`

Pydantic schemas for request/response are in `ipa_server/models.py`.

### Testing Strategy

- `asyncio_mode = "auto"` is set globally — all async tests work without manual decoration.
- Stub backends (`PRONUNCIAPA_ASR=stub`) are the baseline for all CI tests.
- Test fixtures and stub setup for API tests are in `ipa_server/tests/conftest.py`.
- Contract tests in `ipa_core/testing/contracts/` verify plugin compliance.
