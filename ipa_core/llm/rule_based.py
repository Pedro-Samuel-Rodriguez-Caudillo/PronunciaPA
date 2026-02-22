"""Adaptador de feedback basado en reglas (sin LLM, sin model pack).

Implementa el protocolo LLMAdapter usando ``generate_fallback_feedback()``
de forma completamente determinista y offline.  Es útil como:

- Fallback cuando no hay LLM configurado.
- Backend por defecto en instalaciones mínimas (pip install pronunciapa).
- Modo de desarrollo rápido sin descargar modelos.

El adaptador se puede registrar como ``llm = rule_based`` en el config
o mediante la variable de entorno ``PRONUNCIAPA_LLM=rule_based``.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from ipa_core.plugins.base import BasePlugin


class RuleBasedFeedbackAdapter(BasePlugin):
    """Genera feedback determinista a partir del reporte de error.

    Implementa el protocolo LLMAdapter sin requerir modelo ni model pack.
    FeedbackService detecta ``rule_based=True`` para omitir la validación
    del model pack y pasarle el reporte directamente como JSON.

    Parámetros
    ----------
    lang : str, optional
        Idioma preferido para las plantillas de fallback.  Si no se
        especifica se usa el campo ``lang`` del reporte de error.
    """

    # Señal para que FeedbackService no exija model_pack
    rule_based: bool = True

    def __init__(self, *, lang: Optional[str] = None) -> None:
        super().__init__()
        self._lang = lang

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

    async def complete(
        self,
        prompt: str,
        params: Optional[dict[str, Any]] = None,
        **kw: Any,
    ) -> str:
        """Generar feedback sin LLM.

        Parameters
        ----------
        prompt : str
            Reporte de error serializado como JSON (pasado por
            ``FeedbackService`` cuando detecta ``rule_based=True``).
        params : dict, optional
            Ignorado (sin modelo que parametrizar).

        Returns
        -------
        str
            Feedback serializado como JSON.
        """
        from ipa_core.services.fallback import generate_fallback_feedback

        try:
            report: dict[str, Any] = json.loads(prompt)
        except (json.JSONDecodeError, ValueError):
            report = {}

        # Permitir override de idioma via constructor
        if self._lang and "lang" not in report:
            report = {**report, "lang": self._lang}

        feedback = generate_fallback_feedback(report)
        return json.dumps(feedback, ensure_ascii=False)


__all__ = ["RuleBasedFeedbackAdapter"]
