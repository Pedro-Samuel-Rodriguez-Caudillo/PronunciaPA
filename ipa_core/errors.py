class KernelError(Exception):
    """Error genérico del microkernel."""


class ConfigError(KernelError):
    """Errores en configuración o validación."""


class PluginResolutionError(KernelError):
    """Fallo al resolver un plugin por nombre."""


class NotReadyError(KernelError):
    """Kernel o dependencia no inicializada."""


class ValidationError(KernelError):
    """Entrada inválida (p. ej., texto/lenguaje requerido)."""


class UnsupportedFormat(KernelError):
    """Formato de archivo o contenido no soportado."""


class FileNotFound(KernelError):
    """Archivo de audio/texto no encontrado."""
"""Jerarquía de errores del microkernel.

TODO
----
- Definir códigos de error estables y su mapeo HTTP/CLI (Observer para logging).
- Incluir contexto estructurado (archivo, backend, plugin) en cada excepción.
- Separar errores de infraestructura de los de dominio para mensajes más claros.
"""
