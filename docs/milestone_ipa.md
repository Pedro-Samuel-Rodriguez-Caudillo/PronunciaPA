# Milestone: Reconocer audio y transcribir a IPA (MVP)

Objetivo
--------
Construir el flujo mínimo que reciba un archivo de audio y produzca una
secuencia de tokens IPA. No incluye comparación ni UI.

Resultados esperados
--------------------
- Recibir `AudioInput` válido (ruta, SR, canales) y validarlo.
- Ejecutar un backend ASR que devuelva tokens IPA (puede apoyarse en una
  librería existente con modelo pequeño).
- Normalizar tokens con reglas simples y documentadas.
- Entregar la transcripción IPA como lista de tokens o cadena unida.

Fases sugeridas
------------------------------------
1) Preprocessor básico (Chain/Template sencillo)
   - Aceptar WAV mono 16kHz. Si el audio no es mono/16k, registrar un TODO y
     continuar (o fallar con mensaje claro).
   - Normalizar tokens: recortar espacios, bajar a minúsculas, mapear símbolos
     equivalentes sencillos.

2) ASR mínimo (Strategy)
   - Implementar un adaptador a un motor existente que produzca texto.
   - Añadir un mapeo texto→IPA simple (placeholder) o un G2P accesible.
   - Devolver `ASRResult` con `tokens` y `meta` (modelo, versión).

3) TextRefProvider trivial (Strategy)
   - Añadir función `to_ipa(text, lang)` que use el mismo mapeo que el ASR.
   - Esto permite validar coherencia cuando más adelante se compare.

4) Integración con Kernel (Mediator ligero)
   - Conectar `Preprocessor` y `ASRBackend` y exponer `Kernel.run(audio, text)`
     devolviendo la transcripción de hipótesis (sin comparar).

5) CLI mínima
   - `ipa transcribe --audio PATH --lang es` ⇒ imprime tokens IPA o una cadena.

6) Pruebas de contrato
   - Verificar que `Kernel.run` no rompe el contrato.
   - Asegurar que los tipos (`AudioInput`, `ASRResult`) tienen las claves esperadas.

Criterios de finalización
-------------------------
- Se puede ejecutar la CLI con un WAV 16kHz mono y obtener una salida IPA.
- Documentación actualizada con limitaciones y pasos siguientes.
- Código organizado por patrones sencillos (Strategy/Chain/Template) sin
  complejidad innecesaria.

Pasos siguientes (no bloqueantes)
---------------------------------
- Soporte de MP3/OGG con conversión a WAV 16kHz.
- Caché de G2P para frases repetidas.
- Métricas simples de rendimiento (log de tiempos por fase).

