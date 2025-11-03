# TODO - backends

- [ ] Implementar WhisperIPABackend cargando el modelo HF y normalizando a IPA.
- [ ] Integrar una CNN (pre-entrenada o propia) para la extraccion de embeddings acusticos previos a la decodificacion.
- [ ] Permitir configuracion de dispositivo (cpu/gpu) y parametros de inferencia.
- [ ] Agregar manejo de errores para archivos de audio inexistentes o invalidos.
- [ ] Documentar formato de salida esperado del backend (tokenizacion IPA, normalizacion, etc.).
- [ ] Crear pruebas unitarias usando fixtures de audio sintetico.

## Módulos propuestos

- ipa_core/backends/whisper_ipa.py
  - Carga de modelo (device, dtype), resampleo y decodificación a IPA.
- ipa_core/backends/audio_io.py
  - Lectura de WAV/MP3, normalización de formato, metadatos.
- ipa_core/backends/vad.py
  - Recorte opcional por VAD para mejorar SNR.

## Contrato ASRBackend

```python
from typing import Optional

class ASRBackend(Protocol):
    def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult: ...

# Parámetros mínimos esperados (params)
ASRParams = {
  "device": "cpu",   # cpu|cuda
  "chunk_sec": 30.0,  # segmentación
}
```

## Salida esperada

- `ASRResult.tokens`: lista de tokens IPA normalizados.
- `ASRResult.raw_text`: texto bruto si aplica.
- `ASRResult.time_stamps`: por token/segmento si el backend lo soporta.
