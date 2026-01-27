"""LLM Guardrails: validación JSON, retry y fallback determinista.

Según ipa_core/TODO.md paso 14:
- Validar JSON del LLM contra schema
- Si falla, reintentar una vez con prompt de corrección
- Si vuelve a fallar, usar fallback determinista con plantillas
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from ipa_core.ports.llm import LLMAdapter

logger = logging.getLogger(__name__)


# Fallback determinista cuando LLM falla
_FALLBACK_PAYLOADS = {
    "es": {
        "summary": "Análisis de pronunciación completado.",
        "advice_short": "Practica los sonidos marcados.",
        "advice_long": "Revisa los fonemas con errores e intenta pronunciarlos lentamente.",
        "drills": [{"type": "minimal_pair", "text": "Practica pares mínimos"}],
    },
    "en": {
        "summary": "Pronunciation analysis complete.",
        "advice_short": "Practice the marked sounds.",
        "advice_long": "Review the phonemes with errors and try pronouncing them slowly.",
        "drills": [{"type": "minimal_pair", "text": "Practice minimal pairs"}],
    },
}

# Prompt de corrección para retry
_CORRECTION_PROMPT = """
The previous response was not valid JSON. Please respond ONLY with valid JSON in this exact format:
{
  "summary": "brief summary",
  "advice_short": "short advice",
  "advice_long": "detailed advice",
  "drills": [{"type": "type", "text": "drill text"}]
}

Original request:
{original_prompt}
"""


class LLMGuardrails:
    """Wrapper que agrega validación, retry y fallback a un LLMAdapter."""

    def __init__(
        self,
        adapter: LLMAdapter,
        *,
        max_retries: int = 1,
        fallback_lang: str = "en",
    ) -> None:
        self._adapter = adapter
        self._max_retries = max_retries
        self._fallback_lang = fallback_lang
        self._setup_done = False

    async def setup(self) -> None:
        if not self._setup_done:
            await self._adapter.setup()
            self._setup_done = True

    async def teardown(self) -> None:
        if self._setup_done:
            await self._adapter.teardown()
            self._setup_done = False

    async def complete_with_guardrails(
        self,
        prompt: str,
        *,
        schema: Optional[dict[str, Any]] = None,
        lang: str = "en",
        params: Optional[dict[str, Any]] = None,
        **kw,
    ) -> dict[str, Any]:
        """Ejecutar LLM con validación, retry y fallback.

        Args:
            prompt: Prompt original para el LLM
            schema: Schema JSON opcional para validación estructural
            lang: Idioma para fallback (default: en)
            params: Parámetros adicionales para el adapter

        Returns:
            Diccionario con la respuesta parseada (o fallback si falla)
        """
        attempt = 0
        last_error: Optional[str] = None

        while attempt <= self._max_retries:
            try:
                if attempt == 0:
                    current_prompt = prompt
                else:
                    # Retry con prompt de corrección
                    current_prompt = _CORRECTION_PROMPT.format(original_prompt=prompt)
                    logger.warning(
                        f"LLM retry {attempt}/{self._max_retries} - usando prompt de corrección"
                    )

                response = await self._adapter.complete(current_prompt, params=params, **kw)
                result = self._parse_and_validate(response, schema)
                return result

            except (json.JSONDecodeError, ValueError) as e:
                last_error = str(e)
                attempt += 1
                logger.warning(f"LLM response inválida (intento {attempt}): {last_error}")

        # Fallback determinista
        logger.error(
            f"LLM falló después de {self._max_retries + 1} intentos. "
            f"Usando fallback para '{lang}'. Último error: {last_error}"
        )
        return self._get_fallback(lang)

    def _parse_and_validate(
        self,
        response: str,
        schema: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Parsear JSON y validar estructura básica.

        Raises:
            json.JSONDecodeError: Si no es JSON válido
            ValueError: Si falta estructura requerida
        """
        # Limpiar respuesta (remover markdown code blocks si existen)
        clean_response = response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.split("\n")
            clean_response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        result = json.loads(clean_response)

        if not isinstance(result, dict):
            raise ValueError("Response must be a JSON object")

        # Validación estructural básica
        required_keys = {"summary", "advice_short", "advice_long", "drills"}
        missing = required_keys - set(result.keys())
        if missing:
            raise ValueError(f"Missing required keys: {missing}")

        # TODO: Validar contra schema completo si se proporciona
        return result

    def _get_fallback(self, lang: str) -> dict[str, Any]:
        """Obtener payload de fallback por idioma."""
        fallback_lang = lang[:2] if len(lang) > 2 else lang
        if fallback_lang not in _FALLBACK_PAYLOADS:
            fallback_lang = self._fallback_lang
        return dict(_FALLBACK_PAYLOADS.get(fallback_lang, _FALLBACK_PAYLOADS["en"]))


__all__ = ["LLMGuardrails"]
