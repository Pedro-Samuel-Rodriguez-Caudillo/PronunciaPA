"""Tests para verificación de integridad de packs."""
import os
import tempfile
from pathlib import Path

import pytest

from ipa_core.packs.integrity import (
    compute_file_sha256,
    generate_checksums,
    load_checksums,
    verify_pack_integrity,
    write_checksums,
    IntegrityResult,
    CHECKSUMS_FILENAME,
)


def _create_temp_pack(files: dict[str, str]) -> Path:
    """Crear pack temporal con archivos dados."""
    temp_dir = tempfile.mkdtemp(prefix="test_pack_")
    for filename, content in files.items():
        with open(os.path.join(temp_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)
    return Path(temp_dir)


class TestComputeSHA256:
    """Tests para cálculo de SHA256."""
    
    def test_consistent_hash(self):
        """Mismo contenido produce mismo hash."""
        pack = _create_temp_pack({"test.yaml": "hello world"})
        try:
            hash1 = compute_file_sha256(pack / "test.yaml")
            hash2 = compute_file_sha256(pack / "test.yaml")
            assert hash1 == hash2
            assert len(hash1) == 64
        finally:
            import shutil
            shutil.rmtree(pack)
    
    def test_different_content_different_hash(self):
        """Contenido diferente produce hash diferente."""
        pack = _create_temp_pack({
            "a.yaml": "content a",
            "b.yaml": "content b",
        })
        try:
            hash_a = compute_file_sha256(pack / "a.yaml")
            hash_b = compute_file_sha256(pack / "b.yaml")
            assert hash_a != hash_b
        finally:
            import shutil
            shutil.rmtree(pack)


class TestVerifyIntegrity:
    """Tests para verificación de integridad."""
    
    def test_valid_pack(self):
        """Pack con checksums correctos pasa verificación."""
        pack = _create_temp_pack({
            "data.yaml": "test content",
            "rules.yaml": "more content",
        })
        try:
            # Generar y escribir checksums
            checksums = generate_checksums(pack)
            write_checksums(pack, checksums)
            
            # Verificar
            result = verify_pack_integrity(pack)
            assert result.valid is True
            assert len(result.verified_files) == 2
            assert len(result.failed_files) == 0
        finally:
            import shutil
            shutil.rmtree(pack)
    
    def test_modified_file_fails(self):
        """Archivo modificado falla verificación."""
        pack = _create_temp_pack({
            "data.yaml": "original content",
        })
        try:
            # Generar checksums
            checksums = generate_checksums(pack)
            write_checksums(pack, checksums)
            
            # Modificar archivo
            with open(pack / "data.yaml", "w") as f:
                f.write("modified content")
            
            # Verificar debe fallar
            result = verify_pack_integrity(pack)
            assert result.valid is False
            assert "data.yaml" in result.failed_files
        finally:
            import shutil
            shutil.rmtree(pack)
    
    def test_missing_checksums_file(self):
        """Pack sin checksums.sha256 falla."""
        pack = _create_temp_pack({"data.yaml": "content"})
        try:
            result = verify_pack_integrity(pack)
            assert result.valid is False
            assert "No se encontró" in result.error
        finally:
            import shutil
            shutil.rmtree(pack)
    
    def test_missing_file_fails(self):
        """Archivo faltante falla verificación."""
        pack = _create_temp_pack({
            "data.yaml": "content",
        })
        try:
            checksums = {"data.yaml": compute_file_sha256(pack / "data.yaml")}
            checksums["missing.yaml"] = "a" * 64  # Hash falso
            write_checksums(pack, checksums)
            
            result = verify_pack_integrity(pack)
            assert result.valid is False
            assert "missing.yaml" in result.missing_files
        finally:
            import shutil
            shutil.rmtree(pack)


class TestRealPacks:
    """Tests con packs reales del proyecto."""
    
    def test_verify_es_mx(self):
        """Verificar pack es-mx existente."""
        pack_dir = Path(__file__).parents[3] / "plugins" / "language_packs" / "es-mx"
        if not (pack_dir / CHECKSUMS_FILENAME).exists():
            pytest.skip("checksums.sha256 no generado aún")
        
        result = verify_pack_integrity(pack_dir)
        assert result.valid is True
    
    def test_verify_en_us(self):
        """Verificar pack en-us existente."""
        pack_dir = Path(__file__).parents[3] / "plugins" / "language_packs" / "en-us"
        if not (pack_dir / CHECKSUMS_FILENAME).exists():
            pytest.skip("checksums.sha256 no generado aún")
        
        result = verify_pack_integrity(pack_dir)
        assert result.valid is True
