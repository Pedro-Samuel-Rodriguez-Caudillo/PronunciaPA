"""Modo interactivo del CLI de PronunciaPA.

Este módulo implementa la interfaz interactiva de línea de comandos
con visualización en tiempo real, colores y gamificación.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Callable

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich import box

console = Console()


class TranscriptionMode(str, Enum):
    """Modo de transcripción fonético."""
    PHONEMIC = "phonemic"  # /.../ - representación abstracta
    PHONETIC = "phonetic"  # [...] - detalle articulatorio


class FeedbackLevel(str, Enum):
    """Nivel de detalle del feedback LLM."""
    CASUAL = "casual"    # Explicaciones sencillas
    PRECISE = "precise"  # Explicaciones detalladas


@dataclass
class SessionState:
    """Estado de la sesión interactiva."""
    lang: str = "es"
    mode: TranscriptionMode = TranscriptionMode.PHONEMIC
    feedback_level: FeedbackLevel = FeedbackLevel.CASUAL
    reference_text: str = ""
    is_recording: bool = False
    recording_seconds: float = 0.0
    last_result: Optional[dict] = None
    
    # Gamificación
    streak_days: int = 0
    total_practices: int = 0
    session_practices: int = 0
    level: int = 1
    xp: int = 0
    
    # Backend/Config
    backend_name: str = "allosaurus"
    textref_name: str = "epitran"


@dataclass
class GameStats:
    """Estadísticas de gamificación."""
    streak_days: int = 0
    total_practices: int = 0
    avg_score: float = 0.0
    level: int = 1
    xp: int = 0
    xp_to_next_level: int = 100
    
    # Logros desbloqueados
    achievements: list[str] = field(default_factory=list)
    
    def add_practice(self, score: float) -> list[str]:
        """Registra una práctica y devuelve nuevos logros."""
        new_achievements = []
        self._update_avg_score(score)
        self.total_practices += 1
        
        xp_earned = int(score * 100)
        self.xp += xp_earned
        
        new_achievements.extend(self._check_level_up())
        new_achievements.extend(self._check_milestones())
        new_achievements.extend(self._check_score_achievements(score))
            
        return new_achievements

    def _update_avg_score(self, score: float) -> None:
        if self.total_practices == 0:
            self.avg_score = score
        else:
            self.avg_score = (self.avg_score * self.total_practices + score) / (self.total_practices + 1)

    def _check_level_up(self) -> list[str]:
        new_ach = []
        while self.xp >= self.xp_to_next_level:
            self.xp -= self.xp_to_next_level
            self.level += 1
            self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
            new_ach.append(f"🎉 ¡Nivel {self.level} alcanzado!")
        return new_ach

    def _check_milestones(self) -> list[str]:
        milestones = {1: ("first_practice", "🏆 ¡Primera práctica completada!"),
                      10: ("ten_practices", "🏆 ¡10 prácticas! Estás en racha"),
                      100: ("hundred_practices", "🏆 ¡100 prácticas! Eres un experto")}
        
        if self.total_practices in milestones:
            key, msg = milestones[self.total_practices]
            if key not in self.achievements:
                self.achievements.append(key)
                return [msg]
        return []

    def _check_score_achievements(self, score: float) -> list[str]:
        if score >= 0.95 and "perfect_score" not in self.achievements:
            self.achievements.append("perfect_score")
            return ["⭐ ¡Pronunciación perfecta!"]
        if score >= 0.90 and "excellent_score" not in self.achievements:
            self.achievements.append("excellent_score")
            return ["⭐ ¡Excelente pronunciación!"]
        return []


def _get_level_name(level: int) -> str:
    """Devuelve el nombre del nivel."""
    names = {
        1: "Principiante",
        2: "Aprendiz",
        3: "Intermedio",
        4: "Avanzado",
        5: "Experto",
        6: "Maestro",
        7: "Virtuoso",
        8: "Legendario",
    }
    return names.get(level, f"Nivel {level}")


def _format_ipa_mode(mode: TranscriptionMode, text: str) -> str:
    """Formatea texto IPA según el modo."""
    if mode == TranscriptionMode.PHONEMIC:
        return f"/{text}/"
    return f"[{text}]"


def _build_header_panel(state: SessionState, stats: GameStats) -> Panel:
    """Construye el panel de encabezado."""
    header = Table.grid(padding=1)
    header.add_column(justify="left", ratio=1)
    header.add_column(justify="center", ratio=2)
    header.add_column(justify="right", ratio=1)
    
    # Columna izquierda: Idioma y modo
    lang_text = Text()
    lang_text.append("🌍 ", style="bold")
    lang_text.append(state.lang.upper(), style="cyan bold")
    lang_text.append("  ")
    mode_symbol = "/" if state.mode == TranscriptionMode.PHONEMIC else "[]"
    lang_text.append(f"📝 {mode_symbol}", style="yellow")
    
    # Columna central: Título
    title = Text("PronunciaPA", style="bold magenta")
    
    # Columna derecha: Stats
    stats_text = Text()
    stats_text.append(f"Lvl {stats.level} ", style="green bold")
    stats_text.append(f"({_get_level_name(stats.level)})", style="dim")
    stats_text.append(f"  🔥{stats.streak_days}", style="orange1")
    
    header.add_row(lang_text, Align.center(title), stats_text)
    
    return Panel(
        header,
        box=box.DOUBLE,
        border_style="blue",
    )


def _build_recording_panel(state: SessionState) -> Panel:
    """Panel de estado de grabación."""
    if state.is_recording:
        # Animación de ondas
        frames = ["▁", "▃", "▅", "▇", "█", "▇", "▅", "▃"]
        wave_idx = int(time.time() * 4) % len(frames)
        wave = " ".join(frames[(i + wave_idx) % len(frames)] for i in range(8))
        
        content = Text()
        content.append("● REC ", style="red bold blink")
        content.append(f"{state.recording_seconds:.1f}s\n\n", style="white")
        content.append(wave, style="red")
        
        return Panel(
            Align.center(content),
            title="[red bold]🎤 Grabando...[/red bold]",
            border_style="red",
            box=box.HEAVY,
        )
    else:
        content = Text()
        content.append("🎤\n\n", style="purple bold")
        content.append("Presiona ", style="dim")
        content.append("ENTER", style="cyan bold")
        content.append(" para grabar", style="dim")
        
        return Panel(
            Align.center(content),
            title="Micrófono",
            border_style="purple",
        )


def _build_reference_panel(state: SessionState) -> Panel:
    """Panel de texto de referencia."""
    if state.reference_text:
        content = Text(state.reference_text, style="cyan bold")
    else:
        content = Text("(Escribe un texto para practicar)", style="dim italic")
    
    return Panel(
        Align.center(content),
        title="📝 Texto de Referencia",
        border_style="cyan",
    )


def _build_results_panel(state: SessionState) -> Panel:
    """Panel de resultados."""
    if not state.last_result:
        return Panel(Align.center(Text("Aún no hay resultados", style="dim")), title="📊 Resultados", border_style="dim")
    
    res = state.last_result
    score = 1 - res.get("per", 0)
    color, msg = _get_score_display_params(score)
    
    content = Table.grid(padding=1); content.add_column()
    content.add_row(_build_score_bar(score, color))
    content.add_row(Text(msg, style="italic"))
    
    _add_alignment_to_content(content, res.get("alignment", []))
    
    return Panel(content, title="📊 Resultados", border_style=color)

def _get_score_display_params(score: float) -> tuple[str, str]:
    if score >= 0.9: return "green", "¡Excelente! 🎉"
    if score >= 0.7: return "yellow", "¡Buen trabajo! 👍"
    if score >= 0.5: return "orange1", "Sigue practicando 💪"
    return "red", "Necesitas más práctica 📚"

def _build_score_bar(score: float, color: str) -> Text:
    score_pct = int(score * 100)
    filled = int(score * 20)
    txt = Text()
    txt.append(f"Precisión: {score_pct}% ", style=f"{color} bold")
    txt.append("█" * filled, style=color)
    txt.append("░" * (20 - filled), style="dim")
    return txt

def _add_alignment_to_content(content: Table, alignment: list):
    if not alignment: return
    content.add_row(Text(""))
    ref_l, hyp_l = Text("REF: ", style="bold"), Text("TÚ:  ", style="bold")
    
    for r_tok, h_tok in alignment:
        r_s, h_s = r_tok or "-", h_tok or "-"
        w = max(len(r_s), len(h_s))
        style = _get_token_style(r_tok, h_tok)
        ref_l.append(r_s.ljust(w) + " ", style=style)
        hyp_l.append(h_s.ljust(w) + " ", style=style)
    
    content.add_row(ref_l); content.add_row(hyp_l)

def _get_token_style(ref, hyp) -> str:
    if ref == hyp: return "green"
    if ref is None: return "blue"
    if hyp is None: return "red"
    return "yellow"

def _build_feedback_panel(state: SessionState) -> Panel:
    """Panel de feedback LLM."""
    if not state.last_result:
        return Panel(Text(""), title="💡 Consejos", border_style="dim", height=5)
    
    fb = state.last_result.get("feedback")
    if not fb:
        return Panel(Text("Procesa una grabación para obtener consejos", style="dim"), title="💡 Consejos", border_style="dim", height=5)
    
    advice = _extract_advice(fb, state.feedback_level)
    return Panel(Text(advice or "Sin consejos disponibles", style="cyan"), title="💡 Consejos", border_style="cyan")

def _extract_advice(fb: Any, level: FeedbackLevel) -> str:
    data = fb if isinstance(fb, dict) else {}
    advice = data.get("advice_short", data.get("summary", ""))
    if level == FeedbackLevel.PRECISE:
        return data.get("advice_long", advice)
    return advice


def _build_help_bar() -> Text:
    """Barra de ayuda con shortcuts."""
    help_text = Text()
    help_text.append(" [r]", style="cyan bold")
    help_text.append("ecord  ", style="dim")
    help_text.append("[t]", style="cyan bold")
    help_text.append("ext  ", style="dim")
    help_text.append("[m]", style="cyan bold") 
    help_text.append("ode  ", style="dim")
    help_text.append("[l]", style="cyan bold")
    help_text.append("ang  ", style="dim")
    help_text.append("[f]", style="cyan bold")
    help_text.append("eedback-level  ", style="dim")
    help_text.append("[s]", style="cyan bold")
    help_text.append("tats  ", style="dim")
    help_text.append("[q]", style="red bold")
    help_text.append("uit", style="dim")
    return help_text


def _build_main_layout(state: SessionState, stats: GameStats) -> Layout:
    """Construye el layout principal."""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=5),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    
    layout["header"].update(_build_header_panel(state, stats))
    
    layout["main"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=1),
    )
    
    left_layout = Layout()
    left_layout.split_column(
        Layout(_build_reference_panel(state), size=5),
        Layout(_build_recording_panel(state)),
    )
    layout["main"]["left"].update(left_layout)
    
    right_layout = Layout()
    right_layout.split_column(
        Layout(_build_results_panel(state)),
        Layout(_build_feedback_panel(state), size=7),
    )
    layout["main"]["right"].update(right_layout)
    
    layout["footer"].update(Panel(_build_help_bar(), box=box.MINIMAL))
    
    return layout


def _show_stats_popup(stats: GameStats) -> None:
    """Muestra popup de estadísticas."""
    table = Table(title="📊 Tus Estadísticas", box=box.ROUNDED)
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    
    table.add_row("Nivel", f"{stats.level} ({_get_level_name(stats.level)})")
    table.add_row("XP", f"{stats.xp}/{stats.xp_to_next_level}")
    table.add_row("Racha de días", f"🔥 {stats.streak_days}")
    table.add_row("Prácticas totales", str(stats.total_practices))
    table.add_row("Score promedio", f"{stats.avg_score:.1%}")
    table.add_row("Logros", str(len(stats.achievements)))
    
    console.print(table)
    console.print("\nPresiona ENTER para continuar...")
    input()


class SessionManager:
    """Gestiona el bucle principal y comandos de la sesión interactiva."""
    
    def __init__(self, state: SessionState, stats: GameStats, kernel: Optional[Kernel] = None):
        self.state = state
        self.stats = stats
        self.kernel = kernel
        self.running = True

    async def run(self):
        while self.running:
            console.clear()
            console.print(_build_main_layout(self.state, self.stats))
            try:
                cmd = console.input("\n[bold cyan]>[/bold cyan] ").strip().lower()
                await self.handle_command(cmd)
            except (KeyboardInterrupt, EOFError):
                break

    async def handle_command(self, cmd: str):
        handlers = {
            "q": self._cmd_quit, "quit": self._cmd_quit, "exit": self._cmd_quit,
            "r": self._cmd_record, "record": self._cmd_record, "": self._cmd_record,
            "t": self._cmd_text, "text": self._cmd_text,
            "m": self._cmd_mode, "mode": self._cmd_mode,
            "l": self._cmd_lang, "lang": self._cmd_lang,
            "f": self._cmd_feedback, "feedback": self._cmd_feedback,
            "s": self._cmd_stats, "stats": self._cmd_stats,
            "help": self._cmd_help
        }
        if cmd in handlers:
            await handlers[cmd]()

    async def _cmd_quit(self):
        self.running = False

    async def _cmd_record(self):
        if not self.state.reference_text:
            console.print("[yellow]Escribe un texto con 't' primero[/yellow]")
            time.sleep(1.2); return
        
        await self._perform_recording()

    async def _perform_recording(self):
        from ipa_core.audio.microphone import record
        from ipa_core.audio.files import cleanup_temp
        
        console.print("[bold green]🎤 Grabando...[/bold green]")
        self.state.is_recording = True
        try:
            path, meta = record(seconds=3.0)
            self.state.is_recording = False
            self.state.recording_seconds = meta.get("duration", 3.0)
            await self._process_audio(path)
            cleanup_temp(path)
        except Exception as e:
            self.state.is_recording = False
            console.print(f"[red]Error: {e}[/red]"); time.sleep(2)

    async def _process_audio(self, path: str):
        from ipa_core.backends.audio_io import to_audio_input
        console.print("[bold blue]⏳ Procesando...[/bold blue]")
        if self.kernel:
            res = await self.kernel.run(audio=to_audio_input(path), text=self.state.reference_text, lang=self.state.lang)
            self.state.last_result = res
            self.state.session_practices += 1
            for ach in self.stats.add_practice(1 - res.get("per", 0)):
                console.print(f"[bold yellow]{ach}[/bold yellow]"); time.sleep(0.6)
        else:
            self._mock_process()

    def _mock_process(self):
        self.state.last_result = {"per": 0.1, "alignment": [("a", "a")]}
        self.stats.add_practice(0.9)
        self.state.session_practices += 1

    async def _cmd_text(self):
        txt = console.input("[cyan]Texto de referencia:[/cyan] ").strip()
        if txt: self.state.reference_text = txt

    async def _cmd_mode(self):
        self.state.mode = TranscriptionMode.PHONETIC if self.state.mode == TranscriptionMode.PHONEMIC else TranscriptionMode.PHONEMIC
        console.print(f"[yellow]Modo: {self.state.mode}[/yellow]"); time.sleep(0.6)

    async def _cmd_lang(self):
        lang = console.input("[cyan]Idioma:[/cyan] ").strip().lower()
        if lang: self.state.lang = lang

    async def _cmd_feedback(self):
        self.state.feedback_level = FeedbackLevel.PRECISE if self.state.feedback_level == FeedbackLevel.CASUAL else FeedbackLevel.CASUAL
        console.print(f"[yellow]Feedback: {self.state.feedback_level}[/yellow]"); time.sleep(0.6)

    async def _cmd_stats(self):
        _show_stats_popup(self.stats)

    async def _cmd_help(self):
        console.print(Panel("r - Grabar\nt - Texto\nm - Modo\nl - Idioma\nf - Feedback\ns - Stats\nq - Salir", title="Ayuda"))
        input("Presiona ENTER...")


async def run_interactive_session(
    initial_lang: str = "es",
    initial_mode: TranscriptionMode = TranscriptionMode.PHONEMIC,
    feedback_level: FeedbackLevel = FeedbackLevel.CASUAL,
    kernel_factory: Optional[Callable] = None,
) -> None:
    """Ejecuta la sesión interactiva del CLI."""
    state = SessionState(lang=initial_lang, mode=initial_mode, feedback_level=feedback_level)
    stats = GameStats()
    kernel = kernel_factory() if kernel_factory else None
    
    if kernel: await kernel.setup()
    
    _show_welcome()
    mgr = SessionManager(state, stats, kernel)
    await mgr.run()
    
    if kernel: await kernel.teardown()
    console.print(f"\n[bold magenta]¡Hasta pronto! 👋[/bold magenta] ({state.session_practices} prácticas)")

def _show_welcome():
    console.clear()
    console.print(Panel.fit("[bold magenta]¡Bienvenido a PronunciaPA![/bold magenta]\n\nPractica con feedback en tiempo real.\n[dim]Presiona ENTER para comenzar...[/dim]"))
    try: input()
    except (KeyboardInterrupt, EOFError): pass
