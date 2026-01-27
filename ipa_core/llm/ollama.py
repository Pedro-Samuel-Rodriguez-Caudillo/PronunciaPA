"""Ollama runtime adapter for local LLMs.

This adapter calls the Ollama REST API to generate completions
using models like TinyLlama or Phi-3 that are already downloaded.
"""
from __future__ import annotations

import os
from typing import Any, Optional

from ipa_core.errors import NotReadyError, ValidationError
from ipa_core.plugins.base import BasePlugin


class OllamaAdapter(BasePlugin):
    """Adapter that calls Ollama's REST API for LLM completions.
    
    Ollama must be running (`ollama serve`) and the model must be
    downloaded (`ollama pull tinyllama`).
    
    Parameters
    ----------
    params : dict, optional
        - base_url: Ollama server URL (default: http://localhost:11434)
        - model: Model name to use (default: tinyllama)
        - temperature: Sampling temperature (default: 0.7)
        - num_ctx: Context window size (default: 4096)
        - timeout: Request timeout in seconds (default: 120)
    """

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        params = params or {}
        self._base_url = (
            params.get("base_url")
            or os.getenv("OLLAMA_HOST")
            or "http://localhost:11434"
        )
        self._model = params.get("model", "tinyllama")
        self._temperature = params.get("temperature", 0.7)
        self._num_ctx = params.get("num_ctx", 4096)
        self._timeout = params.get("timeout", 120)
        self._session = None

    async def setup(self) -> None:
        """Verify Ollama is running and model is available."""
        try:
            import aiohttp
        except ImportError as e:
            raise NotReadyError(
                "aiohttp is required for OllamaAdapter. "
                "Install with: pip install aiohttp"
            ) from e

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        raise NotReadyError(
                            f"Ollama server not responding at {self._base_url}"
                        )
                    data = await resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    # Check if model exists (partial match for tags like :latest)
                    if not any(self._model in m for m in models):
                        available = ", ".join(models[:5]) or "none"
                        raise NotReadyError(
                            f"Model '{self._model}' not found in Ollama. "
                            f"Available: {available}. "
                            f"Run: ollama pull {self._model}"
                        )
        except aiohttp.ClientError as e:
            raise NotReadyError(
                f"Cannot connect to Ollama at {self._base_url}. "
                f"Is Ollama running? Try: ollama serve"
            ) from e

    async def teardown(self) -> None:
        """Cleanup (no-op for stateless HTTP client)."""
        pass

    async def complete(
        self,
        prompt: str,
        *,
        params: Optional[dict[str, Any]] = None,
        **kw,
    ) -> str:
        """Generate completion using Ollama's generate endpoint.
        
        Parameters
        ----------
        prompt : str
            The prompt to send to the model.
        params : dict, optional
            Override parameters for this call.
            
        Returns
        -------
        str
            The model's raw text response.
        """
        import aiohttp

        merged = dict(params or {})
        model = merged.get("model", self._model)
        temperature = merged.get("temperature", self._temperature)
        num_ctx = merged.get("num_ctx", self._num_ctx)
        timeout = merged.get("timeout", self._timeout)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise ValidationError(
                            f"Ollama error ({resp.status}): {text[:200]}"
                        )
                    data = await resp.json()
                    return data.get("response", "")
        except aiohttp.ClientError as e:
            raise ValidationError(f"Ollama request failed: {e}") from e


__all__ = ["OllamaAdapter"]
