"""Gestión de alto nivel de plugins.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import sys
import subprocess
from ipa_core.plugins import discovery
from ipa_core.config import loader


@dataclass
class PluginMetadata:
    """Metadatos estandarizados de un plugin."""
    name: str
    category: str
    version: str
    author: str
    description: str
    entry_point: str
    enabled: bool = True


class PluginManager:
    """Gestor central para descubrimiento y configuración de plugins."""
    
    PROTECTED_PACKAGES = {"ipa-core", "pronunciapa", "ipa_core"}

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.config_path = config_path
        self._config = None

    @property
    def config(self):
        """Retorna la configuración cargada."""
        if self._config is None:
            try:
                self._config = loader.load_config(self.config_path)
            except Exception:
                # Fallback a config vacía si no se puede cargar
                from ipa_core.config.schema import AppConfig
                self._config = AppConfig()
        return self._config

    def _is_enabled(self, category: str, name: str) -> bool:
        """Determina si un plugin está habilitado en la configuración actual."""
        cfg = self.config
        
        # Mapeo de categorías a campos en AppConfig
        # asr -> backend
        cat_map = {
            "asr": cfg.backend,
            "textref": cfg.textref,
            "comparator": cfg.comparator,
            "preprocessor": cfg.preprocessor,
            "tts": cfg.tts,
            "llm": cfg.llm,
        }
        
        target_cfg = cat_map.get(category.lower())
        if target_cfg and hasattr(target_cfg, "name"):
            return target_cfg.name == name
            
        return False

    def get_installed_plugins(self) -> List[PluginMetadata]:
        """Retorna una lista de todos los plugins detectados en el entorno."""
        plugins = []
        
        for category, name, ep in discovery.iter_plugin_entry_points():
            meta = self.get_plugin_info(category, name)
            if meta:
                plugins.append(meta)
            
        return plugins

    def get_plugin_info(self, category: str, name: str) -> PluginMetadata | None:
        """Busca y retorna metadatos de un plugin específico."""
        details = discovery.get_plugin_details(category, name)
        if not details:
            return None
            
        return PluginMetadata(
            name=details["name"],
            category=details["category"],
            version=details.get("version", "unknown"),
            author=details.get("author", "unknown"),
            description=details.get("description", ""),
            entry_point=details["entry_point"],
            enabled=self._is_enabled(category, name)
        )

    def install_plugin(self, source: str) -> None:
        """Instala un plugin desde un paquete o fuente."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", source],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error installing plugin: {e.stderr}") from e

    def uninstall_plugin(self, package_name: str) -> None:
        """Desinstala un plugin por su nombre de paquete."""
        if package_name in self.PROTECTED_PACKAGES:
            raise ValueError(f"Cannot uninstall protected package: {package_name}")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", package_name],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error uninstalling plugin: {e.stderr}") from e

