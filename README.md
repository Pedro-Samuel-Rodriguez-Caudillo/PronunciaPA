# IPA Core
No tiene logica

## Objetivo
- Núcleo que orquesta:
  1) Backend ASR (audio a IPA),
  2) Conversor de texto a IPA (TextRef),
  3) Comparador (IPA vs IPA).
- Extensible con plugins sin tocar el núcleo.

## Estructura
ipa_core/
  api/        # CLI y futura API
  backends/   # ASR (vozIPA)
  compare/    # Comparación de cadenas IPA
  textref/    # TextoIPA (G2P)
  kernel.py   # Orquestación de plugins
  plugins.py  # Carga de entry points

### api/
- cli.py: comandos `ipa plugins` y `ipa run`.

### backends/
- base.py: interfaz ASRBackend.transcribe_ipa(audio_path) -> str
- null_backend.py: stub de prueba.
- whisper_ipa.py: stub para Whisper-IPA.

### compare/
- base.py: interfaz Comparator.compare(...) -> CompareResult
- noop.py: stub (PER=0, sin ops).

### textref/
- base.py: interfaz TextRef.text_to_ipa(text, lang) -> str
- noop.py: stub de prueba.

### Núcleo
- kernel.py: instancia plugins según KernelConfig.
- plugins.py: carga por entry points.

## Uso
pip install -e .
ipa plugins
ipa run .\sample.wav "hola mundo" --asr null --textref noop --cmp noop

## Próximos pasos
- Implementar backend ASR real (Whisper-IPA y/o Allosaurus).
- Integrar phonemizer/espeak en TextRef.
- Añadir comparador Levenshtein y PER.
