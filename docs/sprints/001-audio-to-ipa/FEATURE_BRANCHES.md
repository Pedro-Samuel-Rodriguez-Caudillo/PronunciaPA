# Guía de trabajo por rama (Sprint 01)

Objetivo
- Que cada desarrollador sepa rápidamente qué hacer, en qué archivos trabajar y cómo validar su entrega.

Convención de ramas
- feature/<owner>/<kebab-feature>
- Este sprint usa 3 ramas:
  - feature/ricardo840/audio-io-asr-stub
  - feature/CWesternBurger/pipeline-transcribe-cli
  - feature/Pedro-Samuel-Rodriguez-Caudillo/preprocessor-basic

---

Persona: ricardo840
Rama: feature/ricardo840/audio-io-asr-stub
Alcance
- Implementar utilidades de audio I/O (WAV PCM mínimo) y un backend ASR de stub para smoke tests.

Archivos (crear/modificar)
- Crear: `ipa_core/backends/audio_io.py` (ya agregado):
  - `sniff_wav(path) -> WavInfo`
  - `to_audio_input(path) -> AudioInput`
- Crear: `ipa_core/backends/asr_stub.py` (ya agregado):
  - Clase `StubASR(params)` que implemente `ASRBackend.transcribe()` devolviendo `ASRResult.tokens`.
- Opcional futuro (documentar si se toca): `ipa_core/backends/whisper_ipa.py`

Criterios de éxito
- `sniff_wav()` devuelve `sample_rate` y `channels` válidos para un WAV.
- `StubASR.transcribe()` retorna tokens cuando se le pasa un `AudioInput` válido.

Cómo testear
- Grabar audio: `python scripts/record_wav.py --out inputs/rec.wav --seconds 2`
- Sniff WAV: `python scripts/tests/test_audio_io_sniff.py inputs/rec.wav`
- Pipeline con stub: `python scripts/tests/test_transcribe_stub.py`

Notas
- No introducir dependencias pesadas en esta rama.
- Manejar errores con `ipa_core.errors.FileNotFound` y `UnsupportedFormat`.

---

Persona: CWesternBurger
Rama: feature/CWesternBurger/pipeline-transcribe-cli
Alcance
- Implementar el pipeline de transcripción independiente de comparación y exponer stub de CLI `cli_transcribe`.

Archivos (crear/modificar)
- Crear: `ipa_core/pipeline/transcribe.py` (ya agregado):
  - `transcribe(pre, asr, textref, *, audio, lang) -> list[Token]`
  - Flujo: `pre.process_audio` → `asr.transcribe` → tokens o `raw_text` → `textref.to_ipa` → `pre.normalize_tokens`.
- Modificar: `ipa_core/api/cli.py` (ya agregado el stub):
  - Mantener `cli_transcribe(...) -> list[str]` como stub; no romper `cli_compare`.
  - Documentar flags esperadas: `--audio`, `--lang`, `--config` (futuro).

Criterios de éxito
- Importar `transcribe` y ejecutar el script de prueba sin errores.
- `cli_transcribe` existe (aunque NotImplemented por ahora).

Cómo testear
- `python scripts/tests/test_transcribe_stub.py` (usa BasicPreprocessor + StubASR).
- `python scripts/tests/test_cli_transcribe_stub.py` (verifica el símbolo CLI).

Notas
- No implementar `registry` ni `runner` aquí; mantener enfoque en transcribe.
- Coordinar con ricardo y pedro para entradas/salidas de funciones.

---

Persona: Pedro-Samuel-Rodriguez-Caudillo
Rama: feature/Pedro-Samuel-Rodriguez-Caudillo/preprocessor-basic
Alcance
- Implementar un preprocesador básico que cumpla el contrato y normalice tokens de forma idempotente.

Archivos (crear/modificar)
- Modificar: `ipa_core/preprocessor_basic.py` (ya implementado):
  - `process_audio(audio) -> AudioInput` validando claves.
  - `normalize_tokens(tokens) -> list[Token]` aplicando `strip().lower()` y filtrando vacíos.

Criterios de éxito
- `normalize_tokens([" A ", "b", "  ", "C"])` → `["a", "b", "c"]`.
- `process_audio` no rompe con AudioInput válido y devuelve estructura intacta.

Cómo testear
- `python scripts/tests/test_preprocessor_basic.py`

Notas
- No realizar resampleo real aún; solo validación ligera.

---

Entrega y medición
- Cada rama debe pasar sus scripts de prueba descritos en TESTING.md.
- Medición exacta de éxito: salida de scripts coincide con ejemplos (tokens IPA esperados, presencia de símbolos, y sin excepciones).
- Commits pequeños con Conventional Commits (feat/chore/docs) y referencia del owner.

Referencias
- Guía de pruebas: `docs/sprints/001-audio-to-ipa/TESTING.md`
- Guía de ramas: `docs/CONTRIBUTING_BRANCHES.md`
- Plan/Arquitectura del sprint: `docs/sprints/001-audio-to-ipa/PLAN.md`, `ARCHITECTURE.md`
