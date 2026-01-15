"""llama.cpp runtime adapter."""
from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin


class LlamaCppAdapter(BasePlugin):
    """Adapter that calls llama.cpp CLI."""

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        params = params or {}
        self._binary = (
            params.get("binary")
            or os.getenv("PRONUNCIAPA_LLAMACPP_BIN")
            or os.getenv("PRONUNCIAPA_LLM_BIN")
            or "llama-cli"
        )
        self._model_path = params.get("model_path")
        self._n_ctx = params.get("n_ctx", 4096)
        self._n_gpu_layers = params.get("n_gpu_layers", 0)
        self._temperature = params.get("temperature")
        self._top_p = params.get("top_p")
        self._prompt_arg = params.get("prompt_arg", "-f")
        self._extra_args = list(params.get("extra_args", []))

    async def setup(self) -> None:
        if not _binary_exists(self._binary):
            raise NotReadyError("llama.cpp binary not found.")
        if not self._model_path:
            raise NotReadyError("llama.cpp model_path is required.")
        if not Path(self._model_path).exists():
            raise NotReadyError(f"llama.cpp model not found: {self._model_path}")

    async def complete(self, prompt: str, *, params: Optional[dict[str, Any]] = None, **kw) -> str:
        if not _binary_exists(self._binary):
            raise NotReadyError("llama.cpp binary not found.")
        if not self._model_path:
            raise NotReadyError("llama.cpp model_path is required.")

        merged = dict(params or {})
        model_path = merged.get("model_path", self._model_path)
        n_ctx = merged.get("n_ctx", self._n_ctx)
        n_gpu_layers = merged.get("n_gpu_layers", self._n_gpu_layers)
        temperature = merged.get("temperature", self._temperature)
        top_p = merged.get("top_p", self._top_p)
        prompt_arg = merged.get("prompt_arg", self._prompt_arg)
        extra_args = list(merged.get("extra_args", self._extra_args))

        prompt_file = _write_prompt(prompt)
        cmd = [
            self._binary,
            "-m",
            str(model_path),
            "--ctx-size",
            str(n_ctx),
            "--n-gpu-layers",
            str(n_gpu_layers),
            prompt_arg,
            str(prompt_file),
        ]
        if temperature is not None:
            cmd.extend(["--temp", str(temperature)])
        if top_p is not None:
            cmd.extend(["--top-p", str(top_p)])
        if extra_args:
            cmd.extend(str(arg) for arg in extra_args)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
        except FileNotFoundError as exc:
            raise NotReadyError(f"Failed to execute llama.cpp: {self._binary}") from exc
        except Exception as exc:
            raise ValidationError(f"llama.cpp invocation failed: {exc}") from exc
        finally:
            try:
                prompt_file.unlink()
            except OSError:
                pass

        if proc.returncode != 0:
            detail = stderr.decode(errors="ignore").strip()
            raise ValidationError(f"llama.cpp failed with code {proc.returncode}: {detail}")
        return stdout.decode(errors="ignore")


def _binary_exists(binary: str) -> bool:
    if shutil.which(binary):
        return True
    return Path(binary).exists()


def _write_prompt(prompt: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(prefix="pronunciapa_llm_", suffix=".txt", delete=False)
    path = Path(tmp.name)
    path.write_text(prompt, encoding="utf-8")
    return path


__all__ = ["LlamaCppAdapter"]
