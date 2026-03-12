"""Adaptador Ollama especializado en feedback de pronunciación.

Combina OllamaAdapter con una plantilla de prompt pedagógica para generar
consejos de pronunciación más ricos que los de rule_based, sin requerir
un model_pack descargado.

Funcionamiento
--------------
1. FeedbackService detecta ``rule_based = True`` y pasa el error report
   como JSON (en lugar de un prompt con model_pack).
2. Este adaptador construye un prompt de pronunciación a partir del JSON.
3. Llama a Ollama (llama3, phi3:mini, tinyllama, etc.) para generar consejos.
4. Parsea la respuesta y la devuelve como JSON estructurado.
5. Si Ollama falla (no disponible, timeout, respuesta inválida), hace
   fallback automático a ``generate_fallback_feedback``.

Configuración recomendada
-------------------------
En ``configs/local.yaml``::

    llm:
      name: ollama
      params:
        model: qwen3.5:3b        # modelos recomendados: qwen3.5:3b (rápido, json), llama3:8b (calidad)
        base_url: http://localhost:11434
        temperature: 0.4        # más bajo = más determinista, mejor para JSON
        timeout: 60

Variables de entorno::

    PRONUNCIAPA_LLM=ollama
    OLLAMA_HOST=http://localhost:11434  # si no es el default
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from ipa_core.llm.ollama import OllamaAdapter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template — bilingual, concise for small models
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """You are a helpful pronunciation coach for language learners.
Analyze the phonetic error report below and generate structured feedback.
Respond in the same language as the "lang" field (es=Spanish, en=English, fr=French, etc.).

RULES:
- Return ONLY a valid JSON object, no extra text
- Keep advice concise and encouraging
- Focus on the most important errors (max 3)
- For the `advice_long` section, explicitly include articulatory hints: explain HOW the user possibly pronounced the sound (e.g. "Posiblemente lo hiciste así: moviste tu lengua...") and HOW they should correctly pronounce it (e.g. "Debería ser: coloca los labios...").
- Suggest practical exercises (drills)

OUTPUT JSON structure (replace placeholders with actual feedback):
{{
  "summary": "<Insert brief overall assessment (1 sentence, encouraging tone)>",
  "advice_short": "<Insert single most important tip>",
  "advice_long": "<Insert detailed explanation with phonetic guidance (2-4 sentences)>",
  "drills": [
    {{"type": "contrast", "text": "<Insert minimal pair or contrast exercise>"}},
    {{"type": "practice", "text": "<Insert repetition exercise>"}}
  ]
}}

ERROR REPORT:
{report_json}

JSON:"""

# Fallback minimal JSON if the model's response can't be parsed
_MINIMAL_FEEDBACK = {
    "summary": "",
    "advice_short": "",
    "advice_long": "",
    "drills": [],
}


def _build_prompt(report: dict[str, Any]) -> str:
    """Construir el prompt para Ollama a partir del error report."""
    # Simplify the report to reduce token count
    compact = {
        "lang": report.get("lang", "es"),
        "target_text": report.get("target_text", ""),
        "target_ipa": report.get("target_ipa", ""),
        "observed_ipa": report.get("observed_ipa", ""),
        "per": report.get("metrics", {}).get("per", 0.0),
        "score": report.get("metrics", {}).get("score", 0),
        "ops": [
            op for op in (report.get("ops") or [])
            if op.get("op") != "eq"  # only errors
        ][:5],  # max 5 ops
        "evaluation_level": report.get("evaluation_level", "phonemic"),
    }
    return _PROMPT_TEMPLATE.format(report_json=json.dumps(compact, ensure_ascii=False))


def _extract_feedback(raw: str, report: dict[str, Any]) -> dict[str, Any]:
    """Extraer JSON estructurado de la respuesta del modelo.

    Intenta varias estrategias de extracción antes de usar el fallback.
    """
    if not raw or not raw.strip():
        return {}

    # Strategy 1: full response is valid JSON
    try:
        payload = json.loads(raw.strip())
        if isinstance(payload, dict) and "summary" in payload:
            return payload
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: find JSON object in response
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            payload = json.loads(raw[start:end])
            if isinstance(payload, dict) and "summary" in payload:
                return payload
        except (json.JSONDecodeError, ValueError):
            pass

        logger.debug("No se pudo parsear JSON de la respuesta de Ollama: %r", raw[:200])
    return {}


class OllamaFeedbackAdapter(OllamaAdapter):
    """Adaptador Ollama especializado en feedback de pronunciación.

    Implementa el protocolo LLMAdapter con ``rule_based = True`` para que
    FeedbackService le pase el error report como JSON (sin necesitar model_pack).
    El adaptador construye su propio prompt pedagógico y llama a Ollama.
    Si Ollama no está disponible, hace fallback a ``generate_fallback_feedback``.

    Parámetros
    ----------
    params : dict, optional
        Los mismos de OllamaAdapter (base_url, model, temperature, etc.)
        más:
        - fallback_on_error: bool — si True (default), usa rule_based si Ollama falla.
    """

    # Señal para que FeedbackService pase el JSON del error report directamente
    rule_based: bool = True

    def __init__(self, params: Optional[dict[str, Any]] = None) -> None:
        params = params or {}
        self._fallback_on_error = params.pop("fallback_on_error", True)
        self._max_retries = int(params.pop("max_retries", 2))
        self._base_delay = float(params.pop("retry_base_delay", 0.8))
        self._request_timeout = int(params.get("timeout", 35))
        # Default to better models for pronunciation feedback
        if "model" not in params:
            params = {**params, "model": "qwen3.5:4b"}
        if "temperature" not in params:
            params = {**params, "temperature": 0.4}
        if "timeout" not in params:
            params = {**params, "timeout": self._request_timeout}
        super().__init__(params)

    async def setup(self) -> None:
        """Inicializar Ollama, con fallback silencioso si no está disponible."""
        try:
            await super().setup()
            logger.info(
                "OllamaFeedbackAdapter listo: modelo=%s, url=%s",
                self._model, self._base_url,
            )
        except Exception as exc:
            if self._fallback_on_error:
                logger.warning(
                    "Ollama no disponible (%s) — usando fallback rule_based. "
                    "Para activar Ollama: ollama serve && ollama pull %s",
                    exc, self._model,
                )
                self._ollama_ready = False
            else:
                raise
        else:
            self._ollama_ready = True

    async def complete(
        self,
        prompt: str,
        *,
        params: Optional[dict[str, Any]] = None,
        **kw,
    ) -> str:
        """Generar feedback de pronunciación usando Ollama.

        Recibe el error report como JSON string (porque rule_based=True),
        construye un prompt pedagógico, llama a Ollama y retorna JSON
        con la estructura de FeedbackPayload.
        """
        from ipa_core.services.fallback import generate_fallback_feedback

        # Parsear el error report recibido de FeedbackService
        try:
            report: dict[str, Any] = json.loads(prompt)
        except (json.JSONDecodeError, ValueError):
            report = {}

        # Si Ollama no está disponible, usar fallback directamente
        if not getattr(self, "_ollama_ready", False):
            logger.debug("Ollama no disponible, usando generate_fallback_feedback")
            return json.dumps(generate_fallback_feedback(report), ensure_ascii=False)

        # Construir prompt pedagógico
        ollama_prompt = _build_prompt(report)

        import asyncio
        from ipa_core.errors import LLMAPIError

        max_retries = max(1, self._max_retries)
        base_delay = max(0.1, self._base_delay)

        for attempt in range(1, max_retries + 1):
            try:
                runtime_params = dict(params or {})
                runtime_params.setdefault("timeout", self._request_timeout)
                raw = await super().complete(ollama_prompt, params=runtime_params, **kw)
                feedback = _extract_feedback(raw, report)
                if feedback:
                    # Asegurarnos de que el resultado tiene todos los campos requeridos
                    feedback.setdefault("drills", [])
                    feedback.setdefault("summary", feedback.get("advice_short", ""))
                    feedback.setdefault("advice_short", feedback.get("summary", ""))
                    feedback.setdefault("advice_long", feedback.get("advice_short", ""))
                    feedback["source"] = "ollama"
                    feedback["model"] = self._model
                    return json.dumps(feedback, ensure_ascii=False)
                else:
                    raise LLMAPIError("Extracción de feedback falló o JSON no encontrado")
            except Exception as exc:
                if attempt < max_retries:
                    logger.warning(
                        "Ollama request falló (intento %d/%d): %r. Reintentando en %.1fs...",
                        attempt, max_retries, exc, base_delay * (2 ** (attempt - 1))
                    )
                    await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
                else:
                    logger.warning(
                        "Ollama request falló definitivamente tras %d intentos: %r. Usando fallback rule_based.",
                        max_retries, exc
                    )

        # Fallback: usar generate_fallback_feedback
        fallback = generate_fallback_feedback(report)
        fallback["source"] = "fallback_after_ollama_error"
        return json.dumps(fallback, ensure_ascii=False)


__all__ = ["OllamaFeedbackAdapter"]
