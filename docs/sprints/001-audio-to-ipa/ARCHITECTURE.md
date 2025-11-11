# Arquitectura (Sprint 01)

Flujo
- Preprocessor.process_audio(AudioInput) → ASR.transcribe(audio, lang)
- Si ASR entrega `tokens`: Preprocessor.normalize_tokens(tokens)
- Si ASR entrega `raw_text`: TextRef.to_ipa(raw_text, lang) → normalize

Contratos
- `ASRBackend.transcribe(audio, lang) -> ASRResult`
- `TextRefProvider.to_ipa(text, lang) -> list[str]`
- `Preprocessor.normalize_tokens(tokens) -> list[str]`
