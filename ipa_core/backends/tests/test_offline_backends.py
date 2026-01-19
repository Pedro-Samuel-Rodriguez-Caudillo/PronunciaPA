"""Tests para backends offline (Wav2Vec2, Vosk).

Estos tests verifican la estructura de los backends sin requerir
los modelos descargados. Los tests de integración requieren modelos.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch


class TestWav2Vec2Backend:
    """Tests para Wav2Vec2Backend."""
    
    def test_import(self) -> None:
        """Backend se puede importar."""
        from ipa_core.backends.wav2vec2_backend import Wav2Vec2Backend, MODEL_REGISTRY
        assert Wav2Vec2Backend is not None
        assert "en" in MODEL_REGISTRY
    
    def test_for_language(self) -> None:
        """for_language() crea backend con modelo correcto."""
        from ipa_core.backends.wav2vec2_backend import Wav2Vec2Backend, MODEL_REGISTRY
        backend = Wav2Vec2Backend.for_language("en")
        assert backend._model_name == MODEL_REGISTRY["en"]
    
    def test_not_ready_before_setup(self) -> None:
        """Backend no está listo antes de setup."""
        from ipa_core.backends.wav2vec2_backend import Wav2Vec2Backend
        backend = Wav2Vec2Backend()
        assert not backend._ready


class TestVoskBackend:
    """Tests para VoskBackend."""
    
    def test_import(self) -> None:
        """Backend se puede importar."""
        from ipa_core.backends.vosk_backend import VoskBackend, VOSK_MODELS
        assert VoskBackend is not None
        assert "es" in VOSK_MODELS
    
    def test_not_ready_before_setup(self) -> None:
        """Backend no está listo antes de setup."""
        from ipa_core.backends.vosk_backend import VoskBackend
        backend = VoskBackend(model_path=Path("/tmp/fake"))
        assert not backend._ready


# Tests de integración (requieren modelos)
@pytest.mark.skip(reason="Requires Wav2Vec2 model download")
class TestWav2Vec2Integration:
    """Tests de integración para Wav2Vec2."""
    
    @pytest.mark.asyncio
    async def test_transcribe(self, tmp_path: Path) -> None:
        """Transcribir audio real."""
        from ipa_core.backends.wav2vec2_backend import Wav2Vec2Backend
        backend = Wav2Vec2Backend.for_language("en")
        await backend.setup()
        # Aquí se usaría un archivo de audio real
        await backend.teardown()
