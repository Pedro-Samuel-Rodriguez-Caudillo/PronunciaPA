# Arquitectura

Componentes
- Preprocessor: normaliza audio/tokens.
- ASR: audio → tokens o texto.
- TextRef: texto → tokens IPA.
- Pipeline: orquestra pasos.

Interacciones
- Preprocess(audio) → ASR.transcribe → normalize_tokens.
