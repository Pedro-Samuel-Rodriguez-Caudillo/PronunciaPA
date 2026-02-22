"""Implementación en memoria del HistoryPort.

Almacena intentos y estadísticas en RAM.  Los datos se pierden al
reiniciar el proceso.  Útil para demos, CI, y despliegues sin BD.

Para persistencia entre reinicios usar SQLite (futuro) o montar el
directorio de datos en un volumen Docker.
"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Any, Optional


def _mastery_level(error_rate: float) -> str:
    if error_rate < 0.05:
        return "mastered"
    if error_rate < 0.20:
        return "proficient"
    if error_rate < 0.50:
        return "developing"
    return "beginner"


class InMemoryHistory:
    """Implementación volátil del HistoryPort.

    Thread-safe para uso dentro de un solo proceso asyncio (sin locks
    explícitos porque asyncio es cooperativo de un solo hilo).
    """

    def __init__(self) -> None:
        # user_id → lista de AttemptRecord (más reciente al final)
        self._attempts: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

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
        attempt_id = str(uuid.uuid4())
        record: dict[str, Any] = {
            "attempt_id": attempt_id,
            "user_id": user_id,
            "lang": lang,
            "text": text,
            "score": round(score, 2),
            "per": round(per, 4),
            "ops": ops,
            "timestamp": time.time(),
            "meta": meta or {},
        }
        self._attempts[user_id].append(record)
        return attempt_id

    async def get_attempts(
        self,
        user_id: str,
        *,
        lang: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        records = self._attempts.get(user_id, [])
        if lang:
            records = [r for r in records if r.get("lang") == lang]
        # Más recientes primero
        records = list(reversed(records))
        return records[offset : offset + limit]

    async def get_phoneme_stats(
        self,
        user_id: str,
        lang: str,
    ) -> list[dict[str, Any]]:
        records = [
            r for r in self._attempts.get(user_id, [])
            if r.get("lang") == lang
        ]
        # Acumular por fonema
        phoneme_attempts: dict[str, int] = defaultdict(int)
        phoneme_correct: dict[str, int] = defaultdict(int)

        for record in records:
            for op in record.get("ops", []):
                ref = op.get("ref")
                if not ref:
                    continue
                phoneme_attempts[ref] += 1
                if op.get("op") == "eq":
                    phoneme_correct[ref] += 1

        stats: list[dict[str, Any]] = []
        for phoneme, total in phoneme_attempts.items():
            correct = phoneme_correct.get(phoneme, 0)
            error_rate = (total - correct) / total if total > 0 else 0.0
            stats.append({
                "phoneme": phoneme,
                "attempts": total,
                "correct": correct,
                "error_rate": round(error_rate, 4),
                "mastery_level": _mastery_level(error_rate),
            })

        # Ordenar por error_rate desc (problemas primero)
        stats.sort(key=lambda s: s["error_rate"], reverse=True)
        return stats

    async def get_summary(self, user_id: str) -> dict[str, Any]:
        records = self._attempts.get(user_id, [])
        if not records:
            return {
                "total_attempts": 0,
                "avg_score": 0.0,
                "languages": [],
                "top_errors": [],
            }

        total = len(records)
        avg_score = sum(r["score"] for r in records) / total
        languages = sorted({r["lang"] for r in records})

        # Top fonemas con error agrupados por todos los idiomas
        phoneme_errors: dict[str, int] = defaultdict(int)
        phoneme_total: dict[str, int] = defaultdict(int)
        for record in records:
            for op in record.get("ops", []):
                ref = op.get("ref")
                if not ref:
                    continue
                phoneme_total[ref] += 1
                if op.get("op") != "eq":
                    phoneme_errors[ref] += 1

        top_errors = sorted(
            phoneme_errors,
            key=lambda p: phoneme_errors[p] / max(phoneme_total[p], 1),
            reverse=True,
        )[:5]

        return {
            "total_attempts": total,
            "avg_score": round(avg_score, 2),
            "languages": languages,
            "top_errors": top_errors,
        }


__all__ = ["InMemoryHistory"]
