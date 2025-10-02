# Validación del MVP

## Resumen ejecutivo
- Pipeline ejecutado con la configuración `configs/local.yaml` sobre el dataset sample.
- Métrica PER global de 1.00 utilizando el backend `null` y comparador Levenshtein.
- Tiempo de ejecución end-to-end (incluyendo carga y escritura de reportes): **1.01 s** en entorno local (real), **0.57 s** CPU de usuario, **0.60 s** CPU de sistema.
- Todos los tests unitarios pasan (`pytest`).
- No se encontró dataset adicional disponible en el repositorio para validación complementaria.

## Dataset evaluado
| Dataset            | Ítems | Notas |
|--------------------|-------|-------|
| `data/sample`      | 3     | Tono sintético + texto en español. Requiere generar WAV mediante `scripts/generate_sample_dataset.py`.

## Configuración utilizada
- Configuración del kernel: `configs/local.yaml` (backend ASR `null`, TextRef `noop`, comparador `levenshtein`).
- Comando ejecutado:
  ```bash
  python -m ipa_core.api.cli run \
    --config configs/local.yaml \
    --input data/sample/metadata.csv \
    --output outputs/sample_run
  ```

## Resultados de métricas
| Índice | Archivo         | PER | Errores |
|--------|-----------------|-----|---------|
| 1      | `sample_01.wav` | 1.0 | 1 sustitución |
| 2      | `sample_02.wav` | 1.0 | 1 sustitución |
| 3      | `sample_03.wav` | 1.0 | 1 sustitución |

- PER global: **1.00**
- Total de items procesados: **3**
- Items con error: **0** (errores registrados solo en la comparación fonémica)
- Tokens de referencia totales: **3**

## Tiempos de procesamiento
- Comando: `time python -m ipa_core.api.cli run -c configs/local.yaml -i data/sample/metadata.csv -o outputs/sample_run`
- Tiempo real: **1.009 s**
- Tiempo usuario: **0.574 s**
- Tiempo sistema: **0.598 s**

> Nota: los valores corresponden a la ejecución dentro del contenedor de desarrollo, sin aceleración por GPU.

## Testing automatizado
- `pytest` → ✅ 23 tests pasados, 1 skipped.

## Hallazgos y recomendaciones
1. Integrar un backend ASR real (Whisper-IPA) para obtener métricas significativas de PER.
2. Documentar o proporcionar dataset(s) adicionales con habla real para pruebas de regresión.
3. Automatizar la generación de métricas históricas (PER, tiempos) a partir de los reportes JSON.
4. Ampliar el comparador con métricas alternativas (WER, SER) y soportar normalización configurable.
