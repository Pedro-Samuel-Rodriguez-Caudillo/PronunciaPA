# Archivos (Sprint 01)

Agregar
- docs/sprints/001-audio-to-ipa/*
- ipa_core/pipeline/transcribe.py
- ipa_core/backends/audio_io.py
- ipa_core/backends/asr_stub.py
- scripts/record_wav.py (opcional)
- configs/sprint01.example.yaml

Modificar (en ramas de feature)
- ipa_core/api/cli.py (añadir `cli_transcribe`)
- ipa_core/preprocessor_basic.py (implementar)

Relaciones
- `transcribe.py` usa `Preprocessor`, `ASRBackend`, `TextRefProvider`.
- `cli_transcribe` arma kernel y llama a `transcribe`.
- `audio_io.py` valida WAV; `record_wav.py` crea insumo.
