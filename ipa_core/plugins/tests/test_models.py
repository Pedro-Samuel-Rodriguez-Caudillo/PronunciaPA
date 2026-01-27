"""Tests para el gestor de modelos."""
from __future__ import annotations
import pytest
from ipa_core.plugins.model_manager import ModelManager

@pytest.mark.asyncio
async def test_model_manager_ensure_model_exists(tmp_path) -> None:
    """Verifica que no descarga si el modelo ya existe."""
    manager = ModelManager(cache_dir=tmp_path)
    # El archivo debe estar en el subdirectorio correcto del cache
    model_file = manager.get_file_path("model.bin")
    model_file.touch()
    
    # No debería lanzar error ni llamar a download (que fallaría si el archivo no existe en el origen)
    await manager.ensure_model("model.bin", "http://invalid-url.com")
    assert model_file.exists()

@pytest.mark.asyncio
async def test_model_manager_download_simulation(tmp_path) -> None:
    """Verifica la descarga desde archivo local."""
    manager = ModelManager(cache_dir=tmp_path)
    model_filename = "new_model.bin"
    subdir = "subdir"
    
    # Archivo de origen
    source = tmp_path / "source.bin"
    source.write_bytes(b"data")
    
    # Ejecutar descarga simulada
    await manager.ensure_model(model_filename, source.as_uri(), subdir=subdir)

    model_file = manager.get_file_path(model_filename, subdir)
    assert model_file.exists()
    assert model_file.parent.name == "subdir"
    assert model_file.read_bytes() == b"data"

@pytest.mark.asyncio
async def test_model_manager_fails_no_url(tmp_path) -> None:
    """Verifica error si no hay modelo ni URL."""
    manager = ModelManager(cache_dir=tmp_path)
    
    with pytest.raises(Exception): # ModelDownloadError o FileNotFoundError dependiendo de la implementación
        await manager.ensure_model("missing.bin", "http://non-existent-server/file.bin")
