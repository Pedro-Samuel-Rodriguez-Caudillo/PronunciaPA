# Backends ASR

Paquete con implementaciones que convierten audio a secuencias IPA.

## Estructura
- base.ASRBackend: clase abstracta con el contrato transcribe_ipa.
- null_backend.NullASRBackend: stub que devuelve una cadena fija para pruebas.
- whisper_ipa.WhisperIPABackend: plantilla para integrar un modelo Whisper orientado a IPA.

## Arquitectura de referencia
- Emplear una CNN (pre-entrenada o a entrenar) para extraer embeddings acusticos robustos del audio crudo.
- Encapsular la CNN en el backend de forma que pueda cambiarse el checkpoint sin tocar el kernel.
- Normalizar la salida antes de mapearla a simbolos IPA para mantener consistencia con los comparadores.

## Como crear un backend
1. Heredar de ASRBackend y definir el atributo name unico.
2. Implementar transcribe_ipa(audio_path) retornando una cadena IPA normalizada.
3. Registrar la clase como entry point en pyproject.toml bajo el grupo ipa_core.backends.asr.

## Consideraciones tecnicas
- Los backends deben encargarse de la carga del modelo y normalizacion a IPA.
- Se recomienda devolver solo simbolos IPA (sin espacios innecesarios) para facilitar la comparacion.
- Manejar errores de IO y levantar excepciones claras cuando el audio no pueda procesarse.

## Pruebas sugeridas
- Use audios cortos y deterministas (tone sweep, voz sintetica) para validar la salida.
- Combine con Kernel para pruebas end-to-end y verificar interoperabilidad con textref y comparadores.
