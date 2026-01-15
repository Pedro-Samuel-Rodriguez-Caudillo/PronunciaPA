"""Core del microkernel: orquesta puertos y pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from ipa_core.config.schema import AppConfig
from ipa_core.packs.loader import load_language_pack
from ipa_core.packs.schema import LanguagePack, TTSConfig
from ipa_core.pipeline.runner import run_pipeline
from ipa_core.plugins import registry
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.ports.tts import TTSProvider
from ipa_core.types import AudioInput, CompareResult, CompareWeights


@dataclass
class Kernel:
    """Coordina los componentes principales del sistema."""

    pre: Preprocessor
    asr: ASRBackend
    textref: TextRefProvider
    comp: Comparator
    tts: Optional[TTSProvider] = None
    language_pack: Optional[LanguagePack] = None

    async def setup(self) -> None:
        """Inicializar todos los componentes."""
        await self.pre.setup()
        await self.asr.setup()
        await self.textref.setup()
        await self.comp.setup()
        if self.tts:
            await self.tts.setup()

    async def teardown(self) -> None:
        """Limpiar todos los componentes."""
        if self.tts:
            await self.tts.teardown()
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
    language_pack = _load_language_pack(cfg)
    tts = _resolve_tts(cfg, language_pack)
    return Kernel(
        pre=pre,
        asr=asr,
        textref=textref,
        comp=comp,
        tts=tts,
        language_pack=language_pack,
    )


def _load_language_pack(cfg: AppConfig) -> Optional[LanguagePack]:
    if not cfg.language_pack:
        return None
    return load_language_pack(cfg.language_pack)


def _resolve_tts(cfg: AppConfig, language_pack: Optional[LanguagePack]) -> Optional[TTSProvider]:
    if cfg.tts is None:
        return None
    name = (cfg.tts.name or "default").lower()
    params = dict(cfg.tts.params or {})
    if language_pack and language_pack.tts:
        name, params = _merge_pack_tts(name, params, language_pack.tts)
    return registry.resolve_tts(name, params)


def _merge_pack_tts(name: str, params: dict, pack_tts: TTSConfig) -> Tuple[str, dict]:
    provider = (pack_tts.provider or "").lower()
    pack_params = dict(pack_tts.params or {})
    if pack_tts.voice and "voice" not in pack_params:
        pack_params["voice"] = pack_tts.voice
    if pack_tts.sample_rate and "sample_rate" not in pack_params:
        pack_params["sample_rate"] = pack_tts.sample_rate

    if name in ("default", "adapter"):
        if provider in ("piper", "system"):
            params.setdefault("prefer", provider)
            nested = dict(params.get(provider, {}))
            for key, value in pack_params.items():
                nested.setdefault(key, value)
            params[provider] = nested
        return "default", params

    if provider and provider != name:
        return name, params

    for key, value in pack_params.items():
        params.setdefault(key, value)
    return name, params
