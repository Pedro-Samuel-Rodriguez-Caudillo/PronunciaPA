# Guía Rápida - Política de Modelos

## 🎯 Regla de Oro

**PronunciaPA requiere ASR que produzca IPA directo, NO texto.**

### ¿Por qué?

```
Usuario dice: [ˈka.θa] (con /θ/ peninsular)

❌ ASR texto → "casa" → G2P → /kasa/  (PERDISTE el [θ])
✅ ASR IPA   → [ˈka.θa]                (CAPTURADO correctamente)
```

---

## 📦 Descargar Modelos

### Mínimo (recomendado)
```bash
python scripts/download_models.py
```
Descarga: Allosaurus (ASR→IPA) + eSpeak (G2P)

### Con LLMs (ejercicios/feedback)
```bash
python scripts/download_models.py --with-llms --with-phi3
```

### Con Wav2Vec2 IPA (gated)
```bash
export HUGGINGFACEHUB_API_TOKEN=hf_YOUR_TOKEN
python scripts/download_models.py --wav2vec2-ipa-model facebook/wav2vec2-large-xlsr-53-ipa
```

---

## 🔌 Crear Plugin ASR

### Template Mínimo

```python
from ipa_core.plugins.base import BasePlugin
from ipa_core.ports.asr import ASRBackend, ASRResult

class MyIPABackend(BasePlugin, ASRBackend):
    """Mi backend que produce IPA."""
    
    output_type = "ipa"  # ⚠️ OBLIGATORIO
    
    async def transcribe(self, audio, lang=None) -> ASRResult:
        # Tu código aquí
        return ASRResult(tokens=["k", "a"], text="ka")
```

### Registro

```toml
# pyproject.toml
[project.entry-points."pronunciapa.plugins"]
"asr.my_backend" = "my_package:MyIPABackend"
```

### Uso

```yaml
# configs/local.yaml
backend:
  name: my_backend
  require_ipa: true  # Valida que produce IPA
```

---

## ✅ Modelos Aceptados

| Modelo | Output | Descarga |
|--------|--------|----------|
| **Allosaurus uni2005** | IPA | `download_models.py` (default) |
| facebook/wav2vec2-xlsr-53-ipa | IPA | `--wav2vec2-ipa-model` + token |
| Custom ONNX IPA | IPA | Manual |

---

## ❌ Modelos NO Recomendados (producen texto)

- `facebook/wav2vec2-large-xlsr-53` (texto multilingüe)
- `jonatasgrosman/wav2vec2-*-spanish` (texto por idioma)
- Vosk (texto ligero)
- Whisper (texto, excelente para transcripción pero no fonética)

**Bypass** (no recomendado):
```yaml
backend:
  name: vosk
  require_ipa: false  # Desactiva validación
```

---

## 🎓 Niveles de Evaluación

### Fonémico (`evaluation_level=phonemic`)
- **Objetivo**: Aprender a hablar, ser entendido
- **Evalúa**: Fonemas `/kasa/`
- **Usuario**: Principiantes, comunicación funcional

### Fonético (`evaluation_level=phonetic`)
- **Objetivo**: Pronunciación técnicamente precisa
- **Evalúa**: Alófonos `[ˈka.sa]`
- **Usuario**: Avanzados, actores, lingüistas

---

## 🏗️ Arquitectura

### Kernel (ipa_core/kernel/)
- Orquesta pipeline
- Valida contratos (`output_type`)
- NO implementa ASR/TextRef

### Plugins
- **ASR**: Audio → IPA (Allosaurus, Wav2Vec2-IPA)
- **TextRef**: Texto → IPA (eSpeak, Epitran)
- **LLM**: Ejercicios/feedback (TinyLlama, Phi) — **NO ASR**
- **Language Packs**: Inventarios fonéticos, reglas

---

## 🧪 Validar Cambios

```bash
# Tests
python scripts/tests/test_download_models_policy.py
python scripts/tests/test_plugin_output_types.py

# Help
python scripts/download_models.py --help

# Verificar backend (si allosaurus instalado)
python -m ipa_core.interfaces.cli transcribe --audio test.wav --lang es
```

---

## 📚 Documentación Completa

- **README.md**: Arquitectura y uso general
- **PLUGINS.md**: Desarrollo de plugins, entry points
- **conductor/model-policy.md**: Política completa (8 secciones)
- **conductor/IMPLEMENTATION_SUMMARY.md**: Resumen de cambios

---

## 💡 TinyLlama/Phi: ¿Para qué?

**NO son para ASR**. Se usan para:

1. **Generar ejercicios personalizados**
   ```python
   llm.generate("Crea 5 frases con /θ/ para practicar")
   ```

2. **Feedback pedagógico**
   ```python
   error_report = comparator.compare(observed, target)
   llm.generate(f"Explica estos errores: {error_report}")
   ```

---

## 🚨 Error Común

```
ValueError: Backend ASR 'wav2vec2' produce 'text', no IPA.
```

**Solución**:
1. Usa `backend.name: allosaurus` (recomendado)
2. Usa modelo IPA: `--wav2vec2-ipa-model facebook/wav2vec2-xlsr-53-ipa`
3. O desactiva: `require_ipa: false` (pierde precisión)

---

## 📞 Contacto

Política implementada: 19 de enero de 2026  
Documentación: `/conductor/model-policy.md`
