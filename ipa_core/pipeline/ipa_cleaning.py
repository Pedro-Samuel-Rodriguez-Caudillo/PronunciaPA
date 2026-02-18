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
) -> List[Token]:
    """Limpiar tokens provenientes de TextRef.

    TextRef produce IPA canónico, así que NO aplica fixes por idioma
    ni colapso de duplicados (ej. /ll/ en español es legítimo).
    Solo filtra silencio y artefactos no-IPA.

    Parameters
    ----------
    tokens : list[Token]
        Tokens del proveedor TextRef.
    lang : str, optional
        Código de idioma (usado solo para strip de diacríticos irrelevantes).

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
        apply_lang_fixes=False,
    )


__all__ = ["clean_asr_tokens", "clean_textref_tokens"]
