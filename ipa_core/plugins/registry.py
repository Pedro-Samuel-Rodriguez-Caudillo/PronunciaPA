"""Registro y resolución de plugins.

Este módulo permite registrar y obtener implementaciones de los puertos
del sistema (ASR, TextRef, Comparator, Preprocessor, TTS).
"""
from __future__ import annotations
import logging
from typing import Any, Callable, Dict, Optional
from ipa_core.plugins import discovery

logger = logging.getLogger(__name__)

# Diccionario global de plugins: { categoria: { nombre: factory } }
_REGISTRY: Dict[str, Dict[str, Callable[[Any], Any]]] = {
    "asr": {},
    "textref": {},
    "comparator": {},
    "preprocessor": {},
    "tts": {},
    "llm": {},
}

_DISCOVERY_DONE = False


def register(category: str, name: str, factory: Callable[[Any], Any]) -> None:
    """Registra un nuevo plugin en una categoría."""
    if category not in _REGISTRY:
        raise ValueError(f"Categoría de plugin inválida: {category}")
    _REGISTRY[category][name] = factory


def register_discovered_plugins() -> None:
    """Escanea y registra plugins desde entry points.
    
    Idempotente si se llama varias veces, pero re-escanea entry points.
    """
    global _DISCOVERY_DONE
    for category, name, ep in discovery.iter_plugin_entry_points():
        if category not in _REGISTRY:
            continue
            
        try:
            plugin_cls = ep.load()
            # Factory wrapper capturando la clase
            def factory(params: dict[str, Any], cls=plugin_cls) -> Any:
                return cls(params)
            
            register(category, name, factory)
        except Exception as e:
            logger.warning(f"Error cargando plugin {category}.{name}: {e}")
            
    _DISCOVERY_DONE = True


def resolve(category: str, name: str, params: Optional[Dict[str, Any]] = None, *, strict_mode: bool = False) -> Any:
    """Resuelve e instancia un plugin por categoría y nombre.
    
    Args:
        category: Categoría del plugin (asr, textref, etc.)
        name: Nombre del plugin a resolver
        params: Parámetros de inicialización
        strict_mode: Si True, falla en errores. Si False, usa fallbacks automáticos.
    
    Returns:
        Instancia del plugin
        
    Raises:
        KeyError: Si plugin no existe y strict_mode=True
        NotReadyError: Si plugin no está listo y strict_mode=True
    """
    if category not in _REGISTRY:
        raise ValueError(f"Categoría de plugin inválida: {category}")
    
    if name not in _REGISTRY[category]:
        # Intentar cargar defaults si el registro está vacío
        if not _REGISTRY[category]:
            _register_defaults()
            
        # Si aún no está, intentar descubrimiento si no se ha hecho
        if name not in _REGISTRY[category] and not _DISCOVERY_DONE:
            register_discovered_plugins()
            
    if name not in _REGISTRY[category]:
        if strict_mode:
            raise KeyError(f"Plugin '{name}' no encontrado en categoría '{category}'")
        # Auto-fallback: Intentar con stub/default según categoría
        logger.warning(f"⚠️ Plugin '{name}' no encontrado en '{category}'. Usando fallback automático.")
        fallback_name = _get_fallback(category)
        if fallback_name and fallback_name in _REGISTRY[category]:
            name = fallback_name
        else:
            raise KeyError(f"Plugin '{name}' no encontrado y sin fallback disponible en '{category}'")
    
    factory = _REGISTRY[category][name]
    return factory(params or {})


def _register_defaults() -> None:
    """Registra las implementaciones por defecto incluidas en el core."""
    # ASR - Stub (default ligero)
    from ipa_core.backends.asr_stub import StubASR
    register("asr", "stub", StubASR)
    register("asr", "fake", StubASR)
    register("asr", "default", StubASR)  # En el core ligero, el default es el stub
    
    # ASR - ONNX
    try:
        from ipa_core.plugins.asr_onnx import ONNXASRPlugin
    except Exception as exc:
        logger.warning("ONNX ASR plugin unavailable: %s", exc)
    else:
        register("asr", "onnx", lambda p: ONNXASRPlugin(p))
        register("asr", "whisper_onnx", lambda p: ONNXASRPlugin(p))
        register("asr", "whisper", lambda p: ONNXASRPlugin(p))
    
    # ASR - Allosaurus (IPA directo)
    try:
        from ipa_plugin_allosaurus.backend import AllosaurusASR  # type: ignore[import-not-found]
    except Exception as exc:
        logger.warning("Allosaurus ASR plugin unavailable: %s", exc)
    else:
        register("asr", "allosaurus", lambda p: AllosaurusASR(p))
    
    # ASR - Backend IPA unificado (allosaurus, wav2vec2-ipa, xlsr-ipa)
    try:
        from ipa_core.backends.unified_ipa_backend import UnifiedIPABackend
    except Exception as exc:
        logger.warning("Unified IPA backend unavailable: %s", exc)
    else:
        # Factory que crea y configura el backend
        def create_unified_backend(p: dict):
            engine = p.get("engine", "allosaurus")
            device = p.get("device", "cpu")
            allosaurus_lang = p.get("allosaurus_lang", "uni2005")
            return UnifiedIPABackend(
                engine=engine,
                device=device,
                allosaurus_lang=allosaurus_lang,
            )
        
        register("asr", "unified_ipa", create_unified_backend)
        register("asr", "wav2vec2-ipa", lambda p: UnifiedIPABackend(engine="wav2vec2-ipa", device=p.get("device", "cpu")))
        register("asr", "xlsr-ipa", lambda p: UnifiedIPABackend(engine="xlsr-ipa", device=p.get("device", "cpu")))

    # TextRef
    from ipa_core.textref.espeak import EspeakTextRef
    from ipa_core.textref.simple import GraphemeTextRef
    register("textref", "grapheme", lambda _: GraphemeTextRef())
    register("textref", "default", lambda _: GraphemeTextRef())
    try:
        from ipa_core.textref.epitran import EpitranTextRef
    except Exception as exc:
        logger.warning("Epitran TextRef unavailable: %s", exc)
    else:
        register("textref", "epitran", lambda p: EpitranTextRef(default_lang=p.get("default_lang", "es")))
    register("textref", "espeak", lambda p: EspeakTextRef(default_lang=p.get("default_lang", "es")))

    # Comparator
    from ipa_core.compare.levenshtein import LevenshteinComparator
    from ipa_core.compare.noop import NoOpComparator
    register("comparator", "levenshtein", lambda _: LevenshteinComparator(use_articulatory=True))
    register("comparator", "default", lambda _: LevenshteinComparator(use_articulatory=True))
    register("comparator", "noop", lambda _: NoOpComparator())

    # Preprocessor
    from ipa_core.preprocessor_basic import BasicPreprocessor
    register("preprocessor", "basic", lambda _: BasicPreprocessor())
    register("preprocessor", "default", lambda _: BasicPreprocessor())

    # TTS
    try:
        from ipa_core.tts.adapter import TTSAdapter
        from ipa_core.tts.piper import PiperTTS
        from ipa_core.tts.system import SystemTTS
    except Exception as exc:
        logger.warning("TTS adapters unavailable: %s", exc)
    else:
        register("tts", "default", lambda p: TTSAdapter(p))
        register("tts", "piper", lambda p: PiperTTS(p))
        register("tts", "system", lambda p: SystemTTS(p))

    # LLM
    from ipa_core.llm.stub import StubLLMAdapter
    register("llm", "stub", lambda p: StubLLMAdapter(p))
    try:
        from ipa_core.llm.llama_cpp import LlamaCppAdapter
        from ipa_core.llm.onnx import OnnxLLMAdapter
        from ipa_core.llm.ollama import OllamaAdapter
    except Exception as exc:
        logger.warning("LLM adapters unavailable: %s", exc)
    else:
        register("llm", "llama_cpp", lambda p: LlamaCppAdapter(p))
        register("llm", "onnx", lambda p: OnnxLLMAdapter(p))
        register("llm", "ollama", lambda p: OllamaAdapter(p))
        register("llm", "default", lambda p: OllamaAdapter(p))  # Ollama as default

    # También ejecutar descubrimiento inicial
    register_discovered_plugins()


def _get_fallback(category: str) -> Optional[str]:
    """Retorna el nombre de fallback recomendado para cada categoría."""
    fallbacks = {
        "asr": "stub",
        "textref": "grapheme",
        "comparator": "levenshtein",
        "preprocessor": "basic",
        "tts": "default",
        "llm": "stub",
    }
    return fallbacks.get(category)


# Resolutores específicos por compatibilidad
def resolve_asr(name: str, params: Optional[Dict[str, Any]] = None, *, strict_mode: bool = False) -> Any:
    """Resuelve backend ASR con auto-fallback opcional.
    
    Si strict_mode=False y el backend falla al inicializarse (NotReadyError),
    retorna automáticamente StubASR y loguea advertencia.
    """
    from ipa_core.errors import NotReadyError
    
    try:
        instance = resolve("asr", name, params, strict_mode=strict_mode)
        return instance
    except (KeyError, NotReadyError) as e:
        if strict_mode:
            raise
        logger.warning(f"⚠️ ASR backend '{name}' no disponible ({e}). Usando StubASR como fallback.")
        return resolve("asr", "stub", params)


def resolve_textref(name: str, params: Optional[Dict[str, Any]] = None, *, strict_mode: bool = False) -> Any:
    """Resuelve proveedor TextRef con auto-fallback opcional."""
    from ipa_core.errors import NotReadyError
    
    try:
        instance = resolve("textref", name, params, strict_mode=strict_mode)
        return instance
    except (KeyError, NotReadyError) as e:
        if strict_mode:
            raise
        logger.warning(f"⚠️ TextRef '{name}' no disponible ({e}). Usando GraphemeTextRef como fallback.")
        return resolve("textref", "grapheme", params)


def resolve_comparator(name: str, params: Optional[Dict[str, Any]] = None, *, strict_mode: bool = False) -> Any:
    return resolve("comparator", name, params, strict_mode=strict_mode)


def resolve_preprocessor(name: str, params: Optional[Dict[str, Any]] = None, *, strict_mode: bool = False) -> Any:
    return resolve("preprocessor", name, params, strict_mode=strict_mode)


def resolve_tts(name: str, params: Optional[Dict[str, Any]] = None, *, strict_mode: bool = False) -> Any:
    return resolve("tts", name, params, strict_mode=strict_mode)


def resolve_llm(name: str, params: Optional[Dict[str, Any]] = None, *, strict_mode: bool = False) -> Any:
    return resolve("llm", name, params, strict_mode=strict_mode)


def validate_plugin(category: str, plugin_cls: type) -> tuple[bool, list[str]]:
    """Valida que una clase cumpla con el protocolo de su categoría.

    Retorna (es_valido, lista_de_errores).
    """
    if category not in _REGISTRY:
        raise ValueError(f"Categoría de plugin inválida: {category}")

    from ipa_core.ports.asr import ASRBackend
    from ipa_core.ports.textref import TextRefProvider
    from ipa_core.ports.compare import Comparator
    from ipa_core.ports.preprocess import Preprocessor
    from ipa_core.ports.tts import TTSProvider
    from ipa_core.ports.llm import LLMAdapter

    protocols = {
        "asr": ASRBackend,
        "textref": TextRefProvider,
        "comparator": Comparator,
        "preprocessor": Preprocessor,
        "tts": TTSProvider,
        "llm": LLMAdapter,
    }

    protocol = protocols[category]
    errors = []

    # Verificación manual de métodos requeridos para mayor claridad en el error
    required_methods = [m for m in dir(protocol) if not m.startswith("_")]

    for method in required_methods:
        if not hasattr(plugin_cls, method):
            errors.append(f"Falta el método requerido: '{method}'")
        elif not callable(getattr(plugin_cls, method)):
            errors.append(f"El atributo '{method}' debe ser un método ejecutable")

    return len(errors) == 0, errors
