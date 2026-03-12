.PHONY: test-l1 test-l2 test-l3 test-l4 test-functional test-performance \
        test-security test-reliability test-quality-report test-all \
        sync-types dev dev-web server flutter \
        install install-full install-espeak install-nltk setup bench \
        debug debug-json

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

# ── Instalación ──────────────────────────────────────────

## Instala dependencias mínimas (stub backends, sin modelos)
install:
	pip install -e '.[dev]'

## Instala todo: Allosaurus + eSpeak + CMU Dict + Ollama client
install-full:
	pip install -e '.[dev,speech,asr,ollama,cmudict]'
	@$(MAKE) install-nltk
	@echo ""
	@echo "Recuerda instalar eSpeak-NG en tu sistema:"
	@$(MAKE) install-espeak

## Descarga el corpus CMU Dict de NLTK (necesario para textref=cmudict)
install-nltk:
	$(PYTHON) -c "import nltk; nltk.download('cmudict', quiet=False)"

## Muestra instrucciones para instalar eSpeak-NG
install-espeak:
	@echo "── eSpeak-NG ──────────────────────────────────────"
	@echo "  Ubuntu/Debian : sudo apt install espeak-ng"
	@echo "  Fedora/RHEL   : sudo dnf install espeak-ng"
	@echo "  macOS         : brew install espeak-ng"
	@echo "  Windows       : https://github.com/espeak-ng/espeak-ng/releases"
	@echo "───────────────────────────────────────────────────"

## Instalación completa interactiva (guía paso a paso)
setup: install-full
	@echo ""
	@echo "✓ Python deps instalados"
	@echo ""
	@echo "Configuración recomendada para iniciar el servidor:"
	@echo ""
	@echo "  PRONUNCIAPA_ASR=allosaurus \\"
	@echo "  PRONUNCIAPA_TEXTREF=espeak \\"
	@echo "  PRONUNCIAPA_LLM=rule_based \\"
	@echo "  uvicorn ipa_server.main:get_app --reload --port 8000"
	@echo ""
	@echo "Sin modelos (modo rápido para desarrollo):"
	@echo ""
	@echo "  PRONUNCIAPA_ASR=stub PRONUNCIAPA_TEXTREF=grapheme \\"
	@echo "  uvicorn ipa_server.main:get_app --reload --port 8000"

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

# ── Tests (ISO/IEC/IEEE 29119 + ISO/IEC 25010) ────────────────────────

## L1 — Pruebas Unitarias: componentes aislados, sin modelos reales
test-l1:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest -m unit -v

## L2 — Pruebas de Integración: pipeline extremo a extremo en modo stub
test-l2:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest -m integration -v

## L3 — Pruebas de Sistema: CLI + API HTTP en modo stub
test-l3:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest -m system -v

## L4 — Pruebas E2E: flujos de usuario completos (requiere dispositivo/emulador)
test-l4:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest -m e2e -v

## Atributo Funcional (ISO 25010 §8.1): correción funcional
test-functional:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest -m functional -v

## Atributo Rendimiento (ISO 25010 §8.4): RTF, latencia
test-performance:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest -m performance -v

## Atributo Seguridad (ISO 25010 §8.5 + OWASP): path traversal, inputs
test-security:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest -m security -v

## Atributo Confiabilidad (ISO 25010 §8.3): idempotencia, degradación elegante
test-reliability:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest -m reliability -v

## Suite completa L1+L2+L3 (sin e2e/flutter que requieren device)
test-all:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest -m "unit or integration or system" -v

## Reporte HTML de cobertura — verifica ≥ 80 % y genera docs/coverage/
test-quality-report:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) -m pytest \
		-m "unit or integration or system" \
		--cov=ipa_core --cov-report=html:docs/coverage --cov-report=term-missing \
		--cov-fail-under=80 -q
	@echo ""
	@echo "✔ Reporte en docs/coverage/index.html"

sync-types:
	@echo "Synchronizing TypeScript API types from OpenAPI schema..."
	$(PYTHON) scripts/sync_api_types.py
	@echo "Type synchronization complete"

## Benchmark TTS round-trip en stub mode (CI-safe, sin modelos reales)
test-bench:
	PRONUNCIAPA_ASR=stub PYTHONPATH=. $(PYTHON) scripts/benchmark_tts_roundtrip.py \
		--lang es --stub --words 10

## Benchmark con modelos reales (requiere Allosaurus + eSpeak)
bench:
	PYTHONPATH=. $(PYTHON) scripts/benchmark_tts_roundtrip.py \
		--lang $(LANG) --words $(or $(WORDS),30) --verbose \
		$(if $(OUTPUT),--output $(OUTPUT),)

## Debug rápido del pipeline — tabla concisa por etapa
## Uso: make debug TEXT="hola mundo" LANG=es
##      make debug TEXT="hello" LANG=en TEXTREF=cmudict ASR=stub
debug:
	PYTHONPATH=. $(PYTHON) scripts/debug_pipeline.py \
		"$(or $(TEXT),hola mundo)" \
		--lang $(or $(LANG),es) \
		--asr $(or $(ASR),stub) \
		--textref $(or $(TEXTREF),espeak)

## Igual que debug pero salida JSON
debug-json:
	PYTHONPATH=. $(PYTHON) scripts/debug_pipeline.py \
		"$(or $(TEXT),hola mundo)" \
		--lang $(or $(LANG),es) \
		--asr $(or $(ASR),stub) \
		--textref $(or $(TEXTREF),espeak) \
		--json
