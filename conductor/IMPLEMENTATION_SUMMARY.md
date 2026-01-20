# Resumen de Cambios - Política de Modelos PronunciaPA

**Fecha**: 19 de enero de 2026  
**Objetivo**: Establecer política clara de modelos ASR para mantener el propósito del proyecto (análisis fonético IPA directo)

---

## ✅ Cambios Implementados

### 1. **scripts/download_models.py**
- ❌ **Eliminado**: Descarga por defecto de `facebook/wav2vec2-large-xlsr-53` (modelo texto)
- ❌ **Eliminado**: Constante `DEFAULT_W2V2_MODEL`
- ✅ **Añadido**: Flag `--wav2vec2-ipa-model` para descargar modelos IPA opcionales
- ✅ **Renombrado**: `download_wav2vec2()` → `download_wav2vec2_ipa()` con advertencias
- ✅ **Modificado**: `--with-phi3` ahora es `--with-llms` (más claro) + `--with-phi3`
- 📝 **Documentado**: Header con política de modelos y propósito de LLMs

**Comando nuevo**:
```bash
# Default: Solo Allosaurus + eSpeak
python scripts/download_models.py

# Con LLMs para ejercicios
python scripts/download_models.py --with-llms --with-phi3

# Con Wav2Vec2 IPA (gated)
export HUGGINGFACEHUB_API_TOKEN=hf_XXX
python scripts/download_models.py --wav2vec2-ipa-model facebook/wav2vec2-large-xlsr-53-ipa
```

---

### 2. **ipa_core/plugins/base.py**
- ✅ **Añadido**: Atributo `output_type: Literal["ipa", "text", "none"]`
- 📝 **Documentado**: Los plugins ASR deben declarar su tipo de salida

**Cambio**:
```python
class BasePlugin:
    output_type: Literal["ipa", "text", "none"] = "none"
```

---

### 3. **ipa_core/kernel/core.py**
- ✅ **Añadido**: Validación en `create_kernel()` que rechaza backends texto si `require_ipa=True`
- 📝 **Error instructivo**: Mensaje claro con opciones si se selecciona backend incompatible

**Validación**:
```python
if require_ipa and asr.output_type != "ipa":
    raise ValueError(
        f"❌ Backend ASR '{name}' produce '{output_type}', no IPA.\n"
        "Opciones:\n"
        "1. Usa 'allosaurus' (recomendado)\n"
        "2. Usa un modelo Wav2Vec2 IPA\n"
        "3. Desactiva validación: require_ipa: false (no recomendado)\n"
    )
```

---

### 4. **Backends Marcados**

#### **ipa_core/backends/allosaurus_backend.py**
```python
class AllosaurusBackend(BasePlugin):
    output_type = "ipa"  # ✅ Declarado
```

#### **ipa_core/backends/wav2vec2_backend.py**
```python
class Wav2Vec2Backend(BasePlugin, ASRBackend):
    output_type = "text"  # ⚠️ Por defecto texto
    
    def __init__(self, ..., force_ipa: bool = False):
        # Auto-detecta si nombre contiene "ipa" o "phoneme"
        if "ipa" in model_name.lower():
            self.output_type = "ipa"
```

#### **ipa_core/backends/vosk_backend.py**
```python
class VoskBackend(BasePlugin, ASRBackend):
    output_type = "text"  # ⚠️ Produce texto
```

**Advertencias añadidas** en docstrings de Vosk y Wav2Vec2 texto.

---

### 5. **Documentación**

#### **README.md**
- ✅ Nueva sección: "🏗️ Arquitectura: Microkernel + Plugins"
- ✅ Nueva sección: "🎯 Propósito" (fonémico vs fonético)
- ✅ Actualizada: Sección "🔽 Descarga de modelos" con advertencias
- ✅ Añadida: Tabla de modelos NO recomendados

#### **PLUGINS.md**
- ✅ Nueva sección: "Architecture Overview" (Kernel vs Plugins)
- ✅ Nueva sección: "ASR Plugin Requirements (CRITICAL)"
- ✅ Nueva tabla: "Model Acceptance Criteria"
- ✅ Ejemplos de código para declarar `output_type`
- ✅ Explicación: LLM plugins (TinyLlama/Phi) para ejercicios, NO ASR

#### **conductor/model-policy.md** (NUEVO)
- ✅ Documento completo de política (8 secciones):
  1. Objetivo del proyecto (fonémico vs fonético)
  2. Arquitectura (Kernel vs Plugins)
  3. Modelos aceptados
  4. Modelos NO aceptados
  5. Criterios de aceptación
  6. Configuración y validación
  7. Descarga de modelos
  8. Desarrollo de plugins ASR

---

### 6. **Tests**

#### **scripts/tests/test_download_models_policy.py**
- ✅ Test: `--help` muestra flags correctos
- ✅ Test: Wav2Vec2 es opcional (no default)
- ✅ Test: Script se importa y no tiene `DEFAULT_W2V2_MODEL`

#### **scripts/tests/test_plugin_output_types.py**
- ✅ Test: `BasePlugin` tiene `output_type`
- ✅ Test: Backends IPA declaran `output_type="ipa"`
- ✅ Test: Backends texto declaran `output_type="text"`
- ✅ Test: AllosaurusBackend es IPA
- ✅ Test: Wav2Vec2Backend es texto por defecto
- ✅ Test: VoskBackend es texto
- ⚠️ Test: Validación de kernel (requiere pytest)

**Resultados**:
```
✅ All download_models tests passed!
✅ Basic plugin output_type tests passed!
```

---

## 📊 Impacto

### Lo que CAMBIA para usuarios

| Antes | Ahora |
|-------|-------|
| `python scripts/download_models.py` descargaba Wav2Vec2 texto | Solo descarga Allosaurus (IPA) |
| No había validación de output_type | Kernel rechaza backends texto si `require_ipa=True` |
| Documentación ambigua sobre modelos | Política clara en README, PLUGINS.md, model-policy.md |
| TinyLlama/Phi sin explicación de propósito | Claramente documentado: ejercicios/feedback, NO ASR |

### Lo que NO cambia

- ✅ Allosaurus sigue siendo el backend default (IPA)
- ✅ eSpeak/Epitran siguen siendo los TextRef default
- ✅ Vosk y Wav2Vec2 texto siguen disponibles (con advertencias)
- ✅ Usuarios pueden desactivar validación (`require_ipa: false`)

---

## 🎯 Beneficios

1. **Claridad**: Política de modelos explícita y documentada
2. **Protección**: Validación automática previene errores de configuración
3. **Educativo**: Usuarios entienden por qué IPA directo es importante
4. **Extensibilidad**: Template claro para plugins ASR futuros
5. **Mantenibilidad**: Kernel enforcea contratos, fácil identificar backends incompatibles

---

## 🚀 Próximos Pasos

### Opcional (mejoras futuras)
- [ ] Añadir más tests de integración (con mocks de modelos)
- [ ] Crear CLI warning si usuario intenta usar backend texto
- [ ] Desarrollar plugin para `facebook/wav2vec2-large-xlsr-53-ipa` (gated)
- [ ] Añadir soporte para modelos ONNX IPA custom
- [ ] Documentar cómo convertir modelos IPA a ONNX

### Validación recomendada
```bash
# Verificar que download_models funciona
python scripts/download_models.py --help

# Verificar que tests pasan
python scripts/tests/test_download_models_policy.py
python scripts/tests/test_plugin_output_types.py

# Verificar que backend Allosaurus sigue funcionando
# (requiere allosaurus instalado)
python -m ipa_core.interfaces.cli transcribe --audio inputs/ejemplo.wav --lang es
```

---

## 📝 Archivos Modificados

```
✏️  scripts/download_models.py
✏️  ipa_core/plugins/base.py
✏️  ipa_core/kernel/core.py
✏️  ipa_core/backends/allosaurus_backend.py
✏️  ipa_core/backends/wav2vec2_backend.py
✏️  ipa_core/backends/vosk_backend.py
✏️  README.md
✏️  PLUGINS.md
➕  conductor/model-policy.md
➕  scripts/tests/test_download_models_policy.py
➕  scripts/tests/test_plugin_output_types.py
```

**Total**: 8 archivos modificados, 3 archivos creados

---

## ✨ Resumen Ejecutivo

Se implementó una **política de modelos** clara para PronunciaPA:

1. **ASR debe producir IPA directo** (no texto que requiera G2P)
2. **Allosaurus es el default** (universal, 2000+ lenguas)
3. **TinyLlama/Phi son para ejercicios/feedback**, NO para ASR
4. **Kernel valida contratos** automáticamente
5. **Documentación completa** en README, PLUGINS.md, model-policy.md

**Propósito mantenido**: Ayudar a usuarios a mejorar pronunciación mediante análisis fonético preciso (fonémico o fonético según elección del usuario).
