"""PipelineTracer — instrumentación concisa del pipeline.

Uso en código::

    tracer = PipelineTracer()

    with tracer.stage("asr") as s:
        result = await asr.transcribe(audio)
        s.detail = f"tokens={result['tokens'][:4]}"

    with tracer.stage("textref") as s:
        ref = await textref.to_ipa(text, lang=lang)
        s.detail = f"tokens={ref['tokens'][:4]}"

    print(tracer.as_text())

Salida::

    Pipeline "hola mundo" | es | 2 stages
    ──────────────────────────────────────────
     asr       ✓  847ms  tokens=['h','o','l','a'] (4)
     textref   ✓    3ms  tokens=['o','l','a'] (3)
    ──────────────────────────────────────────
     PASS  total=850ms
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, List, Literal, Optional


Status = Literal["ok", "fail", "skip"]

# Ancho de columnas en la tabla ASCII
_W_NAME   = 12
_W_STATUS =  2
_W_MS     =  7


@dataclass
class StageRecord:
    """Registro de una etapa del pipeline."""
    name:       str
    status:     Status = "skip"
    elapsed_ms: float  = 0.0
    detail:     str    = ""
    error:      Optional[str] = None
    extra:      dict   = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name":       self.name,
            "status":     self.status,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "detail":     self.detail,
        }
        if self.error:
            d["error"] = self.error
        if self.extra:
            d["extra"] = self.extra
        return d

    def as_line(self) -> str:
        icon = "✓" if self.status == "ok" else ("✗" if self.status == "fail" else "·")
        ms_str = f"{self.elapsed_ms:.0f}ms"
        name_pad  = self.name.ljust(_W_NAME)
        ms_pad    = ms_str.rjust(_W_MS)
        detail    = self.error or self.detail
        return f" {name_pad} {icon}  {ms_pad}  {detail}"


class PipelineTracer:
    """Coleccionador ligero de métricas por etapa del pipeline.

    No tiene dependencias pesadas — solo stdlib.

    Parámetros
    ----------
    label : str, optional
        Etiqueta descriptiva (texto/audio procesado) para el encabezado.
    lang : str, optional
        Código de idioma para el encabezado.
    """

    def __init__(self, label: str = "", lang: str = "") -> None:
        self._label    = label
        self._lang     = lang
        self._records: List[StageRecord] = []
        self._t0       = time.monotonic()

    @contextmanager
    def stage(self, name: str) -> Generator[StageRecord, None, None]:
        """Context manager para instrumentar una etapa.

        El registro devuelto puede ser modificado dentro del bloque::

            with tracer.stage("asr") as s:
                tokens = await asr.transcribe(audio)
                s.detail = f"tokens={tokens[:3]}"

        Si se lanza una excepción, la etapa se marca como *fail* y
        el error se re-lanza para que el llamador lo maneje.
        """
        rec = StageRecord(name=name)
        t = time.monotonic()
        try:
            yield rec
            rec.elapsed_ms = (time.monotonic() - t) * 1000
            rec.status = "ok"
        except Exception as exc:
            rec.elapsed_ms = (time.monotonic() - t) * 1000
            rec.status = "fail"
            rec.error = f"{type(exc).__name__}: {exc}"
            self._records.append(rec)
            raise
        self._records.append(rec)

    # ------------------------------------------------------------------
    # Propiedades de resultados
    # ------------------------------------------------------------------

    @property
    def records(self) -> List[StageRecord]:
        return list(self._records)

    @property
    def total_ms(self) -> float:
        return (time.monotonic() - self._t0) * 1000

    @property
    def failed(self) -> Optional[StageRecord]:
        """Primera etapa fallida, o None si todo fue bien."""
        return next((r for r in self._records if r.status == "fail"), None)

    @property
    def passed(self) -> bool:
        return self.failed is None

    # ------------------------------------------------------------------
    # Serialización
    # ------------------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        """Dict JSON-serializable con todo el trace."""
        return {
            "label":    self._label,
            "lang":     self._lang,
            "passed":   self.passed,
            "total_ms": round(self.total_ms, 1),
            "stages":   [r.as_dict() for r in self._records],
            "failure":  self.failed.as_dict() if self.failed else None,
        }

    def as_text(self) -> str:
        """Tabla ASCII concisa — una línea por etapa."""
        sep = "─" * 50
        header_parts = [f'"{self._label}"'] if self._label else []
        if self._lang:
            header_parts.append(self._lang)
        header_parts.append(f"{len(self._records)} stages")
        lines = [f"Pipeline {' | '.join(header_parts)}", sep]
        for rec in self._records:
            lines.append(rec.as_line())
        lines.append(sep)
        status = "PASS" if self.failed is None else f"FAIL at '{self.failed.name}'"
        lines.append(f" {status}  total={self.total_ms:.0f}ms")
        return "\n".join(lines)


__all__ = ["PipelineTracer", "StageRecord"]
