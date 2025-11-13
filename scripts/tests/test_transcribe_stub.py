"""Prueba del pipeline transcribe con componentes stub.

Objetivo: Verificar que la función transcribe se puede importar y ejecutar
con implementaciones básicas de Preprocessor, ASR y TextRef.
"""
from __future__ import annotations

from typing import Optional

from ipa_core.pipeline.transcribe import transcribe
from ipa_core.types import ASRResult, AudioInput, Token, TokenSeq


# ========== Implementaciones stub para testing ==========

class BasicPreprocessor:
    """Preprocessor básico para pruebas."""

    def process_audio(self, audio: AudioInput) -> AudioInput:
        """Validar y retornar audio sin modificaciones."""
        assert "path" in audio, "AudioInput debe tener 'path'"
        assert "sample_rate" in audio, "AudioInput debe tener 'sample_rate'"
        assert "channels" in audio, "AudioInput debe tener 'channels'"
        return audio

    def normalize_tokens(self, tokens: TokenSeq) -> list[Token]:
        """Normalizar tokens: strip, lower, filtrar vacíos."""
        return [t.strip().lower() for t in tokens if t.strip()]


class StubASR:
    """Backend ASR stub que retorna tokens de ejemplo."""

    def __init__(self, return_tokens: bool = True):
        """Inicializar stub.
        
        Args:
            return_tokens: Si True, retorna tokens. Si False, retorna raw_text.
        """
        self.return_tokens = return_tokens

    def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult:
        """Retornar resultado ASR de ejemplo."""
        if self.return_tokens:
            return {"tokens": ["ˈo", "l", "a"]}  # "hola" en IPA simplificado
        else:
            return {"raw_text": "hola"}


class StubTextRef:
    """TextRef stub que convierte texto a tokens IPA de ejemplo."""

    def to_ipa(self, text: str, *, lang: str, **kw) -> list[Token]:
        """Convertir texto a tokens IPA de ejemplo."""
        # Para testing: simplemente dividir por caracteres y agregar marcas IPA
        if text.lower() == "hola":
            return ["ˈo", "l", "a"]
        # Fallback genérico
        return [f"/{c}/" for c in text if c.strip()]


# ========== Tests ==========

def test_transcribe_with_tokens() -> None:
    """Probar transcribe cuando ASR retorna tokens directamente."""
    pre = BasicPreprocessor()
    asr = StubASR(return_tokens=True)
    textref = StubTextRef()
    
    audio: AudioInput = {
        "path": "dummy.wav",
        "sample_rate": 16000,
        "channels": 1
    }
    
    result = transcribe(pre, asr, textref, audio=audio, lang="es")
    
    assert isinstance(result, list), "transcribe debe retornar una lista"
    assert len(result) > 0, "transcribe debe retornar al menos un token"
    assert all(isinstance(t, str) for t in result), "Todos los tokens deben ser strings"
    
    print(f"✓ transcribe con tokens: {result}")


def test_transcribe_with_raw_text() -> None:
    """Probar transcribe cuando ASR retorna raw_text que necesita conversión."""
    pre = BasicPreprocessor()
    asr = StubASR(return_tokens=False)
    textref = StubTextRef()
    
    audio: AudioInput = {
        "path": "dummy.wav",
        "sample_rate": 16000,
        "channels": 1
    }
    
    result = transcribe(pre, asr, textref, audio=audio, lang="es")
    
    assert isinstance(result, list), "transcribe debe retornar una lista"
    assert len(result) > 0, "transcribe debe retornar al menos un token"
    
    print(f"✓ transcribe con raw_text: {result}")


def test_transcribe_normalization() -> None:
    """Verificar que la normalización funciona correctamente."""
    pre = BasicPreprocessor()
    
    # Probar normalización con espacios y mayúsculas
    tokens = [" A ", "B", "  ", "c", "D  "]
    normalized = pre.normalize_tokens(tokens)
    
    assert normalized == ["a", "b", "c", "d"], f"Normalización incorrecta: {normalized}"
    print(f"✓ Normalización: {tokens} -> {normalized}")


if __name__ == "__main__":
    test_transcribe_normalization()
    test_transcribe_with_tokens()
    test_transcribe_with_raw_text()
    print("\n✅ Todas las pruebas del pipeline transcribe pasaron correctamente")
