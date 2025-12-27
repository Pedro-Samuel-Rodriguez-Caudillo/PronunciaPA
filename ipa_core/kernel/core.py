"""Core del microkernel: orquesta puertos y pipeline.
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
    """Coordina los componentes principales del sistema."""

    pre: Preprocessor
    asr: ASRBackend
    textref: TextRefProvider
    comp: Comparator

    async def setup(self) -> None:
        """Inicializar todos los componentes."""
        await self.pre.setup()
        await self.asr.setup()
        await self.textref.setup()
        await self.comp.setup()

    async def teardown(self) -> None:
        """Limpiar todos los componentes."""
        await self.comp.teardown()
        await self.textref.teardown()
        await self.asr.teardown()
        await self.pre.teardown()

    async def run(
        self,
        *,
        audio: AudioInput,
        text: str,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
    ) -> CompareResult:
        """Ejecutar el pipeline completo (Asíncrono)."""
        return await run_pipeline(
            pre=self.pre,
            asr=self.asr,
            textref=self.textref,
            comp=self.comp,
            audio=audio,
            text=text,
            lang=lang,
            weights=weights,
        )


def create_kernel(cfg: AppConfig) -> Kernel:
    """Crea un `Kernel` resolviendo plugins definidos en la configuración."""
    pre = registry.resolve_preprocessor(cfg.preprocessor.name, cfg.preprocessor.params)
    asr = registry.resolve_asr(cfg.backend.name, cfg.backend.params)
    textref = registry.resolve_textref(cfg.textref.name, cfg.textref.params)
    comp = registry.resolve_comparator(cfg.comparator.name, cfg.comparator.params)
    return Kernel(pre=pre, asr=asr, textref=textref, comp=comp)
