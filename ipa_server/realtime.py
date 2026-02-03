"""WebSocket router para procesamiento de audio en tiempo real.

Módulo aislado que implementa el endpoint /ws/practice para recibir
audio en streaming, procesar con VAD, y retornar transcripción IPA.

Uso:
    from ipa_server.realtime import realtime_router
    app.include_router(realtime_router)
"""
from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ipa_core.audio.stream import AudioBuffer, AudioSegment, StreamConfig, StreamState
from ipa_core.config import loader
from ipa_core.kernel.core import create_kernel, Kernel
from ipa_core.plugins import registry
from ipa_core.services.transcription import TranscriptionService

logger = logging.getLogger(__name__)

realtime_router = APIRouter(prefix="/ws", tags=["realtime"])


# ============================================================================
# Modelos de mensajes WebSocket
# ============================================================================

class WSMessage(BaseModel):
    """Mensaje base WebSocket."""
    type: str
    data: Optional[Dict[str, Any]] = None


class WSConfig(BaseModel):
    """Configuración inicial de sesión."""
    lang: str = "es"
    reference_text: Optional[str] = None
    mode: str = "objective"
    evaluation_level: str = "phonemic"


class WSStateUpdate(BaseModel):
    """Actualización de estado para el cliente."""
    type: str = "state"
    is_speaking: bool
    volume_level: float
    buffer_duration_ms: int
    status: str


class WSTranscriptionResult(BaseModel):
    """Resultado de transcripción."""
    type: str = "transcription"
    ipa: str
    tokens: list[str]
    duration_ms: int


class WSComparisonResult(BaseModel):
    """Resultado de comparación (si hay texto de referencia)."""
    type: str = "comparison"
    score: float
    user_ipa: str
    ref_ipa: str
    alignment: list
    duration_ms: int


class WSError(BaseModel):
    """Mensaje de error."""
    type: str = "error"
    message: str
    code: str = "unknown"


# ============================================================================
# Conexión WebSocket con estado
# ============================================================================

class RealtimeSession:
    """Sesión de práctica en tiempo real.
    
    Mantiene el estado de una conexión WebSocket individual,
    incluyendo el buffer de audio y la configuración.
    """
    
    def __init__(
        self,
        websocket: WebSocket,
        config: WSConfig,
    ) -> None:
        self.websocket = websocket
        self.ws_config = config
        self.kernel: Optional[Kernel] = None
        self.is_active = True
        
        # Cargar configuración de realtime desde YAML
        cfg = loader.load_config()
        realtime_cfg = getattr(cfg, "realtime", None)
        
        stream_config = StreamConfig(
            silence_timeout_ms=getattr(realtime_cfg, "silence_timeout_ms", 1000) if realtime_cfg else 1000,
            energy_threshold=0.01,
            frame_ms=30,
            max_buffer_seconds=30,
        )
        
        # Crear buffer con callbacks
        self.buffer = AudioBuffer(
            on_segment_ready=self._on_segment_ready,
            on_state_change=self._on_state_change,
            config=stream_config,
        )
    
    async def setup(self) -> None:
        """Inicializar kernel y servicios."""
        try:
            cfg = loader.load_config()
            self.kernel = create_kernel(cfg)
            await self.kernel.setup()
            logger.info(f"Sesión realtime iniciada: lang={self.ws_config.lang}")
        except Exception as e:
            logger.error(f"Error inicializando sesión realtime: {e}")
            raise
    
    async def teardown(self) -> None:
        """Limpiar recursos."""
        self.is_active = False
        self.buffer.reset()
        if self.kernel:
            await self.kernel.teardown()
    
    async def _on_state_change(self, state: StreamState) -> None:
        """Callback cuando cambia el estado del buffer."""
        if not self.is_active:
            return
        
        try:
            msg = WSStateUpdate(
                is_speaking=state.is_speaking,
                volume_level=state.volume_level,
                buffer_duration_ms=state.buffer_duration_ms,
                status=state.status,
            )
            await self.websocket.send_json(msg.model_dump())
        except Exception as e:
            logger.warning(f"Error enviando estado: {e}")
    
    async def _on_segment_ready(self, segment: AudioSegment) -> None:
        """Callback cuando un segmento está listo para procesar."""
        if not self.is_active or not self.kernel:
            return
        
        try:
            # Transcribir audio
            service = TranscriptionService(
                preprocessor=self.kernel.pre,
                asr=self.kernel.asr,
                textref=self.kernel.textref,
                default_lang=self.ws_config.lang,
            )
            
            result = await service.transcribe_file(
                str(segment.audio_path),
                lang=self.ws_config.lang,
            )
            
            # Si hay texto de referencia, comparar
            if self.ws_config.reference_text:
                await self._send_comparison(
                    user_ipa=result.ipa,
                    duration_ms=segment.duration_ms,
                )
            else:
                # Solo transcripción
                msg = WSTranscriptionResult(
                    ipa=result.ipa,
                    tokens=result.tokens,
                    duration_ms=segment.duration_ms,
                )
                await self.websocket.send_json(msg.model_dump())
            
        except Exception as e:
            logger.error(f"Error procesando segmento: {e}")
            await self._send_error(str(e), "processing_error")
        finally:
            # Limpiar archivo temporal
            try:
                segment.audio_path.unlink(missing_ok=True)
            except Exception:
                pass
    
    async def _send_comparison(self, user_ipa: str, duration_ms: int) -> None:
        """Enviar resultado de comparación."""
        if not self.kernel:
            return
        
        try:
            # Obtener IPA de referencia
            ref_result = await self.kernel.textref.to_ipa(
                self.ws_config.reference_text or "",
                lang=self.ws_config.lang,
            )
            ref_ipa = " ".join(ref_result.get("tokens", []))
            
            # Comparar usando el comparador directamente
            comp_result = await self.kernel.comp.compare(
                ref=ref_ipa.split(),
                hyp=user_ipa.split(),
            )
            
            msg = WSComparisonResult(
                score=1.0 - comp_result.get("per", 0.0),
                user_ipa=user_ipa,
                ref_ipa=ref_ipa,
                alignment=comp_result.get("alignment", []),
                duration_ms=duration_ms,
            )
            await self.websocket.send_json(msg.model_dump())
            
        except Exception as e:
            logger.error(f"Error en comparación: {e}")
            # Enviar solo transcripción como fallback
            msg = WSTranscriptionResult(
                ipa=user_ipa,
                tokens=user_ipa.split(),
                duration_ms=duration_ms,
            )
            await self.websocket.send_json(msg.model_dump())
    
    async def _send_error(self, message: str, code: str = "unknown") -> None:
        """Enviar mensaje de error."""
        try:
            msg = WSError(message=message, code=code)
            await self.websocket.send_json(msg.model_dump())
        except Exception:
            pass
    
    async def handle_audio(self, audio_data: bytes) -> None:
        """Procesar chunk de audio recibido."""
        if not self.is_active:
            return
        await self.buffer.add_chunk(audio_data)
    
    async def handle_message(self, message: dict) -> None:
        """Procesar mensaje de control."""
        msg_type = message.get("type", "")
        
        if msg_type == "config":
            # Actualizar configuración
            data = message.get("data", {})
            if "lang" in data:
                self.ws_config.lang = data["lang"]
            if "reference_text" in data:
                self.ws_config.reference_text = data["reference_text"]
            if "mode" in data:
                self.ws_config.mode = data["mode"]
            logger.info(f"Config actualizada: {self.ws_config}")
        
        elif msg_type == "flush":
            # Forzar procesamiento del buffer actual
            await self.buffer.flush()
        
        elif msg_type == "reset":
            # Limpiar buffer sin procesar
            self.buffer.reset()
            await self._on_state_change(self.buffer.state)
        
        elif msg_type == "ping":
            await self.websocket.send_json({"type": "pong"})


# ============================================================================
# Endpoint WebSocket
# ============================================================================

@realtime_router.websocket("/practice")
async def websocket_practice(websocket: WebSocket) -> None:
    """WebSocket endpoint para práctica en tiempo real.
    
    Protocolo:
    1. Cliente conecta y envía mensaje JSON de configuración
    2. Cliente envía audio en chunks binarios (PCM 16-bit 16kHz mono)
    3. Servidor envía actualizaciones de estado JSON (volumen, speaking)
    4. Cuando se detecta pausa de 1s, servidor procesa y envía resultado
    5. Cliente puede enviar mensajes de control (flush, reset, config)
    
    Mensajes del servidor:
    - {"type": "state", "is_speaking": bool, "volume_level": float, ...}
    - {"type": "transcription", "ipa": str, "tokens": [...], ...}
    - {"type": "comparison", "score": float, "user_ipa": str, ...}
    - {"type": "error", "message": str, "code": str}
    
    Mensajes del cliente:
    - {"type": "config", "data": {"lang": "es", "reference_text": "..."}}
    - {"type": "flush"} - Forzar procesamiento inmediato
    - {"type": "reset"} - Limpiar buffer
    - {"type": "ping"} - Keepalive
    """
    await websocket.accept()
    logger.info("WebSocket conectado")
    
    # Configuración inicial por defecto
    config = WSConfig()
    session = RealtimeSession(websocket, config)
    
    try:
        await session.setup()
        
        # Enviar estado inicial
        await websocket.send_json({
            "type": "ready",
            "message": "Sesión iniciada",
            "config": config.model_dump(),
        })
        
        while True:
            # Recibir mensaje (puede ser texto JSON o bytes de audio)
            message = await websocket.receive()
            
            if "text" in message:
                # Mensaje de control JSON
                try:
                    data = json.loads(message["text"])
                    await session.handle_message(data)
                except json.JSONDecodeError:
                    await session._send_error("JSON inválido", "invalid_json")
            
            elif "bytes" in message:
                # Chunk de audio binario
                await session.handle_audio(message["bytes"])
    
    except WebSocketDisconnect:
        logger.info("WebSocket desconectado")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        try:
            await session._send_error(str(e), "internal_error")
        except Exception:
            pass
    finally:
        await session.teardown()


# ============================================================================
# Endpoint REST para verificar estado de realtime
# ============================================================================

@realtime_router.get("/status")
async def realtime_status() -> dict:
    """Verificar si el endpoint realtime está disponible."""
    return {
        "available": True,
        "endpoint": "/ws/practice",
        "protocol": "WebSocket",
        "audio_format": {
            "type": "PCM",
            "sample_rate": 16000,
            "channels": 1,
            "sample_width": 16,
        },
    }


__all__ = ["realtime_router", "RealtimeSession", "WSConfig"]
