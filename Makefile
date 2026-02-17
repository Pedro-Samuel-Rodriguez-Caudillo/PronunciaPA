.PHONY: test-unit test-int sync-types dev dev-web server flutter

PYTHON := python
ifeq ($(OS),Windows_NT)
	ifneq (,$(wildcard ./.venv/Scripts/python.exe))
		PYTHON := ./.venv/Scripts/python.exe
	endif
	ifneq (,$(wildcard ./.venv310/Scripts/python.exe))
		ifeq ($(PYTHON),python)
			PYTHON := ./.venv310/Scripts/python.exe
		endif
	endif
endif

# ── Dev launchers ────────────────────────────────────────
dev:
	@powershell -ExecutionPolicy Bypass -File ./dev.ps1

dev-web:
	@powershell -ExecutionPolicy Bypass -File ./dev.ps1 -Device chrome

dev-react:
	@powershell -ExecutionPolicy Bypass -File ./dev.ps1 -UI vite

server:
	@powershell -ExecutionPolicy Bypass -File ./dev.ps1 -ServerOnly

flutter:
	@powershell -ExecutionPolicy Bypass -File ./dev.ps1 -UIOnly

vite:
	@powershell -ExecutionPolicy Bypass -File ./dev.ps1 -UI vite -UIOnly

# ── Tests ────────────────────────────────────────────────
test-unit:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest \
		ipa_core/audio/tests/test_files.py \
		ipa_core/compare/tests/test_levenshtein.py \
		ipa_core/pipeline/tests/test_runner.py \
		ipa_core/textref/tests/test_epitran_provider.py \
		ipa_core/textref/tests/test_espeak_provider.py \
		ipa_core/services/tests/test_transcription_service.py \
		tests/utils

test-int:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest \
		ipa_core/api/tests/test_http_transcription.py \
		scripts/tests/test_cli_transcribe_stub.py \
		scripts/tests/test_cli_transcribe_errors.py

sync-types:
	@echo "🔄 Synchronizing TypeScript API types from OpenAPI schema..."
	$(PYTHON) scripts/sync_api_types.py
	@echo "✅ Type synchronization complete"
