# API (CLI)

CLI basado en Typer que expone el microkernel para pruebas rapidas.

## Comandos disponibles
- plugins: lista los nombres registrados para backends, textref y comparadores.
- run: procesa un audio y texto de referencia para calcular PER usando las implementaciones activas.

## Flujo de ejecucion
1. Construye una instancia Kernel con los plugins solicitados.
2. Convierte el audio a IPA a traves del backend ASR configurado.
3. Normaliza el texto de referencia a IPA mediante el plugin textref.
4. Ejecuta el comparador para obtener metrica PER y operaciones crudas.

## Consideraciones
- Los plugins reales se resuelven mediante entry points de importlib.metadata.
- Actualmente se usan stubs (null y noop) para facilitar pruebas manuales.
- Los mensajes se imprimen en consola, por lo que conviene encapsular formatos adicionales si se integrara con otras apps.

## Como probar
    poetry run ipa-core-cli plugins
    poetry run ipa-core-cli run sample.wav "texto referencia"
Reemplaza sample.wav y la frase por entradas reales.

## Extensiones planeadas
- Agregar un comando record que capture audio desde el microfono y guarde un WAV listo para invocar run.
