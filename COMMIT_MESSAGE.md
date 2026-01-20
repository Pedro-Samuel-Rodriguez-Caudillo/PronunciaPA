## Establecer política de modelos ASR → IPA

### Cambios principales

- **scripts/download_models.py**: Eliminar descarga por defecto de Wav2Vec2 texto; solo Allosaurus (IPA) + eSpeak
- **ipa_core/plugins/base.py**: Añadir atributo `output_type` para declarar tipo de salida (ipa/text/none)
- **ipa_core/kernel/core.py**: Validar que ASR produce IPA si `require_ipa=True`
- **Backends**: Marcar Allosaurus como `output_type="ipa"`, Vosk/Wav2Vec2 como `output_type="text"`
- **Documentación**: Actualizar README.md, PLUGINS.md, crear model-policy.md y QUICKREF.md
- **Tests**: Añadir tests de política de descarga y validación de output_type

### Propósito

PronunciaPA es un microkernel de análisis fonético que requiere ASR → IPA directo para capturar alófonos reales del usuario. Modelos que producen texto (Wav2Vec2-texto, Vosk, Whisper) pierden información fonética crítica y NO son recomendados para evaluación de pronunciación.

### Niveles de evaluación

- **Fonémico** (`evaluation_level=phonemic`): Para aprender a hablar, evalúa fonemas `/kasa/`
- **Fonético** (`evaluation_level=phonetic`): Para pronunciación técnica, evalúa alófonos `[ˈka.sa]`

### LLMs (TinyLlama/Phi)

Clarificado que se usan para generación de ejercicios y feedback, NO para ASR.

### Archivos modificados

- scripts/download_models.py
- ipa_core/plugins/base.py
- ipa_core/kernel/core.py
- ipa_core/backends/allosaurus_backend.py
- ipa_core/backends/wav2vec2_backend.py
- ipa_core/backends/vosk_backend.py
- README.md
- PLUGINS.md

### Archivos creados

- conductor/model-policy.md
- conductor/IMPLEMENTATION_SUMMARY.md
- conductor/QUICKREF.md
- scripts/tests/test_download_models_policy.py
- scripts/tests/test_plugin_output_types.py

### Tests

```bash
python scripts/tests/test_download_models_policy.py
# ✅ Help output correct
# ✅ Wav2Vec2 is optional (not default)
# ✅ Script imports correctly and has required functions

python scripts/tests/test_plugin_output_types.py
# ✅ BasePlugin has output_type attribute
# ✅ IPA backend declares output_type='ipa'
# ✅ Text backend declares output_type='text'
# ✅ AllosaurusBackend declares output_type='ipa'
# ✅ Wav2Vec2Backend declares output_type='text' by default
# ✅ VoskBackend declares output_type='text'
```

### Breaking changes

⚠️ **Potencial**: Usuarios que ejecutaban `python scripts/download_models.py` sin flags ya NO descargarán Wav2Vec2 texto por defecto. Ahora solo descarga Allosaurus (IPA) + verifica eSpeak.

**Migración**:
- Si usabas Wav2Vec2 texto: añade `--wav2vec2-ipa-model` con un modelo IPA
- Si usabas Vosk: añade `require_ipa: false` en config (no recomendado)
- Recomendado: migrar a Allosaurus (ya incluido por defecto)
