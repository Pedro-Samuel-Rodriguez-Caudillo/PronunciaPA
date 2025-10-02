# Backend Whisper-IPA

El backend ``whisper-ipa`` integra el checkpoint público
`neurlang/ipa-whisper-base` disponible en Hugging Face Hub. El modelo está
ajustado para producir símbolos IPA directamente desde audio en castellano e
inglés, cubriendo la etapa E del pipeline.

## Requisitos

1. **Dependencias**: asegúrate de instalar las dependencias opcionales
   indicadas en ``pyproject.toml`` (`torch`, `transformers`).
2. **Token de Hugging Face**: si el modelo requiere autenticación, ejecuta
   `huggingface-cli login` y define `HF_HOME` si deseas controlar la ruta de
   cache. Para repositorios públicos no es necesario el token.
3. **Descarga inicial**: la primera ejecución descargará ~150 MB. Puedes
   precachear manualmente con:

   ```bash
   python - <<'PY'
   from transformers import pipeline
   pipeline("automatic-speech-recognition", model="neurlang/ipa-whisper-base")
   PY
   ```

## Uso

Una vez instalado, el backend queda registrado como plugin ASR. Puede
invocarse desde el CLI para verificar la instalación:

```bash
python -m ipa_core.api.cli plugins list --group asr
```

Para transcribir un archivo directamente desde Python:

```python
from ipa_core.backends.whisper_ipa import WhisperIPABackend

backend = WhisperIPABackend()
ipa = backend.transcribe_ipa("audio.wav")
print(ipa)
```

La clase se encarga de normalizar el audio (mono, 16 kHz) y de solicitar al
pipeline una salida IPA. Si la transcripción es vacía o el archivo no existe,
se lanzará una excepción descriptiva.
