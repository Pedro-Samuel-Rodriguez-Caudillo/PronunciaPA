"""ASR ONNX offline con salida IPA."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

import numpy as np

from ipa_core.backends.audio_processing import LibrosaFeatureExtractor
from ipa_core.backends.onnx_engine import ONNXRunner
from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin
from ipa_core.plugins.models.schema import ModelConfig
from ipa_core.plugins.models import storage
from ipa_core.types import ASRResult, AudioInput, Token


class ONNXASRPlugin(BasePlugin):
    """Backend ASR basado en modelos ONNX locales."""

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        params = params or {}
        self._model_name = params.get("model_name")
        self._model_dir = Path(params["model_dir"]) if params.get("model_dir") else None
        self._model_path = Path(params["model_path"]) if params.get("model_path") else None
        self._config_path = Path(params["config_path"]) if params.get("config_path") else None
        self._download_url = params.get("download_url")
        self._config_url = params.get("config_url")
        self._vocab_url = params.get("vocab_url")
        self._sha256 = params.get("sha256")
        self._blank_id = params.get("blank_id")
        self._providers = params.get("providers")
        self._input_name = params.get("input_name")
        self._output_name = params.get("output_name")
        self._n_mels = int(params.get("n_mels", 80))

        self._config: ModelConfig | None = None
        self._labels: list[str] = []
        self._extractor: LibrosaFeatureExtractor | None = None
        self._runner: ONNXRunner | None = None

    def _resolve_paths(self) -> tuple[Path, Path]:
        model_dir = self._model_dir
        if not model_dir and self._model_name:
            model_dir = storage.get_models_dir() / self._model_name
        if model_dir:
            model_dir.mkdir(parents=True, exist_ok=True)
        model_path = self._model_path or (model_dir / "model.onnx" if model_dir else None)
        config_path = self._config_path or (model_dir / "config.json" if model_dir else None)
        if not model_path or not config_path:
            raise ValidationError("Falta model_path/model_dir para el plugin ONNX")
        return model_path, config_path

    async def setup(self) -> None:
        model_path, config_path = self._resolve_paths()

        if not model_path.exists():
            if not self._download_url:
                raise NotReadyError(f"Modelo ONNX no encontrado: {model_path}")
            await self.model_manager.download_model(
                name=self._model_name or "onnx_model",
                url=self._download_url,
                dest=model_path,
                sha256=self._sha256,
            )
        if not config_path.exists():
            if not self._config_url:
                raise NotReadyError(f"Config de modelo no encontrada: {config_path}")
            await self.model_manager.download_model(
                name=f"{self._model_name or 'onnx_model'}-config",
                url=self._config_url,
                dest=config_path,
                sha256=None,
            )
            
        vocab_path = model_path.parent / "vocab.json"
        if not vocab_path.exists() and self._vocab_url:
            await self.model_manager.download_model(
                name=f"{self._model_name or 'onnx_model'}-vocab",
                url=self._vocab_url,
                dest=vocab_path,
                sha256=None,
            )

        data = json.loads(config_path.read_text(encoding="utf-8"))
        self._config = ModelConfig(**data)
        
        # Load labels: try vocab.json first, then config.labels
        vocab_path = model_path.parent / "vocab.json"
        if vocab_path.exists():
            vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
            # Wav2Vec2 vocab is "char": id. Sort by ID to create list.
            sorted_items = sorted(vocab.items(), key=lambda item: item[1])
            # Ensure continuity? Assuming 0..N for now
            self._labels = [char for char, _ in sorted_items]
        else:
            self._labels = list(self._config.labels)
            
        blank_id = self._blank_id if self._blank_id is not None else getattr(self._config, "blank_id", 0)
        self._blank_id = int(blank_id)

        self._extractor = LibrosaFeatureExtractor(sample_rate=self._config.sample_rate, n_mels=self._n_mels)
        self._runner = ONNXRunner(
            model_path,
            providers=self._providers,
            input_name=self._input_name,
            output_name=self._output_name,
        )

    async def transcribe(
        self,
        audio: AudioInput,
        *,
        lang: Optional[str] = None,
        **kw: Any,
    ) -> ASRResult:
        if not self._extractor or not self._runner or not self._config:
            raise NotReadyError("ONNXASRPlugin no inicializado. Ejecuta setup().")
        features = await self._extractor.extract(audio)
        features = self._maybe_adjust_features(features)
        logits = await asyncio.to_thread(self._runner.run, features)
        tokens = self._ctc_greedy_decode(logits, self._labels, blank_id=self._blank_id or 0)
        return {
            "tokens": tokens,
            "meta": {
                "backend": "onnx",
                "model": self._config.model_name,
                "lang": lang or "",
                "tokens": len(tokens),
            },
        }

    def _maybe_adjust_features(self, features: np.ndarray) -> np.ndarray:
        if not self._config or not self._config.input_shape or features.ndim != 3:
            return features
        input_shape = self._config.input_shape
        if len(input_shape) != 3:
            return features
        if input_shape[1] == self._n_mels:
            return features
        if input_shape[2] == self._n_mels:
            return np.transpose(features, (0, 2, 1))
        return features

    @staticmethod
    def _ctc_greedy_decode(logits: np.ndarray, labels: list[str], *, blank_id: int) -> list[Token]:
        if logits.ndim == 3:
            seq = np.argmax(logits, axis=-1)[0]
        elif logits.ndim == 2:
            seq = np.argmax(logits, axis=-1)
        else:
            raise ValidationError(f"Salida ONNX con forma inesperada: {logits.shape}")

        tokens: list[Token] = []
        prev: Optional[int] = None
        for idx in seq.tolist():
            if idx == blank_id:
                prev = idx
                continue
            if prev is None or idx != prev:
                token = labels[idx] if idx < len(labels) else ""
                if token:
                    tokens.append(token)
            prev = idx
        return tokens


__all__ = ["ONNXASRPlugin"]
