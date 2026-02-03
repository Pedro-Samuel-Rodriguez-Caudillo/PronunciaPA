"""Core del microkernel: orquesta puertos y pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from ipa_core.config.schema import AppConfig
from ipa_core.packs.loader import load_language_pack, load_model_pack, resolve_manifest_path
from ipa_core.packs.schema import LanguagePack, ModelPack, TTSConfig
from ipa_core.pipeline.runner import run_pipeline
from ipa_core.plugins import registry
from ipa_core.ports.asr import ASRBackend
from ipa_core.ports.compare import Comparator
from ipa_core.ports.preprocess import Preprocessor
from ipa_core.ports.textref import TextRefProvider
from ipa_core.ports.tts import TTSProvider
from ipa_core.ports.llm import LLMAdapter
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
    llm: Optional[LLMAdapter] = None
    model_pack: Optional[ModelPack] = None
    model_pack_dir: Optional[Path] = None

    async def setup(self) -> None:
        """Inicializar todos los componentes."""
        await self.pre.setup()
        await self.asr.setup()
        await self.textref.setup()
        await self.comp.setup()
        if self.tts:
            await self.tts.setup()
        if self.llm:
            await self.llm.setup()

    async def teardown(self) -> None:
        """Limpiar todos los componentes."""
        if self.tts:
            await self.tts.teardown()
        if self.llm:
            await self.llm.teardown()
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
    """Crea un `Kernel` resolviendo plugins definidos en la configuración.
    
    Valida que el backend ASR seleccionado produzca IPA si require_ipa=True.
    Usa strict_mode de la config para determinar comportamiento ante errores.
    """
    strict = cfg.strict_mode
    pre = registry.resolve_preprocessor(cfg.preprocessor.name, cfg.preprocessor.params, strict_mode=strict)
    asr = registry.resolve_asr(cfg.backend.name, cfg.backend.params, strict_mode=strict)
    textref = registry.resolve_textref(cfg.textref.name, cfg.textref.params, strict_mode=strict)
    comp = registry.resolve_comparator(cfg.comparator.name, cfg.comparator.params, strict_mode=strict)
    
    # Validar que ASR produce IPA si es requerido
    require_ipa = cfg.backend.params.get("require_ipa", True)  # Por defecto True
    if require_ipa:
        output_type = getattr(asr, "output_type", "none")
        if output_type != "ipa":
            raise ValueError(
                f"❌ Backend ASR '{cfg.backend.name}' produce '{output_type}', no IPA.\n"
                f"PronunciaPA requiere backends que produzcan IPA directo para análisis fonético.\n"
                f"\n"
                f"Opciones:\n"
                f"1. Usa 'allosaurus' (recomendado): ASR → IPA universal\n"
                f"2. Usa un modelo Wav2Vec2 IPA (ej: facebook/wav2vec2-large-xlsr-53-ipa)\n"
                f"3. Desactiva la validación (no recomendado): añade 'require_ipa: false' en config\n"
                f"\n"
                f"Backends texto (como Vosk, Wav2Vec2-texto) pierden información de alófonos."
            )
    
    language_pack = _load_language_pack(cfg)
    model_pack, model_pack_dir = _load_model_pack(cfg)
    tts = _resolve_tts(cfg, language_pack, strict_mode=strict)
    llm = _resolve_llm(cfg, model_pack, model_pack_dir, strict_mode=strict)
    return Kernel(
        pre=pre,
        asr=asr,
        textref=textref,
        comp=comp,
        tts=tts,
        language_pack=language_pack,
        llm=llm,
        model_pack=model_pack,
        model_pack_dir=model_pack_dir,
    )


def _load_language_pack(cfg: AppConfig) -> Optional[LanguagePack]:
    if not cfg.language_pack:
        return None
    return load_language_pack(cfg.language_pack)


def _load_model_pack(cfg: AppConfig) -> tuple[Optional[ModelPack], Optional[Path]]:
    if not cfg.model_pack:
        return None, None
    manifest_path = resolve_manifest_path(cfg.model_pack)
    return load_model_pack(manifest_path), manifest_path.parent


def _resolve_tts(cfg: AppConfig, language_pack: Optional[LanguagePack], *, strict_mode: bool = False) -> Optional[TTSProvider]:
    if cfg.tts is None:
        return None
    name = (cfg.tts.name or "default").lower()
    params = dict(cfg.tts.params or {})
    if language_pack and language_pack.tts:
        name, params = _merge_pack_tts(name, params, language_pack.tts)
    return registry.resolve_tts(name, params, strict_mode=strict_mode)


def _resolve_llm(
    cfg: AppConfig,
    model_pack: Optional[ModelPack],
    model_pack_dir: Optional[Path],
    *,
    strict_mode: bool = False,
) -> Optional[LLMAdapter]:
    if not model_pack:
        return None
    runtime_kind = (model_pack.runtime.kind or "").lower()
    name = (cfg.llm.name or "auto").lower()
    if name == "auto":
        name = runtime_kind
    name = _normalize_llm_name(name)
    params = dict(model_pack.runtime.params or {})
    params.update(model_pack.params or {})
    params.update(cfg.llm.params or {})
    if model_pack_dir:
        params["model_pack_dir"] = str(model_pack_dir)
    if "prompt_path" not in params and model_pack.prompt:
        params["prompt_path"] = str(model_pack.prompt.resolve_path(model_pack_dir or Path(".")))
    if "output_schema_path" not in params and model_pack.output_schema:
        params["output_schema_path"] = str(model_pack.output_schema.resolve_path(model_pack_dir or Path(".")))
    return registry.resolve_llm(name, params, strict_mode=strict_mode)


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


def _normalize_llm_name(name: str) -> str:
    if name in ("llama.cpp", "llama-cpp", "llamacpp"):
        return "llama_cpp"
    return name
