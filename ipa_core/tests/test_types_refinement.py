"""Pruebas para refinamiento de tipos.
"""
from __future__ import annotations
import pytest
from ipa_core import types as T

def test_text_ref_result_exists() -> None:
    """Verifica que TextRefResult esté definido (falla si no existe)."""
    # Intentamos instanciarlo. Si no existe en T, esto fallará.
    res = T.TextRefResult(tokens=["a", "b"], meta={"source": "epitran"})
    assert res["tokens"] == ["a", "b"]

def test_preprocessor_result_exists() -> None:
    """Verifica que PreprocessorResult esté definido (opcional pero bueno para consistencia)."""
    # Si decidimos que Preprocessor devuelve un resultado con meta.
    res = T.PreprocessorResult(audio=T.AudioInput(path="p", sample_rate=1, channels=1), meta={})
    assert res["audio"]["path"] == "p"

def test_token_is_str() -> None:
    assert T.Token is str

def test_token_seq_is_sequence() -> None:
    # TokenSeq debe ser Sequence[Token]
    from typing import Sequence
    # Esto es una comprobación de tipo estática principalmente, 
    # pero podemos verificar la definición si es posible.
    assert T.TokenSeq == Sequence[T.Token]
