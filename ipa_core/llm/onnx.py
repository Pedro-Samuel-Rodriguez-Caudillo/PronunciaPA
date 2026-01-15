"""ONNX runtime adapter (command-based)."""
from __future__ import annotations

import asyncio
import os
import shlex
from pathlib import Path
from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin


class OnnxLLMAdapter(BasePlugin):
    """Adapter that delegates to an external ONNX CLI."""

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        params = params or {}
        self._command = (
            params.get("command")
            or os.getenv("PRONUNCIAPA_ONNX_CMD")
            or os.getenv("PRONUNCIAPA_LLM_CMD")
        )
        self._extra_args = list(params.get("extra_args", []))

    async def setup(self) -> None:
        if not self._command:
            raise NotReadyError("ONNX adapter requires a command to execute.")

    async def complete(self, prompt: str, *, params: Optional[dict[str, Any]] = None, **kw) -> str:
        if not self._command:
            raise NotReadyError("ONNX adapter requires a command to execute.")

        cmd = _build_command(self._command, prompt)
        extra_args = list((params or {}).get("extra_args", self._extra_args))
        if extra_args:
            cmd.extend(str(arg) for arg in extra_args)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(prompt.encode("utf-8"))
        except FileNotFoundError as exc:
            raise NotReadyError("Failed to execute ONNX command.") from exc
        except Exception as exc:
            raise ValidationError(f"ONNX invocation failed: {exc}") from exc

        if proc.returncode != 0:
            detail = stderr.decode(errors="ignore").strip()
            raise ValidationError(f"ONNX command failed with code {proc.returncode}: {detail}")
        return stdout.decode(errors="ignore")


def _build_command(command: str | list[str], prompt: str) -> list[str]:
    if isinstance(command, list):
        return [str(item) for item in command]
    rendered = command.replace("{prompt}", prompt)
    return [str(part) for part in shlex.split(rendered)]


__all__ = ["OnnxLLMAdapter"]
