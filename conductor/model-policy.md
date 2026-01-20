# Política de Modelos - PronunciaPA

## Objetivo del Proyecto

PronunciaPA es un **microkernel de análisis fonético** diseñado para ayudar a usuarios a mejorar su pronunciación mediante evaluación precisa en dos niveles:

### Niveles de Evaluación

| Nivel | Objetivo | Qué evalúa | Caso de uso |
|-------|----------|------------|-------------|
| **Fonémico** (`evaluation_level=phonemic`) | Aprender a hablar y ser entendido | Fonemas `/kasa/` | Principiantes, comunicación funcional |
| **Fonético** (`evaluation_level=phonetic`) | Pronunciación técnicamente precisa | Alófonos `[ˈka.sa]` | Avanzados, actores, lingüistas |

### Pipeline Requerido

```
Audio del usuario ──► ASR (IPA directo) ──► [ˈka.sa]
                                              │
                                              ▼
                                        COMPARADOR
                                              ▲
                                              │
Texto objetivo ──► TextRef (G2P) ──► /kasa/ (fonémico)
                                  └─► [ˈka.sa] (fonético, si hay derive)
```

**Requisito crítico**: El ASR debe producir **IPA directo** desde audio para capturar alófonos reales. **NO usar** modelos que produzcan texto (Wav2Vec2 texto, Vosk, Whisper), ya que pierden información fonética.

---

## Arquitectura: Kernel vs Plugins

### Kernel (ipa_core/kernel/core.py)

**Responsabilidades**:
- Orquestar el pipeline (Preprocessor → ASR → TextRef → Comparator)
- Inicializar y teardown de componentes
- **Validar contratos**: ASR debe declarar `output_type="ipa"` si `require_ipa=True`
- Lanzar errores instructivos si se selecciona un backend incompatible

**No hace**:
- No implementa ASR, TextRef, etc. (delega a plugins)
- No decide qué plugin usar (lee configuración)

### Plugins

**Definición**: Componentes externos que implementan interfaces del kernel.

| Tipo | Interface | Rol | Ejemplos |
|------|-----------|-----|----------|
| **ASR** | `ASRBackend` | Audio → IPA | Allosaurus, Wav2Vec2-IPA |
| **TextRef** | `TextRefProvider` | Texto → IPA | eSpeak, Epitran |
| **Comparator** | `Comparator` | IPA vs IPA → Error report | Levenshtein con pesos |
| **LLM** | `LLMAdapter` | Ejercicios y feedback | TinyLlama, Phi-3 |
| **Language Pack** | `LanguagePack` | Inventario + reglas fonológicas | es-mx, en-us |
| **TTS** | `TTSProvider` | Texto → Audio | Piper, System TTS |

**Atributo obligatorio para ASR plugins**:
```python
output_type: Literal["ipa", "text", "none"] = "ipa"
```

---

## Modelos Aceptados

### 1. ASR → IPA (Obligatorios)

| Modelo | Output | Idiomas | Estado | Notas |
|--------|--------|---------|--------|-------|
| **Allosaurus uni2005** | IPA | 2000+ | ✅ **Default** | Universal, no requiere ajustes |
| facebook/wav2vec2-large-xlsr-53-ipa | IPA | Multi | ✅ Recomendado | Gated, requiere token HF |
| Modelos ONNX custom IPA | IPA | Varía | ✅ Aceptado | Si entrenados para IPA |

### 2. TextRef → IPA (Obligatorios)

| Herramienta | Output | Idiomas | Estado |
|-------------|--------|---------|--------|
| **eSpeak-ng** | IPA | 100+ | ✅ **Default** |
| Epitran | IPA | ~70 | ✅ Recomendado |

### 3. LLM (Opcionales, NO para ASR)

| Modelo | Uso | Descarga | Estado |
|--------|-----|----------|--------|
| **TinyLlama 1.1B** | Ejercicios, feedback | Ollama | ✅ Opcional |
| **Phi-3 mini** | Ejercicios, feedback | Ollama | ✅ Opcional |

**⚠️ IMPORTANTE**: TinyLlama y Phi NO se usan para ASR. Solo para:
1. Generar ejercicios personalizados (drill generation)
2. Retroalimentación pedagógica textual (feedback)

---

## Modelos NO Aceptados (Default)

Estos modelos producen **texto**, no IPA. Pierden información de alófonos:

| Modelo | Output | Problema |
|--------|--------|----------|
| facebook/wav2vec2-large-xlsr-53 | Texto | No captura alófonos reales |
| jonatasgrosman/wav2vec2-*-spanish/english/... | Texto | Requiere G2P posterior |
| Vosk | Texto | Ligero pero sin IPA |
| Whisper | Texto | Excelente para transcripción, no fonética |

**Ejemplo del problema**:
- Usuario dice: `[ˈka.θa]` (español peninsular con /θ/)
- ASR texto devuelve: "casa"
- G2P produce: `/kasa/` — **¡perdiste el [θ]!**

**Solución**: Usar Allosaurus que captura `[ˈka.θa]` directamente.

---

## Criterios de Aceptación de Nuevos Modelos

Para que un modelo ASR sea aceptado en PronunciaPA:

| Criterio | Descripción |
|----------|-------------|
| ✅ **Output IPA** | Debe producir IPA/fonemas, NO texto |
| ✅ **Multilingüe** | Soportar múltiples idiomas con un solo modelo |
| ✅ **Sin postproceso** | No requerir G2P manual posterior |
| ✅ **Offline** | Ejecutable sin internet tras descarga |
| ✅ **Plugin-ready** | Integrarse via `pronunciapa.plugins` entry point |
| ✅ **Declarar output_type** | `output_type = "ipa"` en la clase |

---

## Configuración y Validación

### Configuración del backend

```yaml
# configs/local.yaml
backend:
  name: allosaurus  # o wav2vec2_ipa
  require_ipa: true  # Por defecto True
  params:
    model_name: uni2005
```

### Validación del Kernel

Al crear el kernel, se valida:

```python
# ipa_core/kernel/core.py
if require_ipa and asr.output_type != "ipa":
    raise ValueError(
        f"❌ Backend ASR '{name}' produce '{output_type}', no IPA.\n"
        "Opciones:\n"
        "1. Usa 'allosaurus' (recomendado)\n"
        "2. Usa un modelo Wav2Vec2 IPA (ej: facebook/wav2vec2-large-xlsr-53-ipa)\n"
        "3. Desactiva validación: require_ipa: false (no recomendado)\n"
    )
```

### Bypass (NO recomendado)

Si necesitas usar un backend texto:

```yaml
backend:
  name: vosk  # o wav2vec2 texto
  require_ipa: false  # Desactiva validación
  params:
    model_path: /path/to/vosk/model
```

**Consecuencia**: Pérdida de precisión fonética, no capturará alófonos reales.

---

## Descarga de Modelos

### Comando por defecto (mínimo)

```bash
python scripts/download_models.py
```

Descarga:
- Allosaurus uni2005 (ASR → IPA)
- Verifica eSpeak-ng (G2P)

### Opcionales

```bash
# LLMs para ejercicios/feedback
python scripts/download_models.py --with-llms --with-phi3

# ASR alternativo Wav2Vec2 IPA
export HUGGINGFACEHUB_API_TOKEN=hf_XXXX
python scripts/download_models.py \
  --wav2vec2-ipa-model facebook/wav2vec2-large-xlsr-53-ipa
```

---

## Desarrollo de Plugins ASR

### Template mínimo

```python
from ipa_core.plugins.base import BasePlugin
from ipa_core.ports.asr import ASRBackend, ASRResult
from ipa_core.types import AudioInput

class MyIPABackend(BasePlugin, ASRBackend):
    """Mi backend ASR que produce IPA."""
    
    # OBLIGATORIO: Declarar tipo de salida
    output_type = "ipa"
    
    async def setup(self) -> None:
        # Cargar modelo
        pass
    
    async def transcribe(
        self,
        audio: AudioInput,
        lang: str | None = None,
    ) -> ASRResult:
        # Tu implementación
        # Debe retornar ASRResult con tokens IPA
        return ASRResult(
            tokens=["k", "a", "s", "a"],
            text="kasa",
            confidence=0.95,
        )
    
    async def teardown(self) -> None:
        # Liberar recursos
        pass
```

### Registro en pyproject.toml

```toml
[project.entry-points."pronunciapa.plugins"]
"asr.my_ipa_backend" = "my_package.backend:MyIPABackend"
```

---

## Resumen

| Componente | Tipo | Propósito |
|------------|------|-----------|
| **Kernel** | Core | Orquesta pipeline, valida contratos |
| **Allosaurus** | Plugin ASR | Audio → IPA (default) ✅ |
| **eSpeak/Epitran** | Plugin TextRef | Texto → IPA (default) ✅ |
| **TinyLlama/Phi** | Plugin LLM | Ejercicios/feedback (NO ASR) ✅ |
| **Vosk/Wav2Vec2-texto** | Plugin ASR | Produce texto ⚠️ NO recomendado |
| **Language Packs** | Plugin | Inventarios fonéticos, reglas derive/collapse ✅ |

**Regla de oro**: Si un modelo ASR produce texto en lugar de IPA, NO lo uses por defecto. El propósito del proyecto es análisis fonético preciso, lo cual requiere capturar alófonos reales.
