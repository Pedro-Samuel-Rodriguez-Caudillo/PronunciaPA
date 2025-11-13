# Guía de Testing - Feature Pipeline Transcribe CLI

## Alcance de la Implementación

Esta rama implementa:
1. Pipeline de transcripción (`ipa_core/pipeline/transcribe.py`)
2. Stub de CLI para el comando `transcribe` (`ipa_core/api/cli.py`)

## Procedimiento de Validación

### Prerequisito: Configurar PYTHONPATH
Todos los comandos deben ejecutarse con el PYTHONPATH correcto:

```powershell
$env:PYTHONPATH="c:\Users\julio\OneDrive\Documentos\GitHub\PronunciaPA"
```

### Prueba 1: Validación de CLI transcribe
Validar que `cli_transcribe` existe y retorna tokens IPA:

```powershell
python scripts/tests/test_cli_transcribe_stub.py
```

**Salida esperada:**
```
cli_transcribe retornó 3 tokens: ['ˈo', 'l', 'a']
Todas las pruebas pasaron correctamente
```

### Prueba 2: Validación del Pipeline completo
Verificar funcionamiento del pipeline con componentes stub:

```powershell
python scripts/tests/test_transcribe_stub.py
```

**Salida esperada:**
```
Normalización: [' A ', 'B', '  ', 'c', 'D  '] -> ['a', 'b', 'c', 'd']
transcribe con tokens: ['ˈo', 'l', 'a']
transcribe con raw_text: ['ˈo', 'l', 'a']
Todas las pruebas del pipeline transcribe pasaron correctamente
```

## Componentes Implementados

### 1. Pipeline `transcribe()`
**Archivo:** `ipa_core/pipeline/transcribe.py`

Flujo:
1. `pre.process_audio(audio)` → procesa el audio
2. `asr.transcribe()` → obtiene tokens o texto raw
3. Si hay tokens: `pre.normalize_tokens()` → salida
4. Si hay raw_text: `textref.to_ipa()` → `pre.normalize_tokens()` → salida

### 2. CLI `cli_transcribe()`
**Archivo:** `ipa_core/api/cli.py`

Modificaciones realizadas:
- Eliminación de `NotImplementedError`
- Retorno de tokens de ejemplo: `["ˈo", "l", "a"]`
- Documentación de flags esperados para implementación futura

### 3. Suite de Pruebas
**Archivos creados:**
- `scripts/tests/test_cli_transcribe_stub.py`: Validación de CLI stub
- `scripts/tests/test_transcribe_stub.py`: Validación de pipeline completo

## Criterios de Éxito

- Pipeline `transcribe` se puede importar y ejecutar sin errores
- `cli_transcribe` existe y no lanza `NotImplementedError`
- Scripts de prueba ejecutan correctamente
- Contratos existentes preservados (ej: `cli_compare`)

## Integración Futura

Pendiente de integración con otras ramas del sprint:
1. Rama ricardo840: `audio_io.py` y `asr_stub.py`
2. Rama Pedro-Samuel: `preprocessor_basic.py`
3. Conexión de componentes reales en `cli_transcribe`

## Referencias Técnicas

- Plan del sprint: `docs/sprints/001-audio-to-ipa/PLAN.md`
- Guía de ramas: `docs/sprints/001-audio-to-ipa/FEATURE_BRANCHES.md`
- Arquitectura: `docs/sprints/001-audio-to-ipa/ARCHITECTURE.md`

## Resolución de Problemas

### Error: `ModuleNotFoundError: No module named 'ipa_core'`
Configurar PYTHONPATH antes de la ejecución:
```powershell
$env:PYTHONPATH="c:\Users\julio\OneDrive\Documentos\GitHub\PronunciaPA"
```

### Advertencia: `Import "pytest" could not be resolved`
Este es un aviso del linter sin impacto funcional. Los tests en `scripts/tests/` utilizan ejecución directa con Python, no requieren pytest.
