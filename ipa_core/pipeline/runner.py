"""Ejecución del pipeline de alto nivel.

Descripción
-----------
Define el contrato del orquestador de pasos del pipeline.

Estado: Implementación pendiente (expone entradas y salidas del proceso).

Patrones de diseño
------------------
- Template Method: secuencia estable de pasos con puntos de extensión.
- Observer: hooks opcionales de progreso/telemetría (a definir).

TODO
----
- Definir una interfaz de `hooks` para inicio/fin de paso, métricas y errores.
- Acordar manejo de `lang=None` (propagar desde configuración o requerirlo).
- Asegurar inmutabilidad de `AudioInput` y de tokens a lo largo del pipeline.
"""
from __future__ import annotations

from typing import Optional

from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import AudioInput, CompareResult, CompareWeights


def run_pipeline(
    pre: Preprocessor,
    asr: ASRBackend,
    textref: TextRefProvider,
    comp: Comparator,
    *,
    audio: AudioInput,
    text: str,
    lang: Optional[str] = None,
    weights: Optional[CompareWeights] = None,
) -> CompareResult:
    """Orquestar preproceso -> ASR -> TextRef -> Comparación.

    Nota: Implementación pendiente. Esta función solo describe entradas y salidas.
    """
    raise NotImplementedError("run_pipeline está sin implementar (contrato únicamente)")
