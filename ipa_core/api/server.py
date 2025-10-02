"""HTTP API para exponer el microkernel a aplicaciones externas."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ipa_core.compare.base import PhonemeStats
from ipa_core.kernel import Kernel, KernelConfig
from ipa_core.plugins import PLUGIN_GROUPS, list_plugins

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(os.getenv("IPA_KERNEL_CONFIG", "config/ipa_kernel.yaml"))


class AnalysisService:
    """Pequeño contenedor que orquesta el kernel y serializa respuestas."""

    def __init__(
        self,
        *,
        kernel: Kernel | None = None,
        config: KernelConfig | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        if kernel is not None:
            self._kernel = kernel
            self.config = kernel.config
            return

        if config is not None:
            self.config = config
        else:
            self.config = self._load_config(config_path)

        self._kernel = Kernel(self.config)

    @staticmethod
    def _load_config(config_path: str | Path | None) -> KernelConfig:
        path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
        try:
            return KernelConfig.from_yaml(path)
        except FileNotFoundError:
            logger.warning("No se encontró %s, usando configuración por defecto", path)
        except Exception as exc:  # pragma: no cover - logging defensivo
            logger.warning("No se pudo cargar la configuración %s: %s", path, exc)
        return KernelConfig()

    @property
    def kernel(self) -> Kernel:
        return self._kernel

    def analyze(self, *, text: str, audio_path: Path, lang: str | None = None) -> Dict[str, Any]:
        if not text or not text.strip():
            raise ValueError("El texto de referencia no puede estar vacío")

        if self._kernel.asr is None or self._kernel.textref is None or self._kernel.comparator is None:
            raise RuntimeError("El kernel no cuenta con todos los plugins configurados")

        ref_ipa = self._kernel.textref.text_to_ipa(text, lang)
        hyp_ipa = self._kernel.asr.transcribe_ipa(str(audio_path))
        compare_result = self._kernel.comparator.compare(ref_ipa, hyp_ipa)

        return {
            "text": text,
            "lang": lang,
            "ref_ipa": ref_ipa,
            "hyp_ipa": hyp_ipa,
            "per": compare_result.per,
            "matches": compare_result.matches,
            "substitutions": compare_result.substitutions,
            "insertions": compare_result.insertions,
            "deletions": compare_result.deletions,
            "total_ref_tokens": compare_result.total_ref_tokens,
            "ops": self._serialise_ops(compare_result.ops),
            "per_class": self._serialise_per_class(compare_result.per_class.items()),
            "config": self._kernel.config.to_mapping(),
        }

    @staticmethod
    def _serialise_ops(ops: Iterable[tuple[str, str, str]]) -> list[dict[str, str]]:
        return [
            {
                "op": op,
                "ref": ref,
                "hyp": hyp,
            }
            for op, ref, hyp in ops
        ]

    @staticmethod
    def _serialise_per_class(
        items: Iterable[tuple[str, PhonemeStats]]
    ) -> dict[str, dict[str, int]]:
        serialised: dict[str, dict[str, int]] = {}
        for key, stats in items:
            serialised[key] = {
                "matches": stats.matches,
                "substitutions": stats.substitutions,
                "insertions": stats.insertions,
                "deletions": stats.deletions,
                "errors": stats.errors,
            }
        return serialised


def create_app(
    *,
    service: AnalysisService | None = None,
    config: KernelConfig | None = None,
    config_path: str | Path | None = None,
) -> FastAPI:
    """Crea una instancia de FastAPI ya configurada con CORS y rutas."""

    app = FastAPI(title="PronunciaPA API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    app.state.analysis_service = service or AnalysisService(config=config, config_path=config_path)

    @app.get("/health", tags=["status"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/plugins", tags=["metadata"])
    async def get_plugins() -> dict[str, dict[str, list[str]]]:
        plugins: dict[str, list[str]] = {}
        for group_key, group in PLUGIN_GROUPS.items():
            plugins[group_key] = list_plugins(group.entrypoint_group)
        return {"plugins": plugins}

    @app.post("/api/analyze", tags=["analysis"])
    async def analyze(  # noqa: PLR0913 - FastAPI necesita la firma extendida
        request: Request,
        text: str = Form(...),
        lang: str | None = Form(None),
        audio: UploadFile = File(...),
    ) -> dict[str, Any]:
        suffix = Path(audio.filename or "audio.wav").suffix or ".wav"

        try:
            contents = await audio.read()
        finally:
            await audio.close()

        if not contents:
            raise HTTPException(status_code=400, detail="El archivo de audio está vacío")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = Path(tmp.name)

        service: AnalysisService = request.app.state.analysis_service

        try:
            return service.analyze(text=text, lang=lang, audio_path=tmp_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - fallback defensivo
            logger.exception("Error analizando el audio")
            raise HTTPException(status_code=500, detail="Error interno al procesar el análisis") from exc
        finally:
            tmp_path.unlink(missing_ok=True)

    return app


app = create_app()

__all__ = ["AnalysisService", "app", "create_app"]
