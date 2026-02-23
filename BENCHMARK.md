# Benchmark TTS Round-trip

Mide la calidad del pipeline ASR generando audio con TTS, reconociéndolo con
Allosaurus y comparando el resultado contra la referencia de eSpeak.

```
eSpeak TTS("hola") → audio.wav
       ↓
Allosaurus ASR     → ["o", "l", "a"]   (hipótesis)
eSpeak TextRef     → ["o", "l", "a"]   (referencia)
       ↓
PER = 0.0  →  Score = 100
```

## Instalación rápida

```bash
# Dependencias mínimas (stub mode, sin modelos)
pip install -e '.[dev]'

# Dependencias completas (Allosaurus + eSpeak)
pip install -e '.[dev,asr,speech]'

# eSpeak-NG (para TTS y TextRef)
sudo apt install espeak-ng          # Ubuntu/Debian
brew install espeak-ng              # macOS
```

## Cómo ejecutar

### 1. Prueba rápida (sin modelos, solo verifica el pipeline)

```bash
PRONUNCIAPA_ASR=stub python scripts/benchmark_tts_roundtrip.py --lang es --stub
```

Un PER > 0.5 en stub mode es normal y esperado (el stub genera tokens aleatorios).
Lo importante es que el script termina sin errores.

### 2. Benchmark real en español

```bash
python scripts/benchmark_tts_roundtrip.py --lang es
```

### 3. Inglés con CMU Dict

```bash
# Instalar NLTK + descargar el corpus
pip install nltk
python -c "import nltk; nltk.download('cmudict')"

python scripts/benchmark_tts_roundtrip.py --lang en --textref cmudict
```

### 4. Guardar resultados para comparar regresiones

```bash
# Baseline antes de cambios
python scripts/benchmark_tts_roundtrip.py --lang es --output results/baseline_es.json

# Después de cambios
python scripts/benchmark_tts_roundtrip.py --lang es --output results/after_change_es.json
```

### 5. Ver tokens por palabra (diagnóstico)

```bash
python scripts/benchmark_tts_roundtrip.py --lang es --words 10 --verbose
```

Ejemplo de salida con `--verbose`:
```
  hola               PER=0.000  |████████████████████|
    ref: o l a
    hyp: o l a
  pronunciar         PER=0.111  |██████████████████  |
    ref: p ɾ o n u n θ j a ɾ
    hyp: p ɾ o n u n s j a ɾ
```

## Interpretación de resultados

| PER promedio | Calidad |
|---|---|
| < 0.10 | Excelente — el sistema es muy preciso con audio limpio |
| 0.10–0.20 | Bueno — discrepancias menores (alófonos, variantes) |
| 0.20–0.35 | Aceptable — revisar postprocesamiento por idioma |
| > 0.35 | Problema — investigar pipeline, inventario fonético o normalización |

## Diagnóstico de problemas comunes

### PER alto para palabras cortas
- **Causa**: Audio TTS < 700 ms, Allosaurus produce tokens incorrectos
- **Fix**: Ya incluido — `AllosaurusBackend._pad_audio_if_short()` añade 150 ms de silencio

### Discrepancia sistemática (p.ej. "θ" vs "s" en español)
- **Causa**: eSpeak genera [θ] (castellano), Allosaurus reconoce [s] (latinoam.)
- **Fix**: Especificar dialecto con `--lang es-419` o configurar `PRONUNCIAPA_TEXTREF_DIALECT`

### Palabras OOV (Out of Vocabulary) en inglés con CMU Dict
- El log mostrará `oov_words: [...]` en los metadatos
- El fallback es eSpeak; si eSpeak tampoco está disponible, se usan grafemas
- Puedes añadir palabras al léxico del LanguagePack

## Automatizar en CI

```yaml
# .github/workflows/benchmark.yml
- name: Run benchmark (stub mode)
  run: |
    PRONUNCIAPA_ASR=stub python scripts/benchmark_tts_roundtrip.py \
      --lang es --stub --output ci_results.json
```

En stub mode el PER es siempre alto (esperado), pero el script verifica que
el pipeline entero funciona sin errores de importación o crashes.
