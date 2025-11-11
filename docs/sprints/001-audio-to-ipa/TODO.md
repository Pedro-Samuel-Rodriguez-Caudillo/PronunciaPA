# TODOs específicos (Sprint 01)

Asignación
- ricardo840: audio I/O + ASR stub.
- CWesternBurger: pipeline `transcribe` + CLI stub.
- Pedro-Samuel-Rodriguez-Caudillo: preprocessor básico + docs.

Tareas
- [ ] Implementar `ipa_core/backends/audio_io.py` (sniff WAV 16k mono; TODOs MP3/OGG).
- [ ] Implementar `ipa_core/backends/asr_stub.py` (tokens por params o de ejemplo).
- [ ] Implementar `ipa_core/pipeline/transcribe.py` (ASR→tokens o raw_text→TextRef).
- [ ] Añadir `cli_transcribe` en `ipa_core/api/cli.py` (stub, sin romper pruebas).
- [ ] Implementar `ipa_core/preprocessor_basic.py` (normalize_tokens idempotente).
- [ ] `scripts/record_wav.py` (opcional con sounddevice; documentado).
- [ ] `configs/sprint01.example.yaml` de referencia.
