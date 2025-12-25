"""Core del microkernel: orquesta puertos y pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from ipa_core.config.schema import AppConfig
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

    def run(
        self,
        *,
        audio: AudioInput,
        text: str,
        lang: Optional[str] = None,
        weights: Optional[CompareWeights] = None,
    ) -> CompareResult:
        """Ejecutar el pipeline completo."""
        # TODO: Implementar integración real con run_pipeline
        # Por ahora, un stub que delega a los componentes
        processed_audio = self.pre.process_audio(audio)
        asr_res = self.asr.transcribe(processed_audio, lang=lang)
        ref_tokens = self.textref.to_ipa(text, lang=lang or "es")
        norm_ref = self.pre.normalize_tokens(ref_tokens)
        norm_hyp = self.pre.normalize_tokens(asr_res["tokens"])
        
        return self.comp.compare(norm_ref, norm_hyp, weights=weights)


def create_kernel(cfg: AppConfig) -> Kernel:
    """Crea un `Kernel` resolviendo plugins definidos en la configuración."""
    pre = registry.resolve_preprocessor(cfg.preprocessor.name, cfg.preprocessor.params)
    asr = registry.resolve_asr(cfg.backend.name, cfg.backend.params)
    textref = registry.resolve_textref(cfg.textref.name, cfg.textref.params)
    comp = registry.resolve_comparator(cfg.comparator.name, cfg.comparator.params)
    return Kernel(pre=pre, asr=asr, textref=textref, comp=comp)