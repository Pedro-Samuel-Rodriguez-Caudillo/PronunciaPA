"""CLI para interactuar con PronunciaPA."""
from __future__ import annotations

import argparse
import json
from typing import Optional

from ipa_core.audio.files import cleanup_temp
from ipa_core.audio.microphone import record
from ipa_core.services.transcription import TranscriptionService, TranscriptionPayload


def cli_compare(
    audio: str,
    text: str,
    *,
    lang: Optional[str] = None,
    config_path: Optional[str] = None,
    backend_name: Optional[str] = None,
    textref_name: Optional[str] = None,
    comparator_name: Optional[str] = None,
):
    """Placeholder hasta implementar comparación."""
    raise NotImplementedError("CLI compare sigue pendiente. Usa `transcribe`.")


def cli_transcribe(
    audio: Optional[str],
    *,
    lang: Optional[str] = None,
    use_mic: bool = False,
    seconds: float = 3.0,
    textref: Optional[str] = None,
) -> list[str]:
    """Transcribe un archivo WAV/MP3 o captura desde micrófono."""
    if not use_mic and not audio:
        raise ValueError("Debes especificar '--audio' o '--mic'")

    service = TranscriptionService(default_lang=lang or "es", textref_name=textref)
    temp_path = None
    try:
        if use_mic:
            temp_path, _meta = record(seconds, sample_rate=16000)
            payload = service.transcribe_file(temp_path, lang=lang)
        else:
            payload = service.transcribe_file(str(audio), lang=lang)
    finally:
        if temp_path:
            cleanup_temp(temp_path)
    return payload.tokens


def _format_payload(payload: TranscriptionPayload, as_json: bool) -> str:
    if as_json:
        return json.dumps(
            {"ipa": payload.ipa, "tokens": payload.tokens, "lang": payload.lang, "audio": payload.audio},
            ensure_ascii=False,
        )
    return f"IPA ({payload.lang}): {payload.ipa}"


def _run_transcribe(args: argparse.Namespace) -> int:
    service = TranscriptionService(default_lang=args.lang or "es", textref_name=args.textref)
    if args.mic:
        temp_path, _meta = record(args.seconds, sample_rate=16000)
        try:
            payload = service.transcribe_file(temp_path, lang=args.lang)
        finally:
            cleanup_temp(temp_path)
    else:
        payload = service.transcribe_file(args.audio, lang=args.lang)
    print(_format_payload(payload, args.json))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="pronunciapa", description="CLI de transcripción IPA")
    sub = parser.add_subparsers(dest="command", required=True)

    t_parser = sub.add_parser("transcribe", help="Transcribir audio a IPA")
    t_parser.add_argument("--audio", "-a", help="Ruta a WAV/MP3")
    t_parser.add_argument("--lang", "-l", default="es", help="Idioma (por defecto: es)")
    t_parser.add_argument("--mic", action="store_true", help="Capturar audio del micrófono")
    t_parser.add_argument("--seconds", type=float, default=3.0, help="Duración al grabar con --mic (s)")
    t_parser.add_argument("--json", action="store_true", help="Salida JSON")
    t_parser.add_argument(
        "--textref",
        choices=["grapheme", "epitran"],
        help="Conversor texto→IPA (default: grapheme)",
    )

    args = parser.parse_args(argv)
    if args.command == "transcribe":
        if not args.mic and not args.audio:
            parser.error("transcribe requiere --audio o --mic")
        return _run_transcribe(args)

    parser.error("Comando no soportado")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
