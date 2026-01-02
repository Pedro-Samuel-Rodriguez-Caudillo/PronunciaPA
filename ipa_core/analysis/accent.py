"""Análisis de acento y feedback explícito."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional

import yaml

from ipa_core.types import EditOp, Token

_DEFAULT_PROFILE_PATH = Path(__file__).resolve().parents[2] / "configs" / "accents.yaml"


def load_profile(path_or_name: Optional[str] = None) -> dict[str, Any]:
    """Carga un perfil de acento desde path o nombre."""
    if path_or_name:
        candidate = Path(path_or_name)
        if candidate.exists():
            return _load_yaml(candidate)

        accents_dir = Path.home() / ".pronunciapa" / "accents"
        for suffix in (".yaml", ".yml"):
            named = accents_dir / f"{path_or_name}{suffix}"
            if named.exists():
                return _load_yaml(named)
        raise FileNotFoundError(f"Perfil de acento no encontrado: {path_or_name}")

    if _DEFAULT_PROFILE_PATH.exists():
        return _load_yaml(_DEFAULT_PROFILE_PATH)
    raise FileNotFoundError("Perfil de acento por defecto no encontrado")


def rank_accents(
    per_by_accent: dict[str, float],
    accent_labels: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """Ordena acentos por PER y asigna confianza relativa."""
    if not per_by_accent:
        return []
    scores = {accent: -per for accent, per in per_by_accent.items()}
    max_score = max(scores.values())
    exp_scores = {accent: math.exp(score - max_score) for accent, score in scores.items()}
    total = sum(exp_scores.values()) or 1.0

    ranking = []
    for accent, per in per_by_accent.items():
        confidence = exp_scores[accent] / total
        ranking.append(
            {
                "accent": accent,
                "label": (accent_labels or {}).get(accent, accent),
                "per": per,
                "confidence": confidence,
            }
        )
    ranking.sort(key=lambda item: item["per"])
    return ranking


def extract_features(
    alignment: list[tuple[Optional[Token], Optional[Token]]],
    features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extrae diferencias relevantes según pares de rasgos definidos."""
    results: list[dict[str, Any]] = []
    for feature in features:
        pairs = feature.get("pairs", [])
        matched_variants = []
        total_matches = 0
        for target, alt in pairs:
            alt_token = None if alt in (None, "", "_") else alt
            count = 0
            for ref, hyp in alignment:
                if ref != target:
                    continue
                if alt_token is None:
                    if hyp is None:
                        count += 1
                elif hyp == alt_token:
                    count += 1
            if count:
                matched_variants.append({"target": target, "alt": alt_token, "count": count})
                total_matches += count
        results.append(
            {
                "id": feature.get("id"),
                "label": feature.get("label", feature.get("id")),
                "matches": total_matches,
                "variants": matched_variants,
            }
        )
    return results


def build_feedback(ops: list[EditOp]) -> list[dict[str, Any]]:
    """Agrupa diferencias de tokens en formato ref -> hyp."""
    counts: dict[tuple[str, str], int] = {}
    for op in ops:
        if op["op"] == "eq":
            continue
        ref = op.get("ref") or "_"
        hyp = op.get("hyp") or "_"
        key = (ref, hyp)
        counts[key] = counts.get(key, 0) + 1

    feedback = [
        {"ref": ref, "hyp": hyp, "count": count} for (ref, hyp), count in counts.items()
    ]
    feedback.sort(key=lambda item: item["count"], reverse=True)
    return feedback


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


__all__ = ["load_profile", "rank_accents", "extract_features", "build_feedback"]
