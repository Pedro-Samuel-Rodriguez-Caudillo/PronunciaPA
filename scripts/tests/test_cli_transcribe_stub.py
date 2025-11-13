"""Prueba del stub de cli_transcribe.

Objetivo: Verificar que cli_transcribe existe y retorna tokens sin lanzar errores.
"""
from __future__ import annotations

from ipa_core.api.cli import cli_transcribe


def test_cli_transcribe_exists_and_returns_tokens() -> None:
    """Verificar que cli_transcribe existe y retorna una lista de strings."""
    # Llamar al stub con parámetros mínimos
    result = cli_transcribe(audio="dummy.wav", lang="es")
    
    # Verificar que retorna una lista
    assert isinstance(result, list), "cli_transcribe debe retornar una lista"
    
    # Verificar que la lista contiene strings (tokens)
    assert all(isinstance(token, str) for token in result), "Todos los tokens deben ser strings"
    
    # Verificar que retorna al menos un token
    assert len(result) > 0, "cli_transcribe debe retornar al menos un token"
    
    print(f"✓ cli_transcribe retornó {len(result)} tokens: {result}")


if __name__ == "__main__":
    test_cli_transcribe_exists_and_returns_tokens()
    print("\n✅ Todas las pruebas pasaron correctamente")
