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
        self.total_practices += 1
        
        # Actualizar promedio
        if self.avg_score == 0:
            self.avg_score = score
        else:
            self.avg_score = (self.avg_score * (self.total_practices - 1) + score) / self.total_practices
        
        # XP basado en score
        xp_earned = int(score * 100)
        self.xp += xp_earned
        
        # Subir de nivel
        while self.xp >= self.xp_to_next_level:
            self.xp -= self.xp_to_next_level
            self.level += 1
            self.xp_to_next_level = int(self.xp_to_next_level * 1.5)
            new_achievements.append(f"🎉 ¡Nivel {self.level} alcanzado!")
        
        # Logros por cantidad de prácticas
        if self.total_practices == 1 and "first_practice" not in self.achievements:
            self.achievements.append("first_practice")
            new_achievements.append("🏆 ¡Primera práctica completada!")
        elif self.total_practices == 10 and "ten_practices" not in self.achievements:
            self.achievements.append("ten_practices")
            new_achievements.append("🏆 ¡10 prácticas! Estás en racha")
        elif self.total_practices == 100 and "hundred_practices" not in self.achievements:
            self.achievements.append("hundred_practices")
            new_achievements.append("🏆 ¡100 prácticas! Eres un experto")
            
        # Logros por score
        if score >= 0.95 and "perfect_score" not in self.achievements:
            self.achievements.append("perfect_score")
            new_achievements.append("⭐ ¡Pronunciación perfecta!")
        elif score >= 0.90 and "excellent_score" not in self.achievements:
            self.achievements.append("excellent_score")
            new_achievements.append("⭐ ¡Excelente pronunciación!")
            
        return new_achievements


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
        return Panel(
            Align.center(Text("Aún no hay resultados", style="dim")),
            title="📊 Resultados",
            border_style="dim",
        )
    
    res = state.last_result
    per = res.get("per", 0)
    score = 1 - per  # Invertir PER para mostrar como score positivo
    
    content = Table.grid(padding=1)
    content.add_column()
    
    # Barra de score
    score_pct = int(score * 100)
    bar_filled = int(score * 20)
    bar_empty = 20 - bar_filled
    
    if score >= 0.9:
        bar_color = "green"
        message = "¡Excelente! 🎉"
    elif score >= 0.7:
        bar_color = "yellow"
        message = "¡Buen trabajo! 👍"
    elif score >= 0.5:
        bar_color = "orange1"
        message = "Sigue practicando 💪"
    else:
        bar_color = "red"
        message = "Necesitas más práctica 📚"
    
    score_text = Text()
    score_text.append(f"Precisión: {score_pct}% ", style=f"{bar_color} bold")
    score_text.append("█" * bar_filled, style=bar_color)
    score_text.append("░" * bar_empty, style="dim")
    content.add_row(score_text)
    content.add_row(Text(message, style="italic"))
    
    # Alineación IPA
    alignment = res.get("alignment", [])
    if alignment:
        content.add_row(Text(""))
        
        ref_line = Text()
        ref_line.append("REF: ", style="bold")
        
        hyp_line = Text()
        hyp_line.append("TÚ:  ", style="bold")
        
        for ref_tok, hyp_tok in alignment:
            ref_str = ref_tok or "-"
            hyp_str = hyp_tok or "-"
            width = max(len(ref_str), len(hyp_str))
            
            if ref_tok == hyp_tok:
                style = "green"
            elif ref_tok is None:
                style = "blue"  # Inserción
            elif hyp_tok is None:
                style = "red"  # Omisión
            else:
                style = "yellow"  # Sustitución
            
            ref_line.append(ref_str.ljust(width) + " ", style=style)
            hyp_line.append(hyp_str.ljust(width) + " ", style=style)
        
        content.add_row(ref_line)
        content.add_row(hyp_line)
    
    return Panel(
        content,
        title="📊 Resultados",
        border_style=bar_color,
    )


def _build_feedback_panel(state: SessionState) -> Panel:
    """Panel de feedback LLM."""
    if not state.last_result:
        return Panel(
            Text(""),
            title="💡 Consejos",
            border_style="dim",
            height=5,
        )
    
    feedback = state.last_result.get("feedback", {})
    if not feedback:
        return Panel(
            Text("Procesa una grabación para obtener consejos", style="dim"),
            title="💡 Consejos",
            border_style="dim",
            height=5,
        )
    
    fb_data = feedback if isinstance(feedback, dict) else {}
    advice = fb_data.get("advice_short", fb_data.get("summary", ""))
    
    if state.feedback_level == FeedbackLevel.PRECISE:
        advice = fb_data.get("advice_long", advice)
    
    return Panel(
        Text(advice or "Sin consejos disponibles", style="cyan"),
        title="💡 Consejos",
        border_style="cyan",
    )


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


async def run_interactive_session(
    initial_lang: str = "es",
    initial_mode: TranscriptionMode = TranscriptionMode.PHONEMIC,
    feedback_level: FeedbackLevel = FeedbackLevel.CASUAL,
    kernel_factory: Optional[Callable] = None,
) -> None:
    """Ejecuta la sesión interactiva del CLI.
    
    Args:
        initial_lang: Idioma inicial para la transcripción
        initial_mode: Modo de transcripción (fonémico/fonético)
        feedback_level: Nivel de detalle del feedback
        kernel_factory: Factory opcional para crear el kernel
    """
    from ipa_core.audio.microphone import record
    from ipa_core.audio.files import cleanup_temp
    from ipa_core.backends.audio_io import to_audio_input
    
    state = SessionState(
        lang=initial_lang,
        mode=initial_mode,
        feedback_level=feedback_level,
    )
    stats = GameStats()
    
    # Kernel para procesamiento
    kernel = None
    if kernel_factory:
        kernel = kernel_factory()
        await kernel.setup()
    
    console.clear()
    console.print(Panel.fit(
        "[bold magenta]¡Bienvenido a PronunciaPA![/bold magenta]\n\n"
        "Practica tu pronunciación con feedback en tiempo real.\n"
        "Escribe un texto de referencia y graba tu voz.\n\n"
        "[dim]Presiona cualquier tecla para comenzar...[/dim]",
        border_style="magenta",
    ))
    
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        return
    
    running = True
    
    while running:
        console.clear()
        console.print(_build_main_layout(state, stats))
        
        try:
            cmd = console.input("\n[bold cyan]>[/bold cyan] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        
        if cmd in ("q", "quit", "exit"):
            running = False
            
        elif cmd in ("r", "record", ""):
            if not state.reference_text:
                console.print("[yellow]Primero escribe un texto de referencia con 't'[/yellow]")
                time.sleep(1.5)
                continue
                
            # Grabar audio
            console.print("[bold green]🎤 Grabando... (3 segundos)[/bold green]")
            state.is_recording = True
            
            try:
                wav_path, meta = record(seconds=3.0)
                state.is_recording = False
                state.recording_seconds = meta.get("duration", 3.0)
                
                console.print("[bold blue]⏳ Procesando...[/bold blue]")
                
                if kernel:
                    audio_in = to_audio_input(wav_path)
                    result = await kernel.run(
                        audio=audio_in,
                        text=state.reference_text,
                        lang=state.lang,
                    )
                    state.last_result = result
                    
                    # Actualizar stats
                    score = 1 - result.get("per", 0)
                    new_achievements = stats.add_practice(score)
                    state.session_practices += 1
                    
                    for achievement in new_achievements:
                        console.print(f"[bold yellow]{achievement}[/bold yellow]")
                        time.sleep(0.8)
                else:
                    # Mock result para testing sin kernel
                    state.last_result = {
                        "per": 0.15,
                        "alignment": [
                            ("h", "h"),
                            ("o", "o"),
                            ("l", "l"),
                            ("a", "a"),
                        ],
                    }
                    stats.add_practice(0.85)
                    state.session_practices += 1
                
                cleanup_temp(wav_path)
                
            except Exception as e:
                state.is_recording = False
                console.print(f"[red]Error: {e}[/red]")
                time.sleep(2)
                
        elif cmd in ("t", "text"):
            try:
                new_text = console.input("[cyan]Texto de referencia:[/cyan] ").strip()
                if new_text:
                    state.reference_text = new_text
            except (KeyboardInterrupt, EOFError):
                pass
                
        elif cmd in ("m", "mode"):
            if state.mode == TranscriptionMode.PHONEMIC:
                state.mode = TranscriptionMode.PHONETIC
                console.print("[yellow]Modo: [fonético][/yellow]")
            else:
                state.mode = TranscriptionMode.PHONEMIC
                console.print("[yellow]Modo: /fonémico/[/yellow]")
            time.sleep(0.8)
            
        elif cmd in ("l", "lang"):
            try:
                new_lang = console.input("[cyan]Idioma (es, en, etc.):[/cyan] ").strip().lower()
                if new_lang:
                    state.lang = new_lang
            except (KeyboardInterrupt, EOFError):
                pass
                
        elif cmd in ("f", "feedback"):
            if state.feedback_level == FeedbackLevel.CASUAL:
                state.feedback_level = FeedbackLevel.PRECISE
                console.print("[yellow]Feedback: Preciso (detallado)[/yellow]")
            else:
                state.feedback_level = FeedbackLevel.CASUAL
                console.print("[yellow]Feedback: Casual (sencillo)[/yellow]")
            time.sleep(0.8)
            
        elif cmd in ("s", "stats"):
            _show_stats_popup(stats)
        
        elif cmd == "help":
            console.print(Panel(
                "[cyan]r[/cyan] - Grabar audio\n"
                "[cyan]t[/cyan] - Cambiar texto de referencia\n"
                "[cyan]m[/cyan] - Alternar modo fonémico/fonético\n"
                "[cyan]l[/cyan] - Cambiar idioma\n"
                "[cyan]f[/cyan] - Cambiar nivel de feedback\n"
                "[cyan]s[/cyan] - Ver estadísticas\n"
                "[cyan]q[/cyan] - Salir",
                title="Ayuda",
            ))
            input("Presiona ENTER para continuar...")
    
    # Cleanup
    if kernel:
        await kernel.teardown()
    
    console.print("\n[bold magenta]¡Hasta pronto! 👋[/bold magenta]")
    console.print(f"Sesión: {state.session_practices} prácticas")
