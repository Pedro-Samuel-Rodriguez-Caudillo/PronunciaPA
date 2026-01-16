"""Local persistence for feedback results."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

DEFAULT_FEEDBACK_DIR = Path("outputs") / "feedback"
DEFAULT_FEEDBACK_FILE = "feedback.jsonl"
DEFAULT_INDEX_FILE = "index.json"
DEFAULT_EXPORT_FILE = "feedback_export.json"


class FeedbackStore:
    """Append feedback payloads to a JSONL file and keep an index."""

    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
        *,
        filename: str = DEFAULT_FEEDBACK_FILE,
        index_filename: str = DEFAULT_INDEX_FILE,
    ) -> None:
        self._base_dir = Path(base_dir) if base_dir else DEFAULT_FEEDBACK_DIR
        self._filename = filename
        self._index_filename = index_filename

    def append(
        self,
        payload: dict[str, Any],
        *,
        audio: Optional[dict[str, Any]] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> Path:
        created_at = datetime.now(timezone.utc).isoformat()
        entry = {
            "created_at": created_at,
            "audio": audio or {},
            "payload": payload,
            "meta": meta or {},
        }
        self._base_dir.mkdir(parents=True, exist_ok=True)
        path = self._base_dir / self._filename
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
        self._update_index(
            entry_id=uuid4().hex,
            created_at=created_at,
            payload=payload,
            audio=audio,
            meta=meta,
            jsonl_path=path,
        )
        return path

    def export(self, dest: Optional[Path | str] = None) -> Path:
        """Export the index to a standalone JSON file."""
        index = self._load_index()
        export_path = Path(dest) if dest else self._base_dir / DEFAULT_EXPORT_FILE
        if export_path.is_dir():
            export_path = export_path / DEFAULT_EXPORT_FILE
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with export_path.open("w", encoding="utf-8") as handle:
            json.dump(index, handle, ensure_ascii=True, indent=2)
        return export_path

    def _index_path(self) -> Path:
        return self._base_dir / self._index_filename

    def _load_index(self) -> list[dict[str, Any]]:
        path = self._index_path()
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []

    def _update_index(
        self,
        *,
        entry_id: str,
        created_at: str,
        payload: dict[str, Any],
        audio: Optional[dict[str, Any]],
        meta: Optional[dict[str, Any]],
        jsonl_path: Path,
    ) -> None:
        index = self._load_index()
        summary = self._build_summary(payload, audio, meta)
        summary.update(
            {
                "id": entry_id,
                "created_at": created_at,
                "jsonl_path": str(jsonl_path),
                "seq": len(index) + 1,
            }
        )
        index.append(summary)
        index_path = self._index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with index_path.open("w", encoding="utf-8") as handle:
            json.dump(index, handle, ensure_ascii=True, indent=2)

    @staticmethod
    def _build_summary(
        payload: dict[str, Any],
        audio: Optional[dict[str, Any]],
        meta: Optional[dict[str, Any]],
    ) -> dict[str, Any]:
        report = payload.get("report", {}) if isinstance(payload, dict) else {}
        compare = payload.get("compare", {}) if isinstance(payload, dict) else {}
        feedback = payload.get("feedback", {}) if isinstance(payload, dict) else {}
        per = compare.get("per") or report.get("metrics", {}).get("per")
        lang = report.get("lang") or (meta or {}).get("lang")
        summary = feedback.get("summary") or feedback.get("advice_short")
        audio_path = (audio or {}).get("path")
        return {
            "lang": lang,
            "per": per,
            "summary": summary,
            "audio_path": audio_path,
        }


__all__ = [
    "FeedbackStore",
    "DEFAULT_FEEDBACK_DIR",
    "DEFAULT_FEEDBACK_FILE",
    "DEFAULT_INDEX_FILE",
    "DEFAULT_EXPORT_FILE",
]
