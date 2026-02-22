"""Generación dinámica de diagramas SVG del tracto vocal.

Produce SVGs simplificados del tracto vocal sagital marcando los
articuladores activos para un fonema IPA dado.  Los diagramas son
útiles para mostrar al estudiante qué partes de la boca/garganta
debe mover para producir un sonido correctamente.

Diseño
------
El SVG base representa un corte sagital del tracto vocal con:
  - Labios (izquierda)
  - Dientes superiores/inferiores
  - Cresta alveolar
  - Paladar duro
  - Paladar blando (velo)
  - Úvula
  - Pared faríngea
  - Glotis y cuerdas vocales
  - Lengua (masa principal)
  - Punta de la lengua

Cada lugar de articulación activa un grupo SVG con resaltado visual
(color rojo/naranja) para indicar dónde se produce el contacto o
constricción principal.

Uso
---
::

    from ipa_core.display.vocal_tract_svg import render_phone_svg
    svg = render_phone_svg("s")   # → str con SVG completo
    with open("s.svg", "w") as f: f.write(svg)
    # También se puede obtener como data URI para incrustar en HTML:
    from ipa_core.display.vocal_tract_svg import phone_svg_data_uri
    uri = phone_svg_data_uri("s")

Limitaciones
------------
- Los diagramas son esquemáticos, no anatómicamente precisos.
- Se incluyen los articuladores más relevantes; no se modela la
  complejidad de articulaciones secundarias (labialización, etc.).
- Para fonemas no reconocidos se retorna el tracto neutral (vocal /ə/).
"""
from __future__ import annotations

import base64
from typing import Optional


# ---------------------------------------------------------------------------
# Configuración de articuladores activos por lugar y modo
# ---------------------------------------------------------------------------

# Coordenadas SVG de referencia de cada articulador en el diagrama sagital.
# El SVG base tiene un viewBox de 0 0 200 220.
# origin (0,0) = top-left; garganta = derecha, labios = izquierda.
_ARTICULATORS: dict[str, dict] = {
    "lips": {
        "cx": 18, "cy": 110, "rx": 10, "ry": 18,
        "label": "Labios",
    },
    "upper_teeth": {
        "x1": 25, "y1": 90, "x2": 40, "y2": 90,
        "label": "Dientes sup.",
    },
    "lower_teeth": {
        "x1": 25, "y1": 125, "x2": 40, "y2": 125,
        "label": "Dientes inf.",
    },
    "alveolar_ridge": {
        "cx": 55, "cy": 75, "rx": 12, "ry": 8,
        "label": "Alveolar",
    },
    "hard_palate": {
        "cx": 90, "cy": 65, "rx": 30, "ry": 7,
        "label": "Paladar duro",
    },
    "soft_palate": {
        "cx": 135, "cy": 68, "rx": 20, "ry": 8,
        "label": "Velo/Paladar blando",
    },
    "uvula": {
        "cx": 158, "cy": 80, "rx": 7, "ry": 10,
        "label": "Úvula",
    },
    "pharynx": {
        "cx": 175, "cy": 110, "rx": 8, "ry": 30,
        "label": "Faringe",
    },
    "glottis": {
        "cx": 178, "cy": 155, "rx": 8, "ry": 12,
        "label": "Glotis",
    },
    "tongue_tip": {
        "cx": 50, "cy": 118, "rx": 16, "ry": 10,
        "label": "Punta lengua",
    },
    "tongue_blade": {
        "cx": 75, "cy": 110, "rx": 18, "ry": 12,
        "label": "Corona",
    },
    "tongue_body": {
        "cx": 105, "cy": 108, "rx": 22, "ry": 14,
        "label": "Cuerpo lengua",
    },
    "tongue_dorsum": {
        "cx": 140, "cy": 105, "rx": 20, "ry": 13,
        "label": "Dorso",
    },
}

# Articuladores activos (resaltados) por lugar de articulación
_PLACE_TO_ARTICULATORS: dict[str, list[str]] = {
    "bilabial":     ["lips"],
    "labiodental":  ["upper_teeth", "lips"],
    "dental":       ["tongue_tip", "upper_teeth", "lower_teeth"],
    "alveolar":     ["tongue_tip", "alveolar_ridge"],
    "postalveolar": ["tongue_blade", "alveolar_ridge"],
    "retroflex":    ["tongue_tip"],  # punta curvada hacia atrás
    "palatal":      ["tongue_body", "hard_palate"],
    "velar":        ["tongue_dorsum", "soft_palate"],
    "uvular":       ["tongue_dorsum", "uvula"],
    "pharyngeal":   ["tongue_dorsum", "pharynx"],
    "glottal":      ["glottis"],
}

# Lugar de articulación por fonema IPA (fonemas representativos)
_PHONE_TO_PLACE: dict[str, str] = {
    "p": "bilabial", "b": "bilabial", "m": "bilabial",
    "f": "labiodental", "v": "labiodental",
    "θ": "dental", "ð": "dental",
    "t": "alveolar", "d": "alveolar", "n": "alveolar",
    "s": "alveolar", "z": "alveolar",
    "l": "alveolar", "r": "alveolar", "ɾ": "alveolar",
    "ʃ": "postalveolar", "ʒ": "postalveolar",
    "tʃ": "postalveolar", "dʒ": "postalveolar",
    "ʈ": "retroflex", "ɖ": "retroflex", "ɽ": "retroflex",
    "ɻ": "retroflex", "ʂ": "retroflex", "ʐ": "retroflex",
    "j": "palatal", "ɲ": "palatal", "ç": "palatal", "ʎ": "palatal",
    "k": "velar", "g": "velar", "ŋ": "velar", "x": "velar", "ɣ": "velar",
    "q": "uvular", "ɢ": "uvular", "ɴ": "uvular", "ʀ": "uvular",
    "χ": "uvular", "ʁ": "uvular",
    "ħ": "pharyngeal", "ʕ": "pharyngeal",
    "h": "glottal", "ʔ": "glottal",
    # Vocales → articulación por posición de lengua
    "i": "palatal", "e": "palatal", "ɛ": "palatal", "æ": "palatal",
    "u": "velar", "o": "velar", "ɔ": "velar", "ʌ": "velar",
    "a": "alveolar", "ɑ": "pharyngeal",
    "ə": "alveolar",  # neutral
    "ɪ": "palatal", "ʊ": "velar",
    "y": "palatal",  # vocal frontal redondeada
}


def _highlight_color(active: bool) -> str:
    return "#e55" if active else "#ddd"


def render_phone_svg(
    phone: str,
    *,
    width: int = 200,
    height: int = 220,
    title: Optional[str] = None,
) -> str:
    """Generar diagrama SVG del tracto vocal para un fonema.

    Parámetros
    ----------
    phone : str
        Símbolo IPA a visualizar.
    width, height : int
        Dimensiones del SVG en píxeles.
    title : str, optional
        Título opcional para incluir en el SVG.

    Retorna
    -------
    str
        Cadena SVG completa lista para renderizar en HTML/navegador.
    """
    place = _PHONE_TO_PLACE.get(phone, "alveolar")
    active_articulators = set(_PLACE_TO_ARTICULATORS.get(place, []))
    phone_title = title or f"/{phone}/ ({place})"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<title>{_esc(phone_title)}</title>',
        # Fondo
        f'<rect width="{width}" height="{height}" fill="#f8f8f8" rx="6"/>',
        # Título
        f'<text x="{width//2}" y="16" text-anchor="middle" '
        f'font-size="12" font-family="sans-serif" fill="#333">{_esc(phone_title)}</text>',
    ]

    # Dibujar articuladores
    for name, props in _ARTICULATORS.items():
        active = name in active_articulators
        fill = "#e55" if active else "#ccc"
        stroke = "#a00" if active else "#999"
        sw = "2.5" if active else "1"

        if "cx" in props:
            parts.append(
                f'<ellipse cx="{props["cx"]}" cy="{props["cy"]}" '
                f'rx="{props["rx"]}" ry="{props["ry"]}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="0.85"/>'
            )
            if active:
                # Etiqueta para articuladores activos
                parts.append(
                    f'<text x="{props["cx"]}" y="{props["cy"] - props["ry"] - 3}" '
                    f'text-anchor="middle" font-size="7" fill="#a00" '
                    f'font-family="sans-serif">{_esc(props["label"])}</text>'
                )
        elif "x1" in props:
            parts.append(
                f'<line x1="{props["x1"]}" y1="{props["y1"]}" '
                f'x2="{props["x2"]}" y2="{props["y2"]}" '
                f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>'
            )

    # Marco de referencia del tracto vocal (silueta simplificada)
    parts.append(
        '<path d="M 15 95 Q 40 60 100 58 Q 155 58 170 80 Q 185 100 185 130 '
        'Q 185 160 180 175 L 30 175 L 30 120 Q 20 115 15 95 Z" '
        'fill="none" stroke="#aaa" stroke-width="1.5" opacity="0.5"/>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def phone_svg_data_uri(phone: str, **kwargs) -> str:
    """Generar data URI del SVG para incrustar en HTML.

    Retorna
    -------
    str
        ``data:image/svg+xml;base64,...``
    """
    svg = render_phone_svg(phone, **kwargs)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def render_minimal_pair_svg(
    phone_a: str,
    phone_b: str,
    *,
    width: int = 420,
    height: int = 220,
) -> str:
    """Generar SVG comparativo dos fonemas lado a lado.

    Útil para visualizar pares mínimos (p.ej. /s/ vs /ʃ/).
    """
    svg_a = render_phone_svg(
        phone_a,
        width=width // 2 - 5,
        height=height,
        title=f"/{phone_a}/",
    )
    svg_b = render_phone_svg(
        phone_b,
        width=width // 2 - 5,
        height=height,
        title=f"/{phone_b}/",
    )

    # SVG contenedor
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">\n'
        f'<foreignObject x="0" y="0" width="{width // 2 - 5}" height="{height}">'
        f"{svg_a}</foreignObject>\n"
        f'<foreignObject x="{width // 2 + 5}" y="0" width="{width // 2 - 5}" height="{height}">'
        f"{svg_b}</foreignObject>\n"
        "</svg>"
    )


def _esc(text: str) -> str:
    """Escapar caracteres especiales XML."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


__all__ = [
    "render_phone_svg",
    "phone_svg_data_uri",
    "render_minimal_pair_svg",
]
