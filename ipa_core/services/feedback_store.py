"""Local persistence for feedback results."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DEFAULT_FEEDBACK_DIR = Path("outputs") / "feedback"
DEFAULT_FEEDBACK_FILE = "feedback.jsonl"


class FeedbackStore:
    """Append feedback payloads to a JSONL file."""

    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
        *,
        filename: str = DEFAULT_FEEDBACK_FILE,
    ) -> None:
        self._base_dir = Path(base_dir) if base_dir else DEFAULT_FEEDBACK_DIR
        self._filename = filename

    def append(
        self,
        payload: dict[str, Any],
        *,
        audio: Optional[dict[str, Any]] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> Path:
        entry = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "audio": audio or {},
            "payload": payload,
            "meta": meta or {},
        }
        self._base_dir.mkdir(parents=True, exist_ok=True)
        path = self._base_dir / self._filename
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
        return path


__all__ = ["FeedbackStore", "DEFAULT_FEEDBACK_DIR"]
