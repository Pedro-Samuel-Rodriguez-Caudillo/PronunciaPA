# PronunciaPA

Reconocimiento fonético a IPA con CLI, API HTTP y soporte para Allosaurus.

## Instalación rápida

```bash
# Entorno de desarrollo (FastAPI + pruebas)
pip install -e .[dev]

# Dependencias de audio/ASR (Allosaurus, micrófono, conversión MP3)
pip install -e .[speech]
```

> Si solo quieres usar el stub para pruebas, basta con `pip install -e .[dev]` y exportar `PRONUNCIAPA_ASR=stub`.
> El extra `[speech]` requiere ffmpeg (para MP3) y PortAudio (para `sounddevice`).

## Uso por consola

```bash
# Transcribir un WAV/MP3
pronunciapa transcribe --audio inputs/ejemplo.wav --lang es

# Grabar desde micrófono (3 segundos por defecto)
pronunciapa transcribe --mic --seconds 4 --lang es --json

# Forzar proveedor Text→IPA
pronunciapa transcribe --audio inputs/ejemplo.mp3 --textref epitran
```

El comando usa `TranscriptionService` con Allosaurus (o con el stub si `PRONUNCIAPA_ASR=stub`).  
La salida JSON incluye `ipa`, `tokens` y metadatos básicos del audio.

> Conversión MP3→WAV se realiza vía `pydub`, por lo que necesitas `ffmpeg` en tu PATH.
> Usa `PRONUNCIAPA_TEXTREF=epitran` para habilitar el conversor fonético avanzado (requiere el extra `[speech]`).

### Variables de entorno útiles

- `PRONUNCIAPA_ASR` = `allosaurus` | `stub`
- `PRONUNCIAPA_TEXTREF` = `grapheme` | `epitran`

Ambas opciones también están disponibles desde la CLI (`--textref`) y podrán configurarse desde el frontend.

## API HTTP `/pronunciapa/transcribe`

Levanta el servidor con:

```bash
uvicorn ipa_core.api.http:get_app --reload --port 8000
```

Envío de archivos:

```bash
curl -X POST http://localhost:8000/pronunciapa/transcribe \
  -F "lang=es" \
  -F "audio=@inputs/ejemplo.wav"
```

Streaming en vivo (enviar bytes crudos):

```bash
curl -X POST http://localhost:8000/pronunciapa/transcribe \
  -H "Content-Type: application/octet-stream" \
  --data-binary @inputs/ejemplo.wav
```

La respuesta es JSON con tokens IPA, texto unido, idioma y metadatos del backend.

Respuesta tipo:

```json
{
  "ipa": "o l a",
  "tokens": ["o", "l", "a"],
  "lang": "es",
  "audio": {"path": "inputs/rec.wav", "sample_rate": 16000, "channels": 1},
  "meta": {"backend": "allosaurusasr", "tokens": 3}
}
```

## Métricas y comparación

- El microkernel utiliza un comparador de Levenshtein para calcular el Phone Error Rate (PER).
- `run_pipeline` normaliza audio/tokens, obtiene la predicción y devuelve alineaciones (`ops`, `alignment`) listas para dashboards o reportes.
- Cuando integres el frontend, puedes usar estas métricas para resaltar fonemas acertados o erróneos.

## Pruebas

Todos los tests usan el backend stub:

```bash
PRONUNCIAPA_ASR=stub PYTHONPATH=. pytest \
  ipa_core/services/tests/test_transcription_service.py \
  ipa_core/api/tests/test_http_transcription.py \
  scripts/tests/test_cli_transcribe_stub.py

# Tests existentes del preprocesador
PYTHONPATH=. pytest scripts/tests/test_preprocessor_basic.py
```

## Estructura principal

- `ipa_core/` (núcleo, servicios y plugins)
- `config/` (YAML del kernel)
- `scripts/` (herramientas de prueba manual)
- `frontend/` (UI en Vite/Tailwind)
- `docs/` (backlog, milestones y acuerdos de diseño)

Arquitectura (mermaid)
----------------------

```mermaid
flowchart LR
    subgraph ipa_core[ipa_core]
        K[Kernel] --> PPR[Preprocessor]
        K --> ASR[ASRBackend]
        K --> TR[TextRefProvider]
        K --> CMP[Comparator]
        subgraph ports[ports]
            PPR
            ASR
            TR
            CMP
        end
        subgraph pipeline[pipeline]
            RUN[runner.run_pipeline]
        end
        subgraph config[config]
            CFG[loader/schema]
        end
        subgraph plugins[plugins]
            REG[registry]
            DISC[discovery]
        end
    end

    CLI[CLI] --> K
    API[(HTTP API)] --> K
    CFG --> K
    REG --> K
    RUN --> K

    AIN[(AudioInput)] --> ASR
    TXT[(Text)] --> TR
    ASR --> CMP
    TR --> CMP
    CMP --> OUT[(CompareResult)]
```
