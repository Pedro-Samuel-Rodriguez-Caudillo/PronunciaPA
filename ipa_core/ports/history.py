"""Puerto de historial y progreso de pronunciación.

Define el contrato para almacenar intentos de pronunciación y
calcular estadísticas de maestría por fonema por usuario.

Implementaciones
----------------
- ``ipa_core.history.memory.InMemoryHistory`` — almacenamiento volátil
  (se pierde al reiniciar el servidor).  Útil para demos y CI.
- Futuras: SQLite, PostgreSQL, Redis.

Estructura de un intento (``AttemptRecord``)
--------------------------------------------
- attempt_id : str  — UUID generado por la implementación
- user_id    : str  — identificador opaco del usuario
- lang       : str  — idioma del intento ("es", "en", …)
- text       : str  — texto que el usuario intentó pronunciar
- score      : float [0-100] — puntuación global de la comparación
- per        : float [0-1]   — Phone Error Rate
- ops        : list[dict]    — operaciones de edición (eq/sub/ins/del)
- timestamp  : float         — epoch UTC (time.time())

Estadísticas de fonema (``PhonemeStats``)
------------------------------------------
- phoneme       : str  — símbolo IPA
- attempts      : int  — total de intentos en los que aparece
- correct       : int  — veces que fue eq (sin error)
- error_rate    : float — porcentaje de error [0-1]
- mastery_level : str  — "beginner" / "developing" / "proficient" / "mastered"
"""
from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class HistoryPort(Protocol):
    """Contrato para persistencia de historial de pronunciación."""

    async def setup(self) -> None:
        """Inicialización asíncrona (conexión a BD, etc.)."""
        ...

    async def teardown(self) -> None:
        """Limpieza de recursos."""
        ...

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
        """Registrar un intento de pronunciación.

        Parámetros
        ----------
        user_id : str
            Identificador del usuario (opaco, sin PII obligatorio).
        lang : str
            Idioma del intento ("es", "en-us", …).
        text : str
            Texto que el usuario intentó pronunciar.
        score : float
            Puntuación global (0-100).
        per : float
            Phone Error Rate (0-1).
        ops : list[dict]
            Lista de operaciones de edición con campos ``op``, ``ref``, ``hyp``.
        meta : dict, optional
            Metadatos extra (ASR backend, modo, nivel de evaluación, etc.).

        Retorna
        -------
        str
            ``attempt_id`` único generado por la implementación.
        """
        ...

    async def get_attempts(
        self,
        user_id: str,
        *,
        lang: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Obtener intentos de un usuario, más recientes primero.

        Parámetros
        ----------
        user_id : str
        lang : str, optional
            Filtrar por idioma.
        limit : int
            Máximo de registros a retornar.
        offset : int
            Paginación.

        Retorna
        -------
        list[dict]
            Lista de AttemptRecord dicts ordenados por timestamp desc.
        """
        ...

    async def get_phoneme_stats(
        self,
        user_id: str,
        lang: str,
    ) -> list[dict[str, Any]]:
        """Calcular estadísticas de maestría por fonema.

        Parámetros
        ----------
        user_id : str
        lang : str
            Idioma para el que se calculan las estadísticas.

        Retorna
        -------
        list[dict]
            Lista de PhonemeStats dicts ordenados por error_rate desc
            (primero los fonemas con más errores).
        """
        ...

    async def get_summary(self, user_id: str) -> dict[str, Any]:
        """Resumen global de progreso del usuario.

        Retorna campos:
        - total_attempts : int
        - avg_score      : float
        - languages      : list[str]
        - top_errors     : list[str]  — fonemas con mayor error_rate
        """
        ...


__all__ = ["HistoryPort"]
