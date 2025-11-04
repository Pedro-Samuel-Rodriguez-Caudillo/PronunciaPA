"""Orquestación del pipeline (stubs).

Patrones de diseño
------------------
- Template Method: definir la secuencia de pasos del pipeline.
- Mediator (coordinación vía `Kernel`): minimizar acoplamiento entre puertos.

TODO (Issue #18)
----------------
- Definir puntos de extensión (hooks) para instrumentación (Observer).
- Especificar contrato de cancelación/interrupción en ejecuciones largas.
"""
