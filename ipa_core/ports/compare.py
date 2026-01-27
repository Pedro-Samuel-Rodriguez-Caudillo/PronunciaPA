"""Puerto Comparator (ref vs hyp -> métricas).

Patrón sugerido
---------------
- Strategy: posibilita distintas implementaciones (Levenshtein, DTW, etc.).
- Visitor (opcional): facilita recorrer alineaciones para generar reportes.

Prerrequisito: Normalización de tokens
--------------------------------------
Los tokens de entrada (ref y hyp) DEBEN estar normalizados ANTES de
invocar al comparador. Ver `Preprocessor.normalize_tokens()`.
El comparador NO normaliza— compara tokens tal cual los recibe.

Phone Error Rate (PER)
----------------------
PER está en el rango [0.0, ∞), donde:
- 0.0 = pronunciación perfecta (sin errores)
- 1.0 = 100% de errores (todos los tokens incorrectos)
- >1.0 = posible cuando hay más inserciones que tokens de referencia

Fórmula: PER = (S + I + D) / len(ref)
- S = sustituciones
- I = inserciones
- D = eliminaciones

Para UI, se recomienda convertir a score: max(0, 100 * (1 - PER))

Validación de CompareWeights
----------------------------
- sub, ins, del_ deben ser >= 0.0
- Si son None, usar defaults: {sub: 1.0, ins: 1.0, del_: 1.0}
- Pesos negativos son inválidos y deben lanzar ValueError
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from ipa_core.types import CompareResult, CompareWeights, TokenSeq


@runtime_checkable
class Comparator(Protocol):
    """Define el contrato para comparar dos secuencias de tokens IPA.
    
    Debe soportar el ciclo de vida de `BasePlugin`.
    
    Prerrequisito
    -------------
    Los tokens deben estar normalizados antes de comparar.
    El comparador NO realiza normalización.
    """

    async def setup(self) -> None:
        """Configuración inicial del plugin (asíncrona)."""
        ...

    async def teardown(self) -> None:
        """Limpieza de recursos del plugin (asíncrona)."""
        ...

    async def compare(
        self,
        ref: TokenSeq,
        hyp: TokenSeq,
        *,
        weights: Optional[CompareWeights] = None,
        **kw,
    ) -> CompareResult:  # noqa: D401
        """Comparar `ref` (referencia) contra `hyp` (predicción).

        Parámetros
        ----------
        ref : TokenSeq
            Secuencia de tokens de referencia (target).
        hyp : TokenSeq
            Secuencia de tokens producidos por ASR (observado).
        weights : Optional[CompareWeights]
            Pesos para operaciones S/I/D. Default: 1.0 cada uno.
            Pesos negativos son inválidos.

        Retorna
        -------
        CompareResult
            Contiene PER, lista de operaciones, y alineación.
        """
        ...