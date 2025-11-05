"""Core del microkernel: orquesta puertos y pipeline.

Estado: Implementación pendiente (define contratos y conexiones entre módulos).

TODO
----
- Definir ciclo de vida básico: inicializar y cerrar recursos de plugins.
- Especificar reglas de concurrencia si el `Kernel` se usa en hilos.
- Decidir si el `Kernel` actuará como Mediator para eventos entre componentes.
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
    pre: Preprocessor  # Preprocesa audio y normaliza tokens.
    asr: ASRBackend  # Reconoce el habla y produce tokens IPA.
    textref: TextRefProvider  # Convierte texto de referencia a tokens IPA.
    comp: Comparator  # Compara secuencias y calcula métricas.

    def run(
        self,
        *,
        audio: AudioInput,
        text: str,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
    ) -> CompareResult:
        """Ejecutar el pipeline completo para audio y texto de referencia.

        Explicación
        -----------
        - El audio se preprocesa (formato/canales) y pasa al ASR.
        - El texto se convierte a IPA y se normaliza como tokens.
        - Se comparan ambas secuencias para obtener métricas.
        """
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
    # Resolver cada componente a partir de nombres en el archivo de configuración.
    pre = registry.resolve_preprocessor(
        cfg.get("preprocessor", {}).get("name", "default"),
        cfg.get("preprocessor", {}).get("params", {}),
    )  # type: ignore[arg-type]
    asr = registry.resolve_asr(cfg["backend"]["name"], cfg["backend"].get("params", {}))
    textref = registry.resolve_textref(cfg["textref"]["name"], cfg["textref"].get("params", {}))
    comp = registry.resolve_comparator(cfg["comparator"]["name"], cfg["comparator"].get("params", {}))
    return Kernel(pre=pre, asr=asr, textref=textref, comp=comp)
