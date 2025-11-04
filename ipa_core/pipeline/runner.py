"""Ejecución del pipeline de alto nivel.

Descripción
-----------
Define el contrato del orquestador de pasos del pipeline. No contiene
lógica; únicamente explicita entradas y salidas.

Patrones de diseño
------------------
- Template Method: secuencia estable de pasos con puntos de extensión.
- Observer: hooks opcionales de progreso/telemetría (a definir).

TODO (Issue #18)
----------------
- Establecer interfaz de `hooks` (inicio/fin de paso, métricas, errores).
- Acordar manejo de `lang=None` (propagar desde config u opcional del backend).
- Determinar inmutabilidad de `AudioInput` y tokens a lo largo del pipeline.
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
    """Orquesta preproceso -> ASR -> TextRef -> Comparación.

    Implementación pendiente: este stub define el contrato y conexiones.
    """
    raise NotImplementedError("run_pipeline está sin implementar (contrato únicamente)")
