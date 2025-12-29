"""Tests para el gestor de modelos."""
from __future__ import annotations
import pytest
from pathlib import Path
from ipa_core.plugins.models import ModelManager

@pytest.mark.asyncio
async def test_model_manager_ensure_model_exists(tmp_path) -> None:
    """Verifica que no descarga si el modelo ya existe."""
    manager = ModelManager()
    model_file = tmp_path / "model.bin"
    model_file.touch()
    
    # No debería lanzar error ni llamar a download (que dormiría)
    await manager.ensure_model("test", model_file)
    assert model_file.exists()

@pytest.mark.asyncio
async def test_model_manager_download_simulation(tmp_path) -> None:
    """Verifica la simulación de descarga."""
    manager = ModelManager()
    model_file = tmp_path / "subdir" / "new_model.bin"
    
    await manager.ensure_model("test", model_file, download_url="http://example.com")
    
    assert model_file.exists()
    assert model_file.parent.name == "subdir"

@pytest.mark.asyncio
async def test_model_manager_fails_no_url(tmp_path) -> None:
    """Verifica error si no hay modelo ni URL."""
    manager = ModelManager()
    model_file = tmp_path / "missing.bin"
    
    with pytest.raises(FileNotFoundError):
        await manager.ensure_model("test", model_file)
