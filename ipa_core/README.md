# ipa_core

Microkernel para evaluacion prosodica basado en conversion a IPA y comparacion.

## Componentes internos
- kernel.Kernel: orquestador que conecta backends ASR, convertidores de texto y comparadores.
- plugins: utilidades para descubrir entry points de los plugins registrados.
- api: interfaz CLI construida con Typer (ver carpeta dedicada).
- backends: implementaciones ASR audio -> IPA.
- textref: convertidores texto -> IPA.
- compare: calculo de PER y detalle de operaciones entre secuencias IPA.

## Flujo general
1. El CLI u otra interfaz instancia Kernel con nombres de plugins.
2. El backend ASR transcribe el audio en IPA.
3. El textref convierte la frase de referencia a IPA.
4. El comparador calcula la metrica y operaciones para evaluar coincidencia.

## Plugin system
Los plugins se resuelven mediante importlib.metadata.entry_points. Cada clase debe registrarse en pyproject.toml para estar disponible en runtime.

## Estado actual
- Existen stubs (null, noop) que permiten probar el flujo sin dependencias pesadas.
- Falta implementar la logica real de ASR y G2P.
- Se requiere definir entry points reales y pruebas automatizadas.
