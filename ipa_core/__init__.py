"""ipa_core package

Resumen
-------
Este paquete define contratos y puntos de integración del microkernel.
No incluye lógica; únicamente define tipos, puertos e interfaces de
conexión.

TODO (Issue #18)
----------------
- Garantizar que todos los contratos se mantengan estables y versionados.
- Establecer políticas de compatibilidad semántica (SemVer) para puertos.
- Documentar mapa de dependencias y responsabilidades por submódulo.
- Evaluar incorporar un subsistema de eventos (Observer) para métricas y
  trazas sin acoplar el `Kernel`.
"""

__all__ = [
    "types",
]
