"""Utilidades para la gestión de modelos y activos de plugins."""
from __future__ import annotations

import asyncio
import os
import hashlib
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


class ModelManager:
    """Gestiona la descarga y verificación de modelos para plugins."""

    async def ensure_model(
        self,
        name: str,
        local_path: Path,
        download_url: str | None = None,
        sha256: str | None = None,
    ) -> None:
        """Verifica si un modelo existe localmente y lo descarga si no."""
        if local_path.exists():
            return
        if not download_url:
            raise FileNotFoundError(
                f"El modelo '{name}' no se encuentra en {local_path} y no se proporcionó URL de descarga."
            )
        await self.download_model(name, download_url, local_path, sha256=sha256)

    async def download_model(self, name: str, url: str, dest: Path, *, sha256: str | None = None) -> None:
        """Descarga un modelo desde HTTP(S) o ruta local."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._download_model_sync, name, url, dest, sha256)

    @staticmethod
    def _download_model_sync(name: str, url: str, dest: Path, sha256: str | None) -> None:
        local_candidate = Path(url)
        if local_candidate.exists():
            shutil.copyfile(local_candidate, dest)
            if sha256:
                ModelManager._verify_sha256(dest, sha256)
            return

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme == "file":
            source = Path(urllib.request.url2pathname(parsed.path))
            if not source.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {source}")
            shutil.copyfile(source, dest)
            if sha256:
                ModelManager._verify_sha256(dest, sha256)
            return

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PronunciaPA/0.1 (http://github.com/pronunciapa)"}
        )
        with urllib.request.urlopen(req) as response:
            fd, tmp_path = tempfile.mkstemp(prefix="pronunciapa_model_", suffix=dest.suffix)
            with os.fdopen(fd, "wb") as tmp:
                hasher = hashlib.sha256() if sha256 else None
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    if hasher:
                        hasher.update(chunk)
            if sha256 and hasher:
                if hasher.hexdigest().lower() != sha256.lower():
                    raise ValueError(f"SHA256 inválido para {name}")
            shutil.move(tmp_path, dest)

    @staticmethod
    def _verify_sha256(path: Path, expected: str) -> None:
        hasher = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                hasher.update(chunk)
        if hasher.hexdigest().lower() != expected.lower():
            raise ValueError(f"SHA256 inválido para {path}")


__all__ = ["ModelManager"]
