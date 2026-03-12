"""Punto único de limpieza IPA para tokens de ASR y TextRef.

Centraliza la cadena de limpieza (filter silence + postprocess) para
garantizar IPA puro en todo el pipeline, sin duplicar lógica.
"""
from __future__ import annotations

from typing import List, Optional

from ipa_core.types import Token
from ipa_core.pipeline.postprocess import filter_silence_tokens, postprocess_tokens


def clean_asr_tokens(
    tokens: List[Token],
    *,
    lang: Optional[str] = None,
) -> List[Token]:
    """Limpiar tokens provenientes de ASR.

    Aplica en orden:
    1. Filtrado de marcadores de silencio (sil, sp, etc.)
    2. Postprocesamiento completo: fixes por idioma, colapso de duplicados,
       remoción de artefactos no-IPA.

    Parameters
    ----------
    tokens : list[Token]
        Tokens crudos del backend ASR.
    lang : str, optional
        Código de idioma para normalizaciones específicas.

    Returns
    -------
    list[Token]
        Tokens IPA limpios.
    """
    if not tokens:
        return []
    cleaned = filter_silence_tokens(tokens)
    return postprocess_tokens(
        cleaned,
        lang=lang,
        collapse_duplicates=True,
        strip_artifacts=True,
        apply_lang_fixes=True,
    )


def clean_textref_tokens(
    tokens: List[Token],
    *,
    lang: Optional[str] = None,
    preserve_allophones: bool = False,
) -> List[Token]:
    """Limpiar tokens provenientes de TextRef.

    TextRef (espeak, epitran) produce IPA **fonético** que incluye alófonos
    (β, ð, ɣ) y marcadores de acento (ˈ). Por defecto se normalizan los
    alófonos al fonema canónico para que la comparación sea justa (modo fonémico).
    Las marcas de acento se eliminan en ``filter_silence_tokens``.

    Modo fonémico (``preserve_allophones=False``, defecto):
      - ASR (Allosaurus/spa):  ``"b"``  (fonema)
      - TextRef (eSpeak/es):   ``"β"``  → normalizado a ``"b"``
      - Resultado:             IGUAL, pronunciación correcta puntúa 100 %

    Modo fonético (``preserve_allophones=True``):
      - ASR (Allosaurus/spa):  ``"b"``
      - TextRef (eSpeak/es):   ``"β"``  → se preserva como ``"β"``
      - Resultado:             DIFERENTE — detecta variación alofónica real,
        útil para adopción de dialectos específicos.

    A diferencia de ``clean_asr_tokens``, **no** se colapsan duplicados
    (p. ej. /ll/ geminada en español es legítima).

    Parameters
    ----------
    tokens : list[Token]
        Tokens del proveedor TextRef.
    lang : str, optional
        Código de idioma (para normalización de alófonos y strip de diacríticos).
    preserve_allophones : bool
        Si True, no normaliza alófonos (modo fonético).
        Si False (defecto), normaliza β→b, ð→d, ɣ→ɡ, etc. (modo fonémico).

    Returns
    -------
    list[Token]
        Tokens IPA limpios.
    """
    if not tokens:
        return []
    cleaned = filter_silence_tokens(tokens)
    return postprocess_tokens(
        cleaned,
        lang=lang,
        collapse_duplicates=False,
        strip_artifacts=True,
        apply_lang_fixes=not preserve_allophones,
    )


__all__ = ["clean_asr_tokens", "clean_textref_tokens"]
