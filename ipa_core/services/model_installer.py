"""Servicio de instalación automática de modelos.

Este módulo proporciona funcionalidades para detectar, descargar e instalar
modelos necesarios para PronunciaPA. Diseñado para funcionar desde cualquier
interfaz: CLI, API REST (Desktop/Android), o programáticamente.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ModelCategory(str, Enum):
    """Categorías de modelos disponibles."""
    ASR = "asr"
    TEXTREF = "textref"
    LLM = "llm"
    TTS = "tts"


class ModelStatus(str, Enum):
    """Estado de instalación de un modelo."""
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ERROR = "error"
    OUTDATED = "outdated"


@dataclass
class ModelInfo:
    """Información sobre un modelo."""
    id: str
    name: str
    category: ModelCategory
    description: str
    size_mb: int
    download_url: Optional[str] = None
    pip_package: Optional[str] = None
    binary_name: Optional[str] = None
    install_command: Optional[str] = None
    status: ModelStatus = ModelStatus.NOT_INSTALLED
    progress: float = 0.0
    error: Optional[str] = None
    is_required: bool = False
    is_recommended: bool = False
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "size_mb": self.size_mb,
            "status": self.status.value,
            "progress": self.progress,
            "error": self.error,
            "is_required": self.is_required,
            "is_recommended": self.is_recommended,
        }


# Catálogo de modelos disponibles
MODEL_CATALOG: Dict[str, ModelInfo] = {
    # ============ ASR Models (IPA Output) ============
    "allosaurus": ModelInfo(
        id="allosaurus",
        name="Allosaurus",
        category=ModelCategory.ASR,
        description="ASR universal que produce IPA directamente. Fácil de usar, multilingüe (200+ idiomas). CPU ok.",
        size_mb=500,
        pip_package="allosaurus",
        is_required=True,
        is_recommended=True,
    ),
    "wav2vec2-ipa": ModelInfo(
        id="wav2vec2-ipa",
        name="Wav2Vec2 Large IPA",
        category=ModelCategory.ASR,
        description="ASR de alta precisión con salida IPA universal. Mejor para análisis fonético detallado.",
        size_mb=1200,
        pip_package="transformers",
        download_url="https://huggingface.co/facebook/wav2vec2-lv60-espresso-ipa",
        dependencies=["torch", "transformers"],
        is_recommended=True,
    ),
    "xlsr-ipa": ModelInfo(
        id="xlsr-ipa",
        name="XLS-R 300M IPA (Multilingüe)",
        category=ModelCategory.ASR,
        description="Modelo multilingüe (128 idiomas) con salida IPA. Excelente balance precisión/velocidad.",
        size_mb=1200,
        pip_package="transformers",
        download_url="https://huggingface.co/facebook/wav2vec2-xls-r-300m-phoneme",
        dependencies=["torch", "transformers"],
        is_recommended=True,
    ),
    # ============ ASR Models (Text Output - Not recommended) ============
    "wav2vec2-xlsr": ModelInfo(
        id="wav2vec2-xlsr",
        name="Wav2Vec2 XLSR-53 (Texto)",
        category=ModelCategory.ASR,
        description="⚠️ Produce TEXTO, no IPA. Solo para transcripción de palabras, NO para análisis fonético.",
        size_mb=1200,
        pip_package="transformers",
        dependencies=["torch"],
        is_recommended=False,
    ),
    "whisper": ModelInfo(
        id="whisper",
        name="OpenAI Whisper (Texto)",
        category=ModelCategory.ASR,
        description="⚠️ Produce TEXTO, no IPA. Excelente para transcripción, pero pierde información fonética.",
        size_mb=1500,
        pip_package="openai-whisper",
        is_recommended=False,
    ),
    "vosk": ModelInfo(
        id="vosk",
        name="Vosk (Texto, Ligero)",
        category=ModelCategory.ASR,
        description="⚠️ Produce TEXTO, no IPA. Muy rápido y ligero, ideal para dispositivos limitados.",
        size_mb=50,
        pip_package="vosk",
        is_recommended=False,
    ),
    # ============ ASR Dependencies ============
    "torch": ModelInfo(
        id="torch",
        name="PyTorch",
        category=ModelCategory.ASR,
        description="Framework de deep learning requerido por Wav2Vec2, XLS-R y otros modelos neurales.",
        size_mb=800,
        pip_package="torch",
        is_recommended=False,
    ),
    "transformers": ModelInfo(
        id="transformers",
        name="HuggingFace Transformers",
        category=ModelCategory.ASR,
        description="Librería para cargar modelos de HuggingFace (Wav2Vec2, XLS-R, etc).",
        size_mb=50,
        pip_package="transformers",
        dependencies=["torch"],
        is_recommended=False,
    ),
    
    # TextRef Models
    "espeak": ModelInfo(
        id="espeak",
        name="eSpeak-NG",
        category=ModelCategory.TEXTREF,
        description="Conversor texto→IPA basado en reglas. Multilingüe y preciso.",
        size_mb=15,
        binary_name="espeak-ng",
        install_command="winget install eSpeak-NG.eSpeak-NG" if sys.platform == "win32" else "apt install espeak-ng",
        is_required=True,
        is_recommended=True,
    ),
    "epitran": ModelInfo(
        id="epitran",
        name="Epitran",
        category=ModelCategory.TEXTREF,
        description="G2P lingüístico avanzado con reglas fonológicas. Mejor calidad que eSpeak.",
        size_mb=50,
        pip_package="epitran",
        is_recommended=True,
        dependencies=["espeak"],  # Epitran usa eSpeak internamente para algunos idiomas
    ),
    
    # LLM Models
    "ollama": ModelInfo(
        id="ollama",
        name="Ollama Runtime",
        category=ModelCategory.LLM,
        description="Runtime para ejecutar LLMs locales. Requiere descargar modelos adicionales.",
        size_mb=100,
        binary_name="ollama",
        download_url="https://ollama.com/download",
        is_recommended=True,
    ),
    "tinyllama": ModelInfo(
        id="tinyllama",
        name="TinyLlama (vía Ollama)",
        category=ModelCategory.LLM,
        description="LLM compacto (~400MB) para generar feedback. Requiere Ollama.",
        size_mb=400,
        install_command="ollama pull tinyllama",
        dependencies=["ollama"],
        is_recommended=True,
    ),
    "phi3": ModelInfo(
        id="phi3",
        name="Phi-3 Mini (vía Ollama)",
        category=ModelCategory.LLM,
        description="LLM de Microsoft, mejor calidad que TinyLlama (~2GB). Requiere Ollama.",
        size_mb=2000,
        install_command="ollama pull phi3:mini",
        dependencies=["ollama"],
    ),
    "aiohttp": ModelInfo(
        id="aiohttp",
        name="aiohttp (Python)",
        category=ModelCategory.LLM,
        description="Librería HTTP async requerida para conectar con Ollama.",
        size_mb=1,
        pip_package="aiohttp",
        is_required=True,
    ),
    
    # TTS Models
    "piper": ModelInfo(
        id="piper",
        name="Piper TTS",
        category=ModelCategory.TTS,
        description="TTS neural local. Voces naturales sin conexión.",
        size_mb=30,
        download_url="https://github.com/rhasspy/piper/releases",
        binary_name="piper",
    ),
    "piper-es": ModelInfo(
        id="piper-es",
        name="Piper Voice (Español)",
        category=ModelCategory.TTS,
        description="Voz española para Piper TTS.",
        size_mb=60,
        download_url="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/low/es_ES-davefx-low.onnx",
        dependencies=["piper"],
    ),
    "piper-en": ModelInfo(
        id="piper-en",
        name="Piper Voice (English)",
        category=ModelCategory.TTS,
        description="Voz inglesa para Piper TTS.",
        size_mb=60,
        download_url="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        dependencies=["piper"],
    ),
}


class ModelInstaller:
    """Instalador de modelos con soporte para progreso y callbacks."""
    
    def __init__(
        self,
        models_dir: Optional[Path] = None,
        on_progress: Optional[Callable[[str, float, str], None]] = None,
    ):
        """
        Args:
            models_dir: Directorio donde guardar modelos descargados.
            on_progress: Callback (model_id, progress 0-100, message).
        """
        self._models_dir = models_dir or Path.home() / ".pronunciapa" / "models"
        self._models_dir.mkdir(parents=True, exist_ok=True)
        self._on_progress = on_progress
        self._installing: Dict[str, asyncio.Task] = {}
        
    def _report_progress(self, model_id: str, progress: float, message: str) -> None:
        """Reportar progreso de instalación."""
        if self._on_progress:
            self._on_progress(model_id, progress, message)
        logger.info(f"[{model_id}] {progress:.0f}% - {message}")
    
    async def check_status(self, model_id: str) -> ModelInfo:
        """Verificar estado de instalación de un modelo."""
        if model_id not in MODEL_CATALOG:
            raise ValueError(f"Modelo desconocido: {model_id}")
        
        model = MODEL_CATALOG[model_id]
        model = ModelInfo(**{**model.__dict__})  # Copia
        
        # Verificar según el tipo
        if model.pip_package:
            model.status = await self._check_pip_package(model.pip_package)
        elif model.binary_name:
            model.status = await self._check_binary(model.binary_name)
        elif model.id in ("tinyllama", "phi3"):
            model.status = await self._check_ollama_model(model.id)
        elif model.id in ("wav2vec2-ipa", "xlsr-ipa"):
            # Modelos HuggingFace - verificar si transformers está instalado Y el modelo fue usado
            model.status = await self._check_huggingface_model(model.id)
        elif model.download_url and not model.pip_package and not model.binary_name:
            # Modelo descargable
            model_path = self._models_dir / model.id
            if model_path.exists():
                model.status = ModelStatus.INSTALLED
        
        return model
    
    async def _check_pip_package(self, package: str) -> ModelStatus:
        """Verificar si un paquete pip está instalado."""
        try:
            # Primero intentar con pkg_resources (más confiable)
            import pkg_resources
            try:
                pkg_resources.get_distribution(package)
                return ModelStatus.INSTALLED
            except pkg_resources.DistributionNotFound:
                pass
            
            # Fallback: intentar importar
            import_name = package.replace("-", "_")
            result = await asyncio.create_subprocess_exec(
                sys.executable, "-c", f"import {import_name}",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await result.wait()
            return ModelStatus.INSTALLED if result.returncode == 0 else ModelStatus.NOT_INSTALLED
        except Exception as e:
            logger.debug(f"Error checking {package}: {e}")
            return ModelStatus.NOT_INSTALLED
    
    async def _check_binary(self, binary: str) -> ModelStatus:
        """Verificar si un binario está disponible."""
        # Buscar en PATH
        if shutil.which(binary):
            return ModelStatus.INSTALLED
        
        # Buscar en ubicaciones conocidas (Windows)
        if sys.platform == "win32":
            binary_paths = {
                "espeak-ng": [
                    Path(r"C:\Program Files\eSpeak NG\espeak-ng.exe"),
                    Path(r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe"),
                ],
                "piper": [
                    Path(r"C:\Program Files\Piper\piper.exe"),
                    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Piper" / "piper.exe",
                ],
                "ollama": [
                    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                    Path(r"C:\Program Files\Ollama\ollama.exe"),
                ],
            }
            
            for paths in binary_paths.get(binary, []):
                if paths.exists():
                    return ModelStatus.INSTALLED
        
        return ModelStatus.NOT_INSTALLED
    
    async def _check_huggingface_model(self, model_id: str) -> ModelStatus:
        """Verificar si un modelo HuggingFace está disponible."""
        # Primero verificar que transformers esté instalado
        transformers_status = await self._check_pip_package("transformers")
        if transformers_status != ModelStatus.INSTALLED:
            return ModelStatus.NOT_INSTALLED
        
        # Los modelos HF se consideran "instalados" si transformers está disponible
        # porque se descargan automáticamente al primer uso
        # Para verificación más estricta, revisar el cache de HF
        try:
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            if not cache_dir.exists():
                # Transformers instalado pero modelo no usado aún
                return ModelStatus.INSTALLED
            
            # Buscar el modelo en el cache
            model_map = {
                "wav2vec2-ipa": "wav2vec2-lv60-espresso-ipa",
                "xlsr-ipa": "wav2vec2-xls-r-300m-phoneme",
            }
            model_name = model_map.get(model_id, "")
            
            # Si el modelo está en cache, definitivamente está instalado
            for cached in cache_dir.glob(f"*{model_name}*"):
                if cached.is_dir():
                    return ModelStatus.INSTALLED
            
            # Si no está en cache pero transformers sí, está "listo" para descargar
            return ModelStatus.INSTALLED
        except Exception as e:
            logger.debug(f"Error checking HF model {model_id}: {e}")
            # Si transformers está instalado, considerar como disponible
            return ModelStatus.INSTALLED
    
    async def _check_ollama_model(self, model_name: str) -> ModelStatus:
        """Verificar si un modelo está disponible en Ollama."""
        try:
            ollama_bin = shutil.which("ollama")
            if not ollama_bin:
                # En Windows, buscar en ubicaciones conocidas
                if sys.platform == "win32":
                    possible_paths = [
                        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                        Path(r"C:\Program Files\Ollama\ollama.exe"),
                    ]
                    for p in possible_paths:
                        if p.exists():
                            ollama_bin = str(p)
                            break
                
                if not ollama_bin:
                    return ModelStatus.NOT_INSTALLED
            
            result = await asyncio.create_subprocess_exec(
                ollama_bin, "list",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await result.communicate()
            output = stdout.decode()
            
            # Buscar el modelo en la lista (buscar nombre exacto o con versión)
            search_names = [model_name, f"{model_name}:latest"]
            if model_name == "phi3":
                search_names.append("phi3:mini")
            
            for name in search_names:
                if name in output.lower():
                    return ModelStatus.INSTALLED
            return ModelStatus.NOT_INSTALLED
        except Exception as e:
            logger.debug(f"Error checking Ollama model {model_name}: {e}")
            return ModelStatus.NOT_INSTALLED
    
    async def get_all_status(self) -> List[ModelInfo]:
        """Obtener estado de todos los modelos."""
        tasks = [self.check_status(model_id) for model_id in MODEL_CATALOG]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        models = []
        for model_id, result in zip(MODEL_CATALOG.keys(), results):
            if isinstance(result, Exception):
                model = ModelInfo(**{**MODEL_CATALOG[model_id].__dict__})
                model.status = ModelStatus.ERROR
                model.error = str(result)
                models.append(model)
            else:
                models.append(result)
        
        return models
    
    async def install(self, model_id: str) -> ModelInfo:
        """Instalar un modelo."""
        if model_id not in MODEL_CATALOG:
            raise ValueError(f"Modelo desconocido: {model_id}")
        
        model = MODEL_CATALOG[model_id]
        
        # Verificar si ya está instalado
        status = await self.check_status(model_id)
        if status.status == ModelStatus.INSTALLED:
            self._report_progress(model_id, 100, "Ya está instalado")
            return status
        
        # Verificar dependencias primero
        for dep_id in model.dependencies:
            dep_status = await self.check_status(dep_id)
            if dep_status.status != ModelStatus.INSTALLED:
                self._report_progress(model_id, 0, f"Instalando dependencia: {dep_id}")
                await self.install(dep_id)
        
        self._report_progress(model_id, 10, "Iniciando instalación...")
        
        try:
            # Modelos HuggingFace - solo necesitan transformers instalado
            if model_id in ("wav2vec2-ipa", "xlsr-ipa"):
                # Verificar que transformers esté instalado
                tf_status = await self.check_status("transformers")
                if tf_status.status != ModelStatus.INSTALLED:
                    await self.install("transformers")
                self._report_progress(model_id, 100, "Disponible (se descargará al primer uso)")
                model.status = ModelStatus.INSTALLED
                
            elif model.pip_package:
                await self._install_pip_package(model)
            elif model.install_command:
                await self._run_install_command(model)
            elif model.binary_name and model.download_url:
                await self._download_binary(model)
            elif model.download_url:
                await self._download_model(model)
            else:
                raise ValueError(f"No se sabe cómo instalar: {model_id}")
            
            self._report_progress(model_id, 100, "Instalación completada")
            model.status = ModelStatus.INSTALLED
            
        except Exception as e:
            model.status = ModelStatus.ERROR
            model.error = str(e)
            self._report_progress(model_id, 0, f"Error: {e}")
            raise
        
        return await self.check_status(model_id)
    
    async def _install_pip_package(self, model: ModelInfo) -> None:
        """Instalar paquete pip."""
        if not model.pip_package:
            raise ValueError(f"Model {model.id} has no pip_package defined")
        
        self._report_progress(model.id, 30, f"Instalando {model.pip_package}...")
        
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", model.pip_package, "-q",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"pip install failed: {stderr.decode()}")
        
        self._report_progress(model.id, 90, "Verificando instalación...")
    
    async def _run_install_command(self, model: ModelInfo) -> None:
        """Ejecutar comando de instalación."""
        if not model.install_command:
            raise ValueError(f"Model {model.id} has no install_command defined")
        
        self._report_progress(model.id, 30, f"Ejecutando: {model.install_command}")
        
        # Dividir comando
        parts = model.install_command.split()
        
        process = await asyncio.create_subprocess_exec(
            *parts,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            # Algunos comandos fallan pero funcionan (ej: winget)
            logger.warning(f"Command returned {process.returncode}: {stderr.decode()}")
    
    async def _download_model(self, model: ModelInfo) -> None:
        """Descargar modelo desde URL."""
        if not model.download_url:
            raise ValueError(f"Model {model.id} has no download_url defined")
        
        try:
            import aiohttp
        except ImportError:
            # Fallback a urllib
            await self._download_urllib(model)
            return
        
        self._report_progress(model.id, 20, f"Descargando desde {model.download_url}...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(model.download_url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Download failed: HTTP {response.status}")
                
                total = int(response.headers.get("content-length", 0))
                downloaded = 0
                
                # Determinar nombre de archivo
                url_path = urlparse(model.download_url).path
                filename = Path(str(url_path)).name
                output_path = self._models_dir / model.id / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            progress = 20 + (downloaded / total) * 70
                            self._report_progress(model.id, progress, f"Descargando... {downloaded // 1024 // 1024}MB")
    
    async def _download_urllib(self, model: ModelInfo) -> None:
        """Descargar usando urllib (fallback)."""
        if not model.download_url:
            raise ValueError(f"Model {model.id} has no download_url defined")
        
        import urllib.request
        
        self._report_progress(model.id, 20, "Descargando...")
        
        url_path = urlparse(model.download_url).path
        filename = Path(str(url_path)).name
        output_path = self._models_dir / model.id / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        def download():
            if model.download_url:  # Type guard for mypy
                urllib.request.urlretrieve(model.download_url, str(output_path))
        
        await asyncio.get_event_loop().run_in_executor(None, download)
    
    async def _download_binary(self, model: ModelInfo) -> None:
        """Instrucciones para descargar binario."""
        # Para binarios, damos instrucciones ya que requieren instalación manual
        raise RuntimeError(
            f"El binario '{model.binary_name}' debe instalarse manualmente.\n"
            f"Descarga desde: {model.download_url}\n"
            f"O ejecuta: {model.install_command or 'ver documentación'}"
        )
    
    async def install_recommended(self) -> List[ModelInfo]:
        """Instalar todos los modelos recomendados."""
        results = []
        for model_id, model in MODEL_CATALOG.items():
            if model.is_recommended:
                try:
                    result = await self.install(model_id)
                    results.append(result)
                except Exception as e:
                    model_copy = ModelInfo(**{**model.__dict__})
                    model_copy.status = ModelStatus.ERROR
                    model_copy.error = str(e)
                    results.append(model_copy)
        return results
    
    async def install_required(self) -> List[ModelInfo]:
        """Instalar solo modelos requeridos."""
        results = []
        for model_id, model in MODEL_CATALOG.items():
            if model.is_required:
                status = await self.check_status(model_id)
                if status.status != ModelStatus.INSTALLED:
                    try:
                        result = await self.install(model_id)
                        results.append(result)
                    except Exception as e:
                        model_copy = ModelInfo(**{**model.__dict__})
                        model_copy.status = ModelStatus.ERROR
                        model_copy.error = str(e)
                        results.append(model_copy)
        return results


# Singleton para acceso global
_installer: Optional[ModelInstaller] = None


def get_installer() -> ModelInstaller:
    """Obtener instancia del instalador."""
    global _installer
    if _installer is None:
        _installer = ModelInstaller()
    return _installer


async def quick_setup() -> Dict[str, Any]:
    """Setup rápido: instala lo mínimo necesario.
    
    Returns:
        Dict con estado de cada componente instalado.
    """
    installer = get_installer()
    results = {}
    
    # 1. Verificar e instalar aiohttp (para LLM)
    aiohttp_status = await installer.check_status("aiohttp")
    if aiohttp_status.status != ModelStatus.INSTALLED:
        try:
            await installer.install("aiohttp")
            results["aiohttp"] = "installed"
        except Exception as e:
            results["aiohttp"] = f"error: {e}"
    else:
        results["aiohttp"] = "already_installed"
    
    # 2. Verificar e instalar epitran
    epitran_status = await installer.check_status("epitran")
    if epitran_status.status != ModelStatus.INSTALLED:
        try:
            await installer.install("epitran")
            results["epitran"] = "installed"
        except Exception as e:
            results["epitran"] = f"error: {e}"
    else:
        results["epitran"] = "already_installed"
    
    # 3. Verificar eSpeak
    espeak_status = await installer.check_status("espeak")
    results["espeak"] = espeak_status.status.value
    
    # 4. Verificar Allosaurus
    allosaurus_status = await installer.check_status("allosaurus")
    results["allosaurus"] = allosaurus_status.status.value
    
    # 5. Verificar Ollama
    ollama_status = await installer.check_status("ollama")
    results["ollama"] = ollama_status.status.value
    
    return results
