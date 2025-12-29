"""Utilidades para la gestión de modelos y activos de plugins."""
from __future__ import annotations
import asyncio
from pathlib import Path
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn

class ModelManager:
    """Gestiona la descarga y verificación de modelos para plugins."""

    async def ensure_model(self, name: str, local_path: Path, download_url: str | None = None) -> None:
        """Verifica si un modelo existe localmente y lo descarga si no."""
        if local_path.exists():
            return

        if not download_url:
            raise FileNotFoundError(f"El modelo '{name}' no se encuentra en {local_path} y no se proporcionó URL de descarga.")

        await self.download_model(name, download_url, local_path)

    async def download_model(self, name: str, url: str, dest: Path) -> None:
        """Simula la descarga de un modelo con una barra de progreso de Rich."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Simulación de descarga con progreso
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            task = progress.add_task(f"Descargando {name}...", total=100)
            
            # Simulamos fragmentos de descarga
            for _ in range(10):
                await asyncio.sleep(0.2) # Simular red
                progress.update(task, advance=10)
        
        # Crear archivo vacío para simular que ya existe
        dest.touch()
