"""Jerarquía de errores del microkernel.

Define códigos de error estables y su mapeo HTTP/CLI.
Incluye contexto estructurado (archivo, backend, plugin) en cada excepción.
Separa errores de infraestructura de los de dominio para mensajes más claros.
"""


class KernelError(Exception):
    """Error genérico del microkernel.

    Base para todos los errores propios del proyecto. Úsala para capturar
    problemas comunes sin perder detalle en casos específicos.
    """


class ConfigError(KernelError):
    """Error de configuración o validación del archivo YAML.

    Se lanza cuando faltan claves obligatorias, tipos incorrectos o valores
    fuera de rango en la configuración.
    """


class PluginResolutionError(KernelError):
    """Fallo al resolver un plugin por nombre.

    Indica que el nombre del plugin no existe o no es compatible con el puerto
    solicitado (por ejemplo, se pidió un ASR y hay un TextRef con ese nombre).
    """


class NotReadyError(KernelError):
    """El Kernel o alguna dependencia no está inicializada.

    Útil para asegurar el orden correcto de inicialización antes de ejecutar.
    """


class ValidationError(KernelError):
    """Entrada inválida (por ejemplo, texto vacío o idioma no soportado)."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}


class UnsupportedFormat(KernelError):
    """Formato de archivo o contenido no soportado.

    Se usa cuando el contenedor o la codificación del audio no es reconocida.
    """


class FileNotFound(KernelError):
    """Archivo de audio/texto no encontrado en la ruta indicada."""


class AudioFormatError(KernelError):
    """Error al procesar, decodificar o leer un archivo de audio."""


class ModelLoadError(KernelError):
    """El modelo (ASR, TextRef, TTS, LLM) no se pudo cargar en memoria."""


class LLMAPIError(KernelError):
    """La API del LLM local o remoto falló o retornó datos inválidos."""


class LLMTimeoutError(LLMAPIError):
    """La petición al LLM excedió el tiempo límite."""
