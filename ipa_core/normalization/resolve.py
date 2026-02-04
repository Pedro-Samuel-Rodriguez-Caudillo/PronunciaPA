"""Helpers para resolver inventarios desde language packs."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from ipa_core.normalization.inventory import Inventory
from ipa_core.packs.loader import DEFAULT_PACKS_DIR


_DEFAULT_PACK_BY_LANG = {
    "en": "en-us",
    "es": "es-mx",
}


def resolve_pack_id(
    *,
    lang: Optional[str] = None,
    pack: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> Optional[str]:
    """Resolver el ID de pack a partir de lang/pack y la carpeta de packs."""
    candidates: list[str] = []
    if pack:
        candidates.append(pack.lower())
    if lang:
        lang_norm = lang.lower()
        candidates.append(lang_norm)
        if "-" not in lang_norm:
            default = _DEFAULT_PACK_BY_LANG.get(lang_norm)
            if default:
                candidates.append(default)
        else:
            base = lang_norm.split("-", 1)[0]
            default = _DEFAULT_PACK_BY_LANG.get(base)
            if default:
                candidates.append(default)
    packs_dir = base_dir or DEFAULT_PACKS_DIR
    for candidate in candidates:
        inv_path = packs_dir / candidate / "inventory.yaml"
        if inv_path.exists():
            return candidate
    return None


def load_inventory_for(
    *,
    lang: Optional[str] = None,
    pack: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> Tuple[Optional[Inventory], Optional[str]]:
    """Cargar inventario desde un pack si existe."""
    packs_dir = base_dir or DEFAULT_PACKS_DIR
    pack_id = resolve_pack_id(lang=lang, pack=pack, base_dir=packs_dir)
    if not pack_id:
        return None, None
    inv_path = packs_dir / pack_id / "inventory.yaml"
    return Inventory.from_yaml(inv_path), pack_id


__all__ = ["resolve_pack_id", "load_inventory_for"]
