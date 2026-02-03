"""Base para plugins del sistema.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from ipa_core.plugins.model_manager import ModelManager


class BasePlugin:
    """Clase base para todos los componentes enchufables.

    Define el ciclo de vida básico (setup/teardown) que el `Kernel` invocará
    al cargar o descargar el plugin.
    
    Los plugins ASR deben declarar su tipo de salida (IPA o texto) mediante
    el atributo `output_type` para que el kernel valide la compatibilidad.
    """
    
    # Declaración de tipo de salida (plugins ASR deben sobrescribir)
    output_type: Literal["ipa", "text", "none"] = "none"

    def __init__(self) -> None:
        self._model_manager: Optional["ModelManager"] = None

    @property
    def model_manager(self) -> ModelManager:
        """Retorna el gestor de modelos, inicializándolo si es necesario."""
        if self._model_manager is None:
            from ipa_core.plugins.model_manager import ModelManager
            self._model_manager = ModelManager()
        return self._model_manager

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
