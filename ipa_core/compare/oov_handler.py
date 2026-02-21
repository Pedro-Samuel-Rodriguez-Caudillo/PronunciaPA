"""Manejo de fonemas fuera de inventario (OOV — Out-of-Vocabulary).

Estrategia (elegida por el usuario)
-------------------------------------
- Si la distancia articulatoria al fonema más cercano del inventario es
  **< 0.3** → **colapsar**: reemplazar el OOV por ese fonema cercano.
- Si la distancia es **≥ 0.3** → **marcar como desconocido** (``?``) y
  excluirlo del score final.

Esta separación es importante porque:
- Colapsar fonemas parecidos es legítimo en evaluación cross-dialectal.
- Marcar fonemas muy distintos evita que errores de ASR contaminen el score.

Modo fonémico vs. fonético
--------------------------
El handler soporta ambos niveles:
- **Fonémico**: el inventario contiene fonemas abstractos (``/p/``, ``/t/``, …).
- **Fonético**: el inventario contiene alófonos concretos (``[β]``, ``[ð]``, …).

El flag ``level`` en :class:`OOVHandler` indica qué nivel se está usando.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Sequence

from ipa_core.compare.articulatory import articulatory_distance
from ipa_core.types import Token


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

OOVDecision = Literal["collapse", "unknown", "in_inventory"]

UNKNOWN_TOKEN: Token = "?"  # Marcador para fonemas muy distantes


@dataclass(frozen=True)
class OOVResult:
    """Resultado de la resolución de un token potencialmente OOV.

    Campos
    ------
    original:
        Token original antes de la resolución.
    resolved:
        Token tras la resolución.  Puede ser:
        - El mismo token si estaba en el inventario (``decision="in_inventory"``).
        - El fonema más cercano del inventario (``decision="collapse"``).
        - ``UNKNOWN_TOKEN`` (``"?"``) si la distancia es ≥ umbral.
    decision:
        Decisión tomada: ``"in_inventory"``, ``"collapse"`` o ``"unknown"``.
    distance:
        Distancia articulatoria al fonema más cercano (0.0 si ya estaba en inventario).
    nearest:
        Fonema más cercano encontrado en el inventario (puede ser None si el inventario
        está vacío o el token es idéntico).
    """

    original: Token
    resolved: Token
    decision: OOVDecision
    distance: float = 0.0
    nearest: Optional[Token] = None


@dataclass
class OOVStats:
    """Estadísticas de la sesión de manejo OOV."""

    total: int = 0
    in_inventory: int = 0
    collapsed: int = 0
    marked_unknown: int = 0
    excluded_from_score: int = 0

    def record(self, result: OOVResult) -> None:
        self.total += 1
        if result.decision == "in_inventory":
            self.in_inventory += 1
        elif result.decision == "collapse":
            self.collapsed += 1
        else:
            self.marked_unknown += 1
            self.excluded_from_score += 1

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "in_inventory": self.in_inventory,
            "collapsed": self.collapsed,
            "marked_unknown": self.marked_unknown,
            "excluded_from_score": self.excluded_from_score,
            "oov_rate": (
                (self.collapsed + self.marked_unknown) / self.total
                if self.total > 0
                else 0.0
            ),
        }


# ---------------------------------------------------------------------------
# Handler principal
# ---------------------------------------------------------------------------

class OOVHandler:
    """Manejador de fonemas fuera del inventario del LanguagePack.

    Parámetros
    ----------
    inventory:
        Conjunto de fonemas/alófonos válidos para el idioma/dialecto.
    collapse_threshold:
        Umbral de distancia articulatoria.  Tokens con distancia al vecino
        más cercano **por debajo** de este umbral se colapsan; los que
        están **por encima o igual** se marcan como desconocidos.
        Valor por defecto: ``0.3`` (elegido por el usuario).
    level:
        Nivel de representación: ``"phonemic"`` o ``"phonetic"``.
    """

    COLLAPSE_THRESHOLD_DEFAULT: float = 0.3

    def __init__(
        self,
        inventory: Sequence[Token],
        *,
        collapse_threshold: float = COLLAPSE_THRESHOLD_DEFAULT,
        level: Literal["phonemic", "phonetic"] = "phonemic",
    ) -> None:
        if not 0.0 <= collapse_threshold <= 1.0:
            raise ValueError(
                f"collapse_threshold debe estar en [0, 1], recibido: {collapse_threshold}"
            )
        self._inventory: frozenset[Token] = frozenset(inventory)
        self._inventory_list: list[Token] = list(inventory)
        self.collapse_threshold = collapse_threshold
        self.level = level
        self._stats = OOVStats()

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def resolve(self, token: Token) -> OOVResult:
        """Resolver un token: determinar si es OOV y qué hacer con él.

        Parámetros
        ----------
        token:
            Fonema a evaluar.

        Retorna
        -------
        OOVResult
            Resultado con la decisión tomada.
        """
        # Caso 1: Token ya en inventario → sin cambios
        if token in self._inventory:
            result = OOVResult(
                original=token,
                resolved=token,
                decision="in_inventory",
                distance=0.0,
                nearest=token,
            )
            self._stats.record(result)
            return result

        # Caso 2: Inventario vacío → marcar como desconocido
        if not self._inventory_list:
            result = OOVResult(
                original=token,
                resolved=UNKNOWN_TOKEN,
                decision="unknown",
                distance=1.0,
                nearest=None,
            )
            self._stats.record(result)
            return result

        # Caso 3: Buscar el fonema más cercano en el inventario
        nearest, min_dist = self._find_nearest(token)

        if min_dist < self.collapse_threshold:
            result = OOVResult(
                original=token,
                resolved=nearest,
                decision="collapse",
                distance=min_dist,
                nearest=nearest,
            )
        else:
            result = OOVResult(
                original=token,
                resolved=UNKNOWN_TOKEN,
                decision="unknown",
                distance=min_dist,
                nearest=nearest,
            )

        self._stats.record(result)
        return result

    def resolve_sequence(self, tokens: Sequence[Token]) -> list[OOVResult]:
        """Resolver una secuencia completa de tokens."""
        return [self.resolve(t) for t in tokens]

    def filter_sequence(
        self,
        tokens: Sequence[Token],
        *,
        exclude_unknown: bool = True,
    ) -> list[Token]:
        """Resolver tokens y devolver la secuencia filtrada.

        Si ``exclude_unknown=True``, los tokens marcados como ``"?"`` se
        eliminan de la secuencia resultante (no se incluyen en el score).

        Parámetros
        ----------
        tokens:
            Secuencia original de tokens IPA.
        exclude_unknown:
            Si ``True``, excluir tokens ``UNKNOWN_TOKEN`` del resultado.

        Retorna
        -------
        list[Token]
            Secuencia con OOV colapsados y desconocidos filtrados (o marcados).
        """
        results = self.resolve_sequence(tokens)
        if exclude_unknown:
            return [r.resolved for r in results if r.resolved != UNKNOWN_TOKEN]
        return [r.resolved for r in results]

    def normalize_pair(
        self,
        ref: Sequence[Token],
        hyp: Sequence[Token],
        *,
        exclude_unknown: bool = True,
    ) -> tuple[list[Token], list[Token]]:
        """Normalizar el par (referencia, hipótesis) eliminando OOV extremos.

        Aplica la resolución OOV sobre ambas secuencias y elimina posiciones
        donde **ambas** son desconocidas (para no sesgar el PER).

        Retorna
        -------
        tuple[list[Token], list[Token]]
            (ref_normalizada, hyp_normalizada)
        """
        ref_results = self.resolve_sequence(ref)
        hyp_results = self.resolve_sequence(hyp)

        ref_out: list[Token] = []
        hyp_out: list[Token] = []

        # Para secuencias de distinta longitud, procesamos las que tienen pareja
        # y pasamos el resto directamente
        for r in ref_results:
            resolved = r.resolved
            if exclude_unknown and resolved == UNKNOWN_TOKEN:
                continue
            ref_out.append(resolved)

        for r in hyp_results:
            resolved = r.resolved
            if exclude_unknown and resolved == UNKNOWN_TOKEN:
                continue
            hyp_out.append(resolved)

        return ref_out, hyp_out

    # ------------------------------------------------------------------
    # Estadísticas
    # ------------------------------------------------------------------

    @property
    def stats(self) -> OOVStats:
        """Estadísticas acumuladas de la sesión."""
        return self._stats

    def reset_stats(self) -> None:
        """Reiniciar contadores de estadísticas."""
        self._stats = OOVStats()

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _find_nearest(self, token: Token) -> tuple[Token, float]:
        """Encontrar el fonema del inventario con menor distancia articulatoria."""
        best_token = self._inventory_list[0]
        best_dist = articulatory_distance(token, best_token)

        for candidate in self._inventory_list[1:]:
            dist = articulatory_distance(token, candidate)
            if dist < best_dist:
                best_dist = dist
                best_token = candidate
            if best_dist == 0.0:
                break  # No puede mejorar más

        return best_token, best_dist

    # ------------------------------------------------------------------
    # Constructor desde LanguagePack
    # ------------------------------------------------------------------

    @classmethod
    def from_inventory_dict(
        cls,
        inventory_dict: dict,
        *,
        collapse_threshold: float = COLLAPSE_THRESHOLD_DEFAULT,
        level: Literal["phonemic", "phonetic"] = "phonemic",
    ) -> "OOVHandler":
        """Construir desde el dict de inventario del YAML del pack.

        El dict puede tener la estructura del ``inventory_es-mx.yaml``:
        ``{consonants: [...], vowels: [...], diphthongs: [...], ...}``

        Parámetros
        ----------
        inventory_dict:
            Dict con categorías de fonemas.
        collapse_threshold:
            Umbral de colapso.
        level:
            Nivel de representación.
        """
        tokens: list[Token] = []
        for key in ("consonants", "vowels", "diphthongs", "allophones"):
            items = inventory_dict.get("inventory", inventory_dict).get(key, [])
            tokens.extend(str(t) for t in items)

        return cls(tokens, collapse_threshold=collapse_threshold, level=level)


# ---------------------------------------------------------------------------
# Función de conveniencia
# ---------------------------------------------------------------------------

def apply_oov_handling(
    ref: Sequence[Token],
    hyp: Sequence[Token],
    inventory: Sequence[Token],
    *,
    collapse_threshold: float = OOVHandler.COLLAPSE_THRESHOLD_DEFAULT,
    level: Literal["phonemic", "phonetic"] = "phonemic",
    exclude_unknown: bool = True,
) -> tuple[list[Token], list[Token], OOVStats]:
    """Aplicar manejo OOV sobre un par de secuencias.

    Función de conveniencia que crea un :class:`OOVHandler`, procesa el par
    y devuelve las secuencias normalizadas junto con las estadísticas.

    Parámetros
    ----------
    ref:
        Secuencia de referencia (IPA objetivo).
    hyp:
        Secuencia hipótesis (IPA observado por el usuario).
    inventory:
        Inventario fonémico/fonético válido del pack.
    collapse_threshold:
        Umbral de distancia articulatoria para colapsar OOV.
    level:
        Nivel de representación.
    exclude_unknown:
        Si ``True``, excluir tokens marcados como desconocidos del score.

    Retorna
    -------
    tuple[list[Token], list[Token], OOVStats]
        (ref_normalizada, hyp_normalizada, estadísticas)
    """
    handler = OOVHandler(inventory, collapse_threshold=collapse_threshold, level=level)
    ref_norm, hyp_norm = handler.normalize_pair(ref, hyp, exclude_unknown=exclude_unknown)
    return ref_norm, hyp_norm, handler.stats


__all__ = [
    "OOVDecision",
    "OOVHandler",
    "OOVResult",
    "OOVStats",
    "UNKNOWN_TOKEN",
    "apply_oov_handling",
]
