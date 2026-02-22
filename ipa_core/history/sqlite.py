"""Implementación SQLite del HistoryPort.

Almacena intentos de pronunciación y estadísticas de maestría en un
fichero SQLite local.  Los datos persisten entre reinicios del servidor.

Uso típico
----------
::

    from ipa_core.history.sqlite import SQLiteHistory
    history = SQLiteHistory(db_path="data/history.db")
    await history.setup()   # crea tablas si no existen

Esquema
-------
``attempts``
    - attempt_id  TEXT PRIMARY KEY
    - user_id     TEXT NOT NULL
    - lang        TEXT NOT NULL
    - text        TEXT NOT NULL
    - score       REAL NOT NULL
    - per         REAL NOT NULL
    - ops         TEXT NOT NULL  (JSON serializado)
    - meta        TEXT           (JSON serializado, nullable)
    - timestamp   REAL NOT NULL

``phoneme_stats``  (vista materializada / cache)
    - user_id     TEXT NOT NULL
    - lang        TEXT NOT NULL
    - phoneme     TEXT NOT NULL
    - attempts    INTEGER NOT NULL
    - correct     INTEGER NOT NULL
    PRIMARY KEY (user_id, lang, phoneme)

Dependencias opcionales
-----------------------
Requiere ``aiosqlite`` para I/O asíncrono.  Si no está instalado,
``setup()`` emite un aviso y las operaciones lanzarán ``RuntimeError``
con mensaje claro.  Instalar con: ``pip install aiosqlite``.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from collections import defaultdict
from typing import Any, Optional


_AIOSQLITE_AVAILABLE = False
try:
    import aiosqlite  # type: ignore
    _AIOSQLITE_AVAILABLE = True
except ImportError:
    aiosqlite = None  # type: ignore


_CREATE_ATTEMPTS = """
CREATE TABLE IF NOT EXISTS attempts (
    attempt_id  TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    lang        TEXT NOT NULL,
    text        TEXT NOT NULL,
    score       REAL NOT NULL,
    per         REAL NOT NULL,
    ops         TEXT NOT NULL,
    meta        TEXT,
    timestamp   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts (user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_user_lang ON attempts (user_id, lang);
"""

_CREATE_PHONEME = """
CREATE TABLE IF NOT EXISTS phoneme_stats (
    user_id   TEXT NOT NULL,
    lang      TEXT NOT NULL,
    phoneme   TEXT NOT NULL,
    attempts  INTEGER NOT NULL DEFAULT 0,
    correct   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, lang, phoneme)
);
"""


def _mastery_level(error_rate: float) -> str:
    if error_rate < 0.05:
        return "mastered"
    if error_rate < 0.20:
        return "proficient"
    if error_rate < 0.50:
        return "developing"
    return "beginner"


class SQLiteHistory:
    """Implementación persistente del HistoryPort usando SQLite + aiosqlite.

    Parámetros
    ----------
    db_path : str | Path
        Ruta al fichero SQLite.  Se crea si no existe.
        Usar ``:memory:`` para almacenamiento volátil (tests).
    """

    def __init__(self, db_path: str | Path = "data/pronunciapa_history.db") -> None:
        self._db_path = str(db_path)
        self._conn: Optional[Any] = None  # aiosqlite.Connection

    async def setup(self) -> None:
        """Abrir conexión y crear tablas si no existen."""
        if not _AIOSQLITE_AVAILABLE:
            import warnings
            warnings.warn(
                "aiosqlite no está instalado; SQLiteHistory no funcionará. "
                "Instala con: pip install aiosqlite",
                RuntimeWarning,
                stacklevel=2,
            )
            return

        # Crear directorio padre si no existe (excepto :memory:)
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # Re-import locally so Pylance sees a non-None module type.
        import aiosqlite as _aio  # type: ignore[import]

        self._conn = await _aio.connect(self._db_path)
        assert self._conn is not None  # narrow Optional[Any] → Any
        self._conn.row_factory = _aio.Row
        await self._conn.executescript(_CREATE_ATTEMPTS)
        await self._conn.executescript(_CREATE_PHONEME)
        await self._conn.commit()

    async def teardown(self) -> None:
        """Cerrar conexión."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    def _require_conn(self) -> Any:
        if not _AIOSQLITE_AVAILABLE:
            raise RuntimeError(
                "aiosqlite no está instalado. Instala con: pip install aiosqlite"
            )
        if self._conn is None:
            raise RuntimeError("SQLiteHistory.setup() no ha sido llamado.")
        return self._conn

    async def record_attempt(
        self,
        *,
        user_id: str,
        lang: str,
        text: str,
        score: float,
        per: float,
        ops: list[dict[str, Any]],
        meta: Optional[dict[str, Any]] = None,
    ) -> str:
        conn = self._require_conn()
        attempt_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO attempts
                (attempt_id, user_id, lang, text, score, per, ops, meta, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                user_id,
                lang,
                text,
                round(score, 2),
                round(per, 4),
                json.dumps(ops, ensure_ascii=False),
                json.dumps(meta or {}, ensure_ascii=False),
                time.time(),
            ),
        )
        # Actualizar estadísticas de fonemas
        await self._update_phoneme_stats(conn, user_id=user_id, lang=lang, ops=ops)
        await conn.commit()
        return attempt_id

    async def _update_phoneme_stats(
        self,
        conn: Any,
        *,
        user_id: str,
        lang: str,
        ops: list[dict[str, Any]],
    ) -> None:
        """Actualizar contadores de fonemas a partir de las operaciones de edición."""
        phoneme_data: dict[str, dict[str, int]] = defaultdict(lambda: {"attempts": 0, "correct": 0})
        for op in ops:
            ref = op.get("ref") or ""
            hyp = op.get("hyp") or ""
            op_type = op.get("op", "")
            if op_type == "eq" and ref:
                phoneme_data[ref]["attempts"] += 1
                phoneme_data[ref]["correct"] += 1
            elif op_type in ("sub", "del") and ref:
                phoneme_data[ref]["attempts"] += 1
                # correct += 0 (error)

        for phoneme, counts in phoneme_data.items():
            await conn.execute(
                """
                INSERT INTO phoneme_stats (user_id, lang, phoneme, attempts, correct)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, lang, phoneme) DO UPDATE SET
                    attempts = attempts + excluded.attempts,
                    correct  = correct  + excluded.correct
                """,
                (user_id, lang, phoneme, counts["attempts"], counts["correct"]),
            )

    async def get_attempts(
        self,
        user_id: str,
        *,
        lang: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conn = self._require_conn()
        if lang:
            cursor = await conn.execute(
                "SELECT * FROM attempts WHERE user_id=? AND lang=? "
                "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (user_id, lang, limit, offset),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM attempts WHERE user_id=? "
                "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (user_id, limit, offset),
            )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["ops"] = json.loads(d.get("ops") or "[]")
            d["meta"] = json.loads(d.get("meta") or "{}")
            result.append(d)
        return result

    async def get_phoneme_stats(
        self,
        user_id: str,
        lang: str,
    ) -> list[dict[str, Any]]:
        conn = self._require_conn()
        cursor = await conn.execute(
            "SELECT phoneme, attempts, correct FROM phoneme_stats "
            "WHERE user_id=? AND lang=? ORDER BY attempts DESC",
            (user_id, lang),
        )
        rows = await cursor.fetchall()
        stats = []
        for row in rows:
            d = dict(row)
            total = d["attempts"]
            correct = d["correct"]
            error_rate = 1.0 - (correct / total) if total > 0 else 0.0
            d["error_rate"] = round(error_rate, 4)
            d["mastery_level"] = _mastery_level(error_rate)
            stats.append(d)
        return stats

    async def get_progress(
        self,
        user_id: str,
        lang: str,
        *,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Obtener historial de scores recientes para visualizar progreso."""
        conn = self._require_conn()
        cursor = await conn.execute(
            "SELECT score, per, timestamp FROM attempts "
            "WHERE user_id=? AND lang=? ORDER BY timestamp DESC LIMIT ?",
            (user_id, lang, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in reversed(rows)]  # cronológico


__all__ = ["SQLiteHistory"]
