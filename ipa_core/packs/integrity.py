"""Verificación de integridad de packs mediante checksums SHA256.

Implementa validación de firmas/checksums para Language Packs y Model Packs.
Formato: archivo `checksums.sha256` en el directorio del pack con formato estándar.

Ejemplo de checksums.sha256:
```
a1b2c3...  inventory.yaml
d4e5f6...  phonological_rules.yaml
```
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Nombre del archivo de checksums
CHECKSUMS_FILENAME = "checksums.sha256"


@dataclass
class IntegrityResult:
    """Resultado de la verificación de integridad."""
    
    # ¿Pasó la verificación?
    valid: bool
    
    # Archivos verificados correctamente
    verified_files: List[str] = field(default_factory=list)
    
    # Archivos con checksum incorrecto
    failed_files: List[str] = field(default_factory=list)
    
    # Archivos sin checksum (no verificados)
    unverified_files: List[str] = field(default_factory=list)
    
    # Checksums esperados pero archivos no encontrados
    missing_files: List[str] = field(default_factory=list)
    
    # Mensaje de error (si hay)
    error: Optional[str] = None


def compute_file_sha256(path: Path) -> str:
    """Calcular SHA256 de un archivo.
    
    Args:
        path: Ruta al archivo
        
    Returns:
        Hash SHA256 en hexadecimal (64 chars)
    """
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_checksums(pack_dir: Path) -> Dict[str, str]:
    """Cargar checksums desde archivo checksums.sha256.
    
    Args:
        pack_dir: Directorio del pack
        
    Returns:
        Diccionario {filename: sha256_hash}
        
    Raises:
        FileNotFoundError si no existe el archivo de checksums
    """
    checksums_path = pack_dir / CHECKSUMS_FILENAME
    if not checksums_path.exists():
        raise FileNotFoundError(
            f"No se encontró {CHECKSUMS_FILENAME} en {pack_dir}. "
            "El pack no tiene verificación de integridad."
        )
    
    checksums = {}
    with checksums_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Formato: hash  filename (dos espacios como separador)
            parts = line.split("  ", 1)
            if len(parts) != 2:
                logger.warning(
                    f"{CHECKSUMS_FILENAME}:{line_num}: formato inválido, ignorando"
                )
                continue
            
            hash_val, filename = parts
            if len(hash_val) != 64:
                logger.warning(
                    f"{CHECKSUMS_FILENAME}:{line_num}: hash inválido para {filename}"
                )
                continue
            
            checksums[filename] = hash_val.lower()
    
    return checksums


def verify_pack_integrity(
    pack_dir: Path,
    *,
    strict: bool = False,
    required_files: Optional[List[str]] = None,
) -> IntegrityResult:
    """Verificar integridad de un pack.
    
    Args:
        pack_dir: Directorio del pack
        strict: Si True, falla si hay archivos sin checksum
        required_files: Lista de archivos que deben tener checksum
        
    Returns:
        IntegrityResult con detalles de la verificación
    """
    pack_dir = Path(pack_dir)
    
    # Intentar cargar checksums
    try:
        expected = load_checksums(pack_dir)
    except FileNotFoundError as e:
        return IntegrityResult(
            valid=False,
            error=str(e),
        )
    
    if not expected:
        return IntegrityResult(
            valid=False,
            error=f"{CHECKSUMS_FILENAME} está vacío",
        )
    
    verified = []
    failed = []
    missing = []
    
    # Verificar cada archivo con checksum
    for filename, expected_hash in expected.items():
        file_path = pack_dir / filename
        
        if not file_path.exists():
            missing.append(filename)
            continue
        
        actual_hash = compute_file_sha256(file_path)
        if actual_hash == expected_hash:
            verified.append(filename)
        else:
            failed.append(filename)
            logger.warning(
                f"Checksum incorrecto para {filename}: "
                f"esperado {expected_hash[:16]}..., "
                f"actual {actual_hash[:16]}..."
            )
    
    # Verificar archivos requeridos
    if required_files:
        for required in required_files:
            if required not in expected:
                missing.append(f"{required} (no en checksums)")
    
    # Determinar validez
    is_valid = (
        len(failed) == 0 and
        len(missing) == 0
    )
    
    return IntegrityResult(
        valid=is_valid,
        verified_files=verified,
        failed_files=failed,
        missing_files=missing,
    )


def generate_checksums(
    pack_dir: Path,
    *,
    files: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Generar checksums para archivos de un pack.
    
    Args:
        pack_dir: Directorio del pack
        files: Lista de archivos a incluir (None = todos los .yaml/.json/.onnx)
        
    Returns:
        Diccionario {filename: sha256_hash}
    """
    pack_dir = Path(pack_dir)
    checksums = {}
    
    if files is None:
        # Auto-detectar archivos relevantes
        extensions = {".yaml", ".yml", ".json", ".onnx", ".gguf", ".bin"}
        exclude = {CHECKSUMS_FILENAME, "manifest.yaml", "pack.yaml"}
        
        for file_path in pack_dir.iterdir():
            if file_path.is_file() and file_path.suffix in extensions:
                if file_path.name not in exclude:
                    files = files or []
                    files.append(file_path.name)
    
    for filename in (files or []):
        file_path = pack_dir / filename
        if file_path.exists():
            checksums[filename] = compute_file_sha256(file_path)
    
    return checksums


def write_checksums(pack_dir: Path, checksums: Dict[str, str]) -> Path:
    """Escribir archivo checksums.sha256.
    
    Args:
        pack_dir: Directorio del pack
        checksums: Diccionario {filename: sha256_hash}
        
    Returns:
        Ruta al archivo creado
    """
    checksums_path = pack_dir / CHECKSUMS_FILENAME
    
    with checksums_path.open("w", encoding="utf-8") as f:
        f.write("# PronunciaPA Pack Checksums\n")
        f.write("# Format: sha256_hash  filename\n")
        f.write("# Generated automatically - do not edit\n\n")
        
        for filename in sorted(checksums.keys()):
            hash_val = checksums[filename]
            f.write(f"{hash_val}  {filename}\n")
    
    return checksums_path


__all__ = [
    "IntegrityResult",
    "compute_file_sha256",
    "load_checksums",
    "verify_pack_integrity",
    "generate_checksums",
    "write_checksums",
    "CHECKSUMS_FILENAME",
]
