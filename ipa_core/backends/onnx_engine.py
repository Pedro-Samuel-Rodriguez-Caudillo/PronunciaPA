"""Motor ONNX para inferencia offline."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

try:
    import onnxruntime as ort
except ImportError:  # pragma: no cover
    ort = None  # type: ignore[assignment]


class ONNXRunner:
    """Envuelve una sesión de ONNX Runtime para inferencia local."""

    def __init__(
        self,
        model_path: Path,
        *,
        providers: Optional[list[str]] = None,
        input_name: Optional[str] = None,
        output_name: Optional[str] = None,
    ) -> None:
        if ort is None:
            raise ImportError("onnxruntime no instalado. Usa `pip install ipa-core[onnx]`.")
        if not model_path.exists():
            raise FileNotFoundError(f"Modelo ONNX no encontrado: {model_path}")

        self._session = ort.InferenceSession(str(model_path), providers=providers or ["CPUExecutionProvider"])
        self._input_name = input_name or self._session.get_inputs()[0].name
        self._output_name = output_name or self._session.get_outputs()[0].name

    def run(self, features: np.ndarray) -> np.ndarray:
        """Ejecuta inferencia y retorna el tensor de salida."""
        if features.dtype != np.float32:
            features = features.astype(np.float32, copy=False)
        outputs = self._session.run([self._output_name], {self._input_name: features})
        return outputs[0]


__all__ = ["ONNXRunner"]
