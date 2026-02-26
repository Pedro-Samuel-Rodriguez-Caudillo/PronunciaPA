#!/usr/bin/env python
"""CLI para planes de lección y hoja de ruta de PronunciaPA.

Uso:
    # Ver hoja de ruta de un usuario
    python -m ipa_core.cli.lessons roadmap demo --lang es

    # Obtener plan de lección personalizado
    python -m ipa_core.cli.lessons plan demo --lang es

    # Generar lección de vista previa para un sonido (sin historial)
    python -m ipa_core.cli.lessons generate s --lang es
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Optional

# ── Console helpers ─────────────────────────────────────────────────────────


LEVEL_ICONS = {
    "not_started": "○",
    "in_progress": "◑",
    "proficient": "◕",
    "completed": "●",
}

LEVEL_LABELS = {
    "not_started": "Sin iniciar",
    "in_progress": "En proceso",
    "proficient": "Competente",
    "completed": "Completado",
}

LEVEL_COLORS = {
    "not_started": "\033[90m",   # grey
    "in_progress": "\033[33m",   # yellow
    "proficient": "\033[36m",    # cyan
    "completed": "\033[32m",     # green
}
RESET = "\033[0m"


def _colorize(text: str, color: str) -> str:
    """Wrap text in ANSI color if stdout is a TTY."""
    if sys.stdout.isatty():
        return f"{color}{text}{RESET}"
    return text


def _bar(progress: float, width: int = 20) -> str:
    filled = int(progress * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


# ── Sub-commands ─────────────────────────────────────────────────────────────


async def cmd_roadmap(args: argparse.Namespace) -> int:
    """Show roadmap progress for a user."""
    import httpx

    base = args.base_url.rstrip("/")
    url = f"{base}/v1/lessons/roadmap/{args.user_id}/{args.lang}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
    except Exception as exc:
        print(f"Error de conexión: {exc}", file=sys.stderr)
        return 1

    if resp.status_code == 503:
        print(
            "ℹ El servidor no tiene historial configurado (503). "
            "La hoja de ruta no está disponible en este modo.",
            file=sys.stderr,
        )
        return 0

    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        return 1

    data = resp.json()
    topics: list[dict] = sorted(
        data.get("topics", []), key=lambda t: t.get("order", 0)
    )

    print(
        f"\n📊  Hoja de ruta — usuario: {data['user_id']} | idioma: {data['lang'].upper()}\n"
    )
    for t in topics:
        level = t.get("level", "not_started")
        icon = LEVEL_ICONS.get(level, "?")
        label = LEVEL_LABELS.get(level, level)
        color = LEVEL_COLORS.get(level, "")
        progress_val = {
            "not_started": 0.0,
            "in_progress": 0.35,
            "proficient": 0.65,
            "completed": 1.0,
        }.get(level, 0.0)

        bar = _bar(progress_val)
        line = f"  {icon}  {t['name']:<25}  {bar}  {label}"
        print(_colorize(line, color))

    print()
    return 0


async def cmd_plan(args: argparse.Namespace) -> int:
    """Get a personalized lesson plan for a user."""
    import httpx

    base = args.base_url.rstrip("/")
    payload: dict = {"user_id": args.user_id, "lang": args.lang}
    if args.sound_id:
        payload["sound_id"] = args.sound_id

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base}/v1/lessons/plan",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
    except Exception as exc:
        print(f"Error de conexión: {exc}", file=sys.stderr)
        return 1

    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        return 1

    plan = resp.json()
    _print_plan(plan)
    return 0


async def cmd_generate(args: argparse.Namespace) -> int:
    """Generate a preview lesson for a sound (no user history needed)."""
    import httpx

    base = args.base_url.rstrip("/")
    url = f"{base}/v1/lessons/generate/{args.lang}/{args.sound_id}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers={"Content-Type": "application/json"},
            )
    except Exception as exc:
        print(f"Error de conexión: {exc}", file=sys.stderr)
        return 1

    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        return 1

    plan = resp.json()
    _print_plan(plan)
    return 0


def _print_plan(plan: dict) -> None:
    """Pretty-print a lesson plan dict to stdout."""
    sound_id = plan.get("recommended_sound_id", "")
    topic_id = plan.get("topic_id", "")
    intro = plan.get("intro", "")
    tips: list[str] = plan.get("tips", [])
    drills: list[dict] = plan.get("drills", [])

    print()
    if topic_id:
        print(f"🗂  Tema: {topic_id}", end="")
        if sound_id:
            print(f"  |  Sonido recomendado: /{sound_id}/", end="")
        print()
    print()

    if intro:
        print(intro)
        print()

    if tips:
        print("💡 Consejos:")
        for tip in tips:
            print(f"   • {tip}")
        print()

    if drills:
        DRILL_ICONS = {"listen": "🎧", "repeat": "🎙", "write": "✍️"}
        print("🏋 Ejercicios:")
        for d in drills:
            icon = DRILL_ICONS.get(d.get("type", ""), "▸")
            print(f"   {icon} {d.get('text', '')}")
        print()


# ── Entry point ───────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ipa_core.cli.lessons",
        description="Gestión de lecciones y hoja de ruta de PronunciaPA.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="URL base del servidor (defecto: http://127.0.0.1:8000)",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # roadmap
    p_roadmap = sub.add_parser("roadmap", help="Ver hoja de ruta de un usuario")
    p_roadmap.add_argument("user_id", help="Identificador del usuario")
    p_roadmap.add_argument("--lang", default="es", help="Código de idioma (defecto: es)")

    # plan
    p_plan = sub.add_parser("plan", help="Obtener plan de lección personalizado")
    p_plan.add_argument("user_id", help="Identificador del usuario")
    p_plan.add_argument("--lang", default="es")
    p_plan.add_argument("--sound-id", dest="sound_id", default=None,
                        help="Forzar un sonido específico")

    # generate
    p_gen = sub.add_parser("generate", help="Generar lección de vista previa")
    p_gen.add_argument("sound_id", help="ID del sonido (p.ej. s, r, tʃ)")
    p_gen.add_argument("--lang", default="es")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    handlers = {
        "roadmap": cmd_roadmap,
        "plan": cmd_plan,
        "generate": cmd_generate,
    }
    handler = handlers.get(args.cmd)
    if handler is None:
        parser.print_help()
        return 1

    return asyncio.run(handler(args))


if __name__ == "__main__":
    sys.exit(main())
