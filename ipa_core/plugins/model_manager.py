"""Gestor de modelos y recursos externos.

Este módulo se encarga de gestionar la descarga, almacenamiento en caché
y recuperación de rutas de modelos y recursos necesarios para los plugins.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Optional
from urllib.request import urlretrieve

from ipa_core.errors import KernelError

logger = logging.getLogger(__name__)


class ModelDownloadError(KernelError):
    """Error al descargar un modelo o recurso."""

# Catálogo de modelos conocidos y probados para el sistema
MODEL_CATALOG = {
    "allosaurus": {
        "url": "https://github.com/xinjli/allosaurus/releases/download/v1.0/eng2102.pt",
        "filename": "allosaurus_eng2102.pt",
        "description": "Modelo fonético universal (Allosaurus)",
    },
    "llama": {
        "url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "filename": "llama-3.2-1b-instruct-q4_k_m.gguf",
        "description": "Llama 3.2 1B Instruct (GGUF Q4_K_M) - Rápido en CPU",
    },
    "qwen": {
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "description": "Qwen 2.5 1.5B Instruct (GGUF Q4_K_M) - Buen balance multilingüe",
    },
    "phi": {
        "url": "https://huggingface.co/microsoft/Phi-3.5-mini-instruct-gguf/resolve/main/Phi-3.5-mini-instruct-q4_k_m.gguf",
        "filename": "phi-3.5-mini-instruct-q4_k_m.gguf",
        "description": "Phi-3.5 Mini Instruct (GGUF Q4_K_M) - Alta calidad de razonamiento",
    },
    "whisper-tiny": {
        "url": "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
        "filename": "whisper_tiny.pt",
        "description": "OpenAI Whisper Tiny (PyTorch)",
    },
}

class ModelManager:
    """Gestor de ciclo de vida de archivos de modelos.

    Provee utilidades para que los plugins no tengan que reimplementar
    lógica de descarga y gestión de rutas.
    """

    def __init__(self, cache_dir: Optional[str | Path] = None) -> None:
        """Inicializa el gestor.

        Args:
            cache_dir: Ruta base para guardar modelos. Si es None, usa
                       ~/.cache/pronunciapa/models (o equivalente en OS).
        """
        if cache_dir:
            self.base_path = Path(cache_dir)
        else:
            # XDG Cache Home o default
            xdg_cache = os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
            self.base_path = Path(xdg_cache) / "pronunciapa" / "models"

        self._ensure_base_path()

    def _ensure_base_path(self) -> None:
        """Asegura que el directorio base exista."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_file_path(self, filename: str, subdir: str = "") -> Path:
        """Obtiene la ruta absoluta esperada para un archivo.

        No garantiza que el archivo exista.
        """
        target_dir = self.base_path / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename

    async def download_model(
        self,
        name: str,
        url: Optional[str] = None,
        dest: Optional[Path] = None,
        sha256: Optional[str] = None,
    ) -> Path:
        """Descarga un modelo de forma asíncrona (compatible con plugins).

        Si 'url' no se provee, intenta buscar 'name' en el MODEL_CATALOG.
        """
        # 1. Resolver URL y destino si es un modelo conocido
        if not url and name in MODEL_CATALOG:
            entry = MODEL_CATALOG[name]
            url = entry["url"]
            if not dest:
                # Por defecto guardar en el root del cache si no se especifica
                dest = self.get_file_path(entry["filename"])
            logger.info(f"Resolviendo modelo '{name}': {entry['description']}")

        if not url:
            raise ValueError(f"URL no proporcionada y el modelo '{name}' no está en el catálogo.")

        if not dest:
            # Fallback: usar el nombre del archivo de la URL o el nombre del modelo
            filename = url.split("/")[-1] or f"{name}.bin"
            dest = self.get_file_path(filename)

        # 2. Ejecutar descarga en un hilo para no bloquear el loop asíncrono
        return await asyncio.to_thread(
            self._download_sync, url, dest, sha256
        )

    def _download_sync(self, url: str, dest: Path, sha256: Optional[str]) -> Path:
        """Lógica síncrona de descarga y verificación."""
        if dest.exists():
            if sha256:
                if self._verify_hash(dest, sha256, algo="sha256"):
                    logger.debug(f"Modelo verificado (SHA256): {dest}")
                    return dest
                logger.warning(f"Hash SHA256 inválido para {dest.name}, re-descargando...")
            else:
                logger.debug(f"Modelo existente (sin verificación): {dest}")
                return dest

        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Descargando {url} -> {dest}...")
        
        try:
            urlretrieve(url, str(dest))
        except Exception as e:
            # Limpiar descarga parcial si falla
            if dest.exists():
                dest.unlink()
            raise ModelDownloadError(f"Fallo al descargar {url}: {e}") from e

        if sha256 and not self._verify_hash(dest, sha256, algo="sha256"):
            dest.unlink()  # Eliminar archivo corrupto
            raise ModelDownloadError(f"Hash SHA256 no coincide para {dest.name}")

        return dest

    def ensure_model(
        self,
        filename: str,
        url: str,
        subdir: str = "",
        md5_hash: Optional[str] = None,
        force_download: bool = False,
    ) -> Path:
        """Garantiza que un modelo esté disponible localmente (Síncrono/Legacy).

        Si no existe, lo descarga.

        Args:
            filename: Nombre del archivo local.
            url: URL desde donde descargar.
            subdir: Subdirectorio dentro del caché para organizar modelos.
            md5_hash: Hash MD5 opcional para verificar integridad.
            force_download: Si es True, descarga aunque exista.

        Returns:
            Path: Ruta al archivo local listo para usar.
        """
        file_path = self.get_file_path(filename, subdir)

        if file_path.exists() and not force_download:
            if md5_hash:
                if self._verify_hash(file_path, md5_hash):
                    logger.debug(f"Modelo encontrado y verificado: {file_path}")
                    return file_path
                logger.warning(f"Hash inválido para {filename}, re-descargando...")
            else:
                logger.debug(f"Modelo encontrado (sin verificación): {file_path}")
                return file_path

        logger.info(f"Descargando recurso {filename} desde {url}...")
        try:
            # TODO: Implementar barra de progreso si se desea UX mejorada
            urlretrieve(url, str(file_path))
        except Exception as e:
            raise ModelDownloadError(f"Fallo al descargar {url}: {e}") from e

        if md5_hash and not self._verify_hash(file_path, md5_hash):
            raise ModelDownloadError(f"Hash MD5 no coincide para {filename}")

        return file_path

    def _verify_hash(self, path: Path, expected_hash: str, algo: str = "md5") -> bool:
        """Verifica el hash de un archivo."""
        if algo == "sha256":
            hasher = hashlib.sha256()
        else:
            hasher = hashlib.md5()
            
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest() == expected_hash