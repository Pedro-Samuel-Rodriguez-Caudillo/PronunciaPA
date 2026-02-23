"""Módulo de visualización dual de IPA con código de color por token.

Soporta dos modos de display seleccionables por el aprendiz:

- **técnico** (``technical``): IPA puro, apto para perfil avanzado.
  Muestra cada fonema con su símbolo IPA canónico.
- **casual** (``casual``): Transliteración coloquial, más legible para
  principiantes. Usa letras latinas aproximadas y dígrafos intuitivos.

Colores por token
-----------------
Cada token en el resultado de comparación tiene un estado semántico que
se mapea a un color:

+----------+--------+------------------------------------------------------+
| Estado   | Color  | Significado                                          |
+==========+========+======================================================+
| correct  | green  | Token correcto (``op == "eq"``)                     |
| allophone| purple | Alófono — variante fonética contextual (modo        |
|          |        | fonético): b~β, d~ð, g~ɣ, r~ɾ, etc.              |
| close    | yellow | Sustitución con distancia articulatoria < 0.3        |
| error    | red    | Error fonémico significativo (dist ≥ 0.3) o ins/del |
| unknown  | gray   | Token OOV / desconocido                             |
+----------+--------+------------------------------------------------------+

Nivel fonémico vs. fonético
----------------------------
El sistema soporta ambos niveles sin cambiar la interfaz. El nivel se
indica como metadato en ``IPADisplayToken.level``.

En modo **fonémico**, los alófonos se colapsan antes de la comparación
(β→b, ð→d, ɣ→g), por lo que no aparecen como sustituciones.

En modo **fonético**, los alófonos se preservan. Cuando el aprendiz
pronuncia [β] donde se esperaba /b/, se marca como ``purple`` (alófono)
en lugar de amarillo o rojo, indicando que es una variante contextual
válida, no un error.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, List, Literal, Optional, Sequence, Tuple

from ipa_core.compare.articulatory import articulatory_distance
from ipa_core.types import EditOp, Token


# ---------------------------------------------------------------------------
# Constantes y tipos
# ---------------------------------------------------------------------------

TokenColor = Literal["green", "yellow", "red", "gray", "purple"]
DisplayMode = Literal["technical", "casual"]
RepLevel = Literal["phonemic", "phonetic"]

# Umbral articulatorio para distinguir "close" de "error"
COLOR_CLOSE_THRESHOLD: float = 0.3

# Pares de alófonos conocidos (frozensets para lookup O(1) independiente de orden).
# Cuando en modo fonético se detecta una sustitución dentro de este conjunto,
# se clasifica como "purple" (alófono) en lugar de amarillo/rojo.
_ALLOPHONE_PAIRS: FrozenSet[FrozenSet[str]] = frozenset({
    # Spanish stop~fricative allophones (intervocalic lenition)
    frozenset(("b", "β")),  # /b/ ~ [β]
    frozenset(("d", "ð")),  # /d/ ~ [ð]
    frozenset(("g", "ɣ")),  # /g/ ~ [ɣ]
    # Spanish rhotics
    frozenset(("r", "ɾ")),  # /r/ (trill) ~ [ɾ] (tap)
    # Nasal assimilation
    frozenset(("n", "ŋ")),  # /n/ ~ [ŋ] before velars
    frozenset(("n", "m")),  # /n/ ~ [m] before bilabials
    # Voicing assimilation (cross-linguistic)
    frozenset(("s", "z")),  # /s/ ~ [z] before voiced consonants
    # Palatal glide variants
    frozenset(("j", "ʝ")),  # /j/ ~ [ʝ] in stressed position
})


def _is_allophone_pair(ref: str, hyp: str) -> bool:
    """Verificar si ref e hyp son alófonos entre sí."""
    return frozenset((ref, hyp)) in _ALLOPHONE_PAIRS


# Transliteración coloquial: IPA → aproximación latina
# Para Español Mexicano y vocales universales
_CASUAL_MAP: dict[str, str] = {
    # Vocales
    "a": "a", "e": "e", "i": "i", "o": "o", "u": "u",
    "ə": "e", "ɛ": "e", "ɔ": "o", "æ": "a",
    "ɪ": "i", "ʊ": "u", "ʌ": "o",
    # Consonantes comunes
    "p": "p", "b": "b", "t": "t", "d": "d", "k": "k", "g": "g",
    "f": "f", "v": "v", "s": "s", "z": "s",
    "m": "m", "n": "n", "ɲ": "ñ", "ŋ": "ng",
    "l": "l", "r": "r", "ɾ": "r", "ʎ": "ll",
    "j": "y", "w": "w",
    # Fricativas hispanohablantes
    "x": "j", "ʝ": "y", "β": "b", "ð": "d", "ɣ": "g",
    "h": "j",
    # Africadas
    "tʃ": "ch", "dʒ": "dy",
    "ts": "ts", "dz": "ds",
    # Fricativas postalveolares
    "ʃ": "sh", "ʒ": "zh",
    # Vibrante múltiple
    "rr": "rr",
    # Glotal
    "ʔ": "'",
    # Nasales especiales
    "ɴ": "n",
    # Semivocales / glides
    "ɹ": "r",
}


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------

@dataclass
class IPADisplayToken:
    """Representación visual de un token IPA individual.

    Campos
    ------
    ipa:
        Símbolo IPA canónico (modo técnico).
    casual:
        Transliteración coloquial (modo casual).
    color:
        Color semántico: ``"green"``, ``"yellow"``, ``"red"``, ``"gray"``,
        ``"purple"`` (alófono en modo fonético).
    op:
        Operación de edición original (``"eq"``, ``"sub"``, ``"ins"``, ``"del"``).
    ref:
        Token de referencia (IPA objetivo).
    hyp:
        Token observado (IPA hipótesis).
    articulatory_distance:
        Distancia articulatoria en [0, 1].  None si no aplica.
    level:
        Nivel de representación: ``"phonemic"`` o ``"phonetic"``.
    is_allophone:
        True cuando la sustitución es una variante alofónica conocida
        (solo posible en modo fonético). Permite a la UI mostrar un
        indicador visual adicional (e.g., tilde ~).
    """

    ipa: str
    casual: str
    color: TokenColor
    op: str
    ref: Optional[str] = None
    hyp: Optional[str] = None
    articulatory_distance: Optional[float] = None
    level: RepLevel = "phonemic"
    is_allophone: bool = False


@dataclass
class IPADisplayResult:
    """Resultado completo de la visualización IPA dual.

    Contiene la secuencia de tokens con sus colores y ambas representaciones
    (técnica y casual) del IPA objetivo y el observado.

    Campos
    ------
    tokens:
        Lista de tokens con color y transliteración.
    mode:
        Modo de display activo: ``"technical"`` o ``"casual"``.
    level:
        Nivel de evaluación: ``"phonemic"`` o ``"phonetic"``.
    ref_technical:
        IPA objetivo en modo técnico (concatenado).
    ref_casual:
        IPA objetivo en modo casual (concatenado).
    hyp_technical:
        IPA observado en modo técnico (concatenado).
    hyp_casual:
        IPA observado en modo casual (concatenado).
    score_color:
        Color global del score: green ≥ 80, yellow 50–79, red < 50.
    legend:
        Leyenda de colores para mostrar al aprendiz.
    """

    tokens: List[IPADisplayToken]
    mode: DisplayMode = "technical"
    level: RepLevel = "phonemic"
    ref_technical: str = ""
    ref_casual: str = ""
    hyp_technical: str = ""
    hyp_casual: str = ""
    score_color: TokenColor = "green"
    legend: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        """Serializar a dict para respuesta API."""
        return {
            "mode": self.mode,
            "level": self.level,
            "ref_technical": self.ref_technical,
            "ref_casual": self.ref_casual,
            "hyp_technical": self.hyp_technical,
            "hyp_casual": self.hyp_casual,
            "score_color": self.score_color,
            "legend": self.legend or _build_legend(level=self.level),
            "tokens": [
                {
                    "ipa": t.ipa,
                    "casual": t.casual,
                    "color": t.color,
                    "op": t.op,
                    "ref": t.ref,
                    "hyp": t.hyp,
                    "articulatory_distance": t.articulatory_distance,
                    "level": t.level,
                    "is_allophone": t.is_allophone,
                }
                for t in self.tokens
            ],
        }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _to_casual(ipa_token: str) -> str:
    """Transliterar un token IPA a su representación coloquial."""
    if ipa_token in _CASUAL_MAP:
        return _CASUAL_MAP[ipa_token]
    # Para tokens desconocidos, intentar char por char
    result = "".join(_CASUAL_MAP.get(ch, ch) for ch in ipa_token)
    return result or ipa_token


def _compute_color(
    op: str,
    ref: Optional[str],
    hyp: Optional[str],
    *,
    close_threshold: float = COLOR_CLOSE_THRESHOLD,
) -> Tuple[TokenColor, Optional[float]]:
    """Calcular el color y la distancia articulatoria de un EditOp."""
    if op == "eq":
        return "green", 0.0

    if op in ("ins", "del"):
        return "red", None

    # op == "sub"
    if ref is None or hyp is None:
        return "red", None

    # Token OOV / desconocido
    if ref == "?" or hyp == "?":
        return "gray", None

    dist = articulatory_distance(ref, hyp)
    if dist < close_threshold:
        return "yellow", dist
    return "red", dist


def _build_legend(*, level: str = "phonemic") -> dict:
    legend = {
        "green": "Correcto — fonema pronunciado bien",
        "yellow": "Cercano — sustitución articulatoriamente próxima (dist < 0.3)",
        "red": "Error — fonema incorrecto o ausente",
        "gray": "Desconocido — fuera del inventario del pack",
    }
    if level == "phonetic":
        legend["purple"] = "Alófono — variante fonética contextual (b~β, d~ð, g~ɣ, …)"
    return legend


def _score_to_color(score: float) -> TokenColor:
    if score >= 80:
        return "green"
    if score >= 50:
        return "yellow"
    return "red"


def _ipa_str(tokens: Sequence[Optional[str]]) -> str:
    """Construir cadena IPA de una secuencia de tokens opcionales."""
    return " ".join(t for t in tokens if t is not None)


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def build_display(
    ops: Sequence[EditOp],
    *,
    mode: DisplayMode = "technical",
    level: RepLevel = "phonemic",
    score: float = 0.0,
    close_threshold: float = COLOR_CLOSE_THRESHOLD,
) -> IPADisplayResult:
    """Construir la visualización IPA dual a partir de las operaciones de edición.

    Parámetros
    ----------
    ops:
        Lista de operaciones de edición (``EditOp``) del comparador.
    mode:
        Modo de display por defecto: ``"technical"`` o ``"casual"``.
    level:
        Nivel de representación: ``"phonemic"`` o ``"phonetic"``.
        En modo fonético, las sustituciones de pares alofónicos conocidos
        (b~β, d~ð, g~ɣ, r~ɾ, etc.) se colorean como ``purple``.
    score:
        Puntuación numérica (0–100) para calcular ``score_color``.
    close_threshold:
        Umbral articulatorio para distinguir "yellow" de "red".

    Retorna
    -------
    IPADisplayResult
        Objeto con todos los tokens coloreados y transliterados.
    """
    display_tokens: list[IPADisplayToken] = []
    ref_tokens_all: list[Optional[str]] = []
    hyp_tokens_all: list[Optional[str]] = []

    for op_dict in ops:
        op = op_dict.get("op", "eq")  # type: ignore[call-overload]
        ref = op_dict.get("ref")  # type: ignore[call-overload]
        hyp = op_dict.get("hyp")  # type: ignore[call-overload]

        color, dist = _compute_color(op, ref, hyp, close_threshold=close_threshold)

        # En modo fonético, detectar si la sustitución es un par alofónico conocido
        is_allophone = (
            level == "phonetic"
            and op == "sub"
            and ref is not None
            and hyp is not None
            and _is_allophone_pair(ref, hyp)
        )
        if is_allophone:
            color = "purple"

        # Token principal a mostrar (ref para del, hyp para ins, ref para sub/eq)
        display_ipa = ref if op in ("eq", "sub", "del") else hyp
        if display_ipa is None:
            display_ipa = hyp or ref or "?"

        casual = _to_casual(display_ipa)

        display_tokens.append(
            IPADisplayToken(
                ipa=display_ipa,
                casual=casual,
                color=color,
                op=op,
                ref=ref,
                hyp=hyp,
                articulatory_distance=dist,
                level=level,
                is_allophone=is_allophone,
            )
        )

        ref_tokens_all.append(ref)
        hyp_tokens_all.append(hyp)

    # Construir strings de ref y hyp en ambos modos
    ref_ipa_list = [t for t in ref_tokens_all if t is not None]
    hyp_ipa_list = [t for t in hyp_tokens_all if t is not None]

    return IPADisplayResult(
        tokens=display_tokens,
        mode=mode,
        level=level,
        ref_technical=_ipa_str(ref_ipa_list),
        ref_casual=" ".join(_to_casual(t) for t in ref_ipa_list),
        hyp_technical=_ipa_str(hyp_ipa_list),
        hyp_casual=" ".join(_to_casual(t) for t in hyp_ipa_list),
        score_color=_score_to_color(score),
        legend=_build_legend(level=level),
    )


__all__ = [
    "IPADisplayResult",
    "IPADisplayToken",
    "DisplayMode",
    "RepLevel",
    "TokenColor",
    "COLOR_CLOSE_THRESHOLD",
    "build_display",
]
