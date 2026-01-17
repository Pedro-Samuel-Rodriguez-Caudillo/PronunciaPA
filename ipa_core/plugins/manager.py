"""Gestión de alto nivel de plugins.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
from ipa_core.plugins import discovery

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
    
    def get_installed_plugins(self) -> List[PluginMetadata]:
        """Retorna una lista de todos los plugins detectados en el entorno."""
        plugins = []
        
        for category, name, ep in discovery.iter_plugin_entry_points():
            # Deducir paquete para metadatos (heurística simple)
            # ep.value suele ser 'package.module:attr'
            package_name = ep.value.split(".")[0].split(":")[0]
            
            raw_meta = discovery.get_package_metadata(package_name)
            
            meta = PluginMetadata(
                name=name,
                category=category,
                version=raw_meta.get("version", "unknown"),
                author=raw_meta.get("author", "unknown"),
                description=raw_meta.get("description", ""),
                entry_point=ep.value,
                enabled=True  # TODO: Check against config in Phase 2
            )
            plugins.append(meta)
            
        return plugins
