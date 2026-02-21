"""Script simple para iniciar el servidor."""
import logging
import os
import uvicorn


def _configure_logging() -> None:
    """Configura logging base. Si PRONUNCIAPA_DEBUG_AUDIO=1 activa DEBUG
    para el pipeline de audio sin inundar la consola con ruido de uvicorn."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt=datefmt)

    if os.environ.get("PRONUNCIAPA_DEBUG_AUDIO") == "1":
        # Solo los loggers del pipeline de audio y ficheros en DEBUG
        for name in (
            "ipa_core.audio.processing_chain",
            "ipa_core.audio.vad",
            "ipa_core.audio.files",
            "ipa_core.preprocessor_basic",
        ):
            logging.getLogger(name).setLevel(logging.DEBUG)
        print("[start_server] 🔊 Audio debug logging ON — mira los mensajes [AudioChain]", flush=True)


if __name__ == "__main__":
    _configure_logging()
    uvicorn.run(
        "ipa_server.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
