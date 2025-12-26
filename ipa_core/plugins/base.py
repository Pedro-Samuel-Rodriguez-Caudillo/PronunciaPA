"""Base para plugins del sistema.
"""
from __future__ import annotations


class BasePlugin:
    """Clase base para todos los componentes enchufables.

    Define el ciclo de vida básico (setup/teardown) que el `Kernel` invocará
    al cargar o descargar el plugin.
    """

    async def setup(self) -> None:
        """Configuración inicial del plugin.
        
        Puede usarse para cargar modelos, abrir conexiones o inicializar
        estado interno de forma asíncrona.
        """
        pass

    async def teardown(self) -> None:
        """Limpieza de recursos del plugin.
        
        Invocado antes de que el sistema se apague o el plugin sea descargado.
        """
        pass
