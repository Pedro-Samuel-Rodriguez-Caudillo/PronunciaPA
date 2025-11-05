"""Core del microkernel: orquesta puertos y pipeline.

Estado: Implementación pendiente (define contratos y conexiones entre módulos).

TODO (Issue #18)
----------------
- Definir ciclo de vida de recursos (init/shutdown) para cada plugin.
- Especificar reglas de concurrencia/seguridad de hilos del `Kernel`.
- Incorporar Mediator explícito si el `Kernel` debe coordinar eventos entre puertos.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ipa_core.config.schema import AppConfig
from ipa_core.pipeline.runner import run_pipeline
from ipa_core.plugins import registry
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.types import AudioInput, CompareResult, CompareWeights


@dataclass
class Kernel:
    pre: Preprocessor
    asr: ASRBackend
    textref: TextRefProvider
    comp: Comparator

    def run(
        self,
        *,
        audio: AudioInput,
        text: str,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
    ) -> CompareResult:
        """Ejecuta el pipeline completo para audio+texto."""
        return run_pipeline(
            self.pre,
            self.asr,
            self.textref,
            self.comp,
            audio=audio,
            text=text,
            lang=lang,
            weights=weights,
        )


def create_kernel(cfg: AppConfig) -> Kernel:
    """Crea un `Kernel` resolviendo plugins definidos en la configuración.

    Implementación de resolución delegada a `plugins.registry`.
    """
    pre = registry.resolve_preprocessor(cfg.get("preprocessor", {}).get("name", "default"), cfg.get("preprocessor", {}).get("params", {}))  # type: ignore[arg-type]
    asr = registry.resolve_asr(cfg["backend"]["name"], cfg["backend"].get("params", {}))
    textref = registry.resolve_textref(cfg["textref"]["name"], cfg["textref"].get("params", {}))
    comp = registry.resolve_comparator(cfg["comparator"]["name"], cfg["comparator"].get("params", {}))
    return Kernel(pre=pre, asr=asr, textref=textref, comp=comp)
