"""Inventario fonético de un idioma/dialecto.

Define qué fonemas y alófonos son válidos para el sistema fonológico.
Puede operar independientemente o componerse con
``normalization.inventory.Inventory`` para reutilizar alias y OOV handling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set

import yaml

from ipa_core.phonology.segment import Segment
from ipa_core.phonology.features import get_features

if TYPE_CHECKING:
    from ipa_core.normalization.inventory import Inventory


@dataclass
class PhoneticInventory:
    """Inventario fonético de un dialecto.
    
    Atributos
    ---------
    language : str
        Código de idioma (es, en).
    dialect : str
        Código de dialecto (es-mx, en-us).
    phonemes : Dict[str, Segment]
        Mapeo de símbolos a fonemas.
    allophones : Dict[str, List[Segment]]
        Mapeo de fonema base a sus alófonos.
    _norm_inventory : Inventory | None
        Inventario de normalización asociado (bridge, opcional).
    """
    language: str
    dialect: str
    phonemes: Dict[str, Segment] = field(default_factory=dict)
    allophones: Dict[str, List[Segment]] = field(default_factory=dict)
    _norm_inventory: Optional[object] = field(default=None, repr=False)

    def add_phoneme(self, symbol: str) -> Segment:
        """Añadir un fonema al inventario."""
        features = get_features(symbol)
        segment = Segment.phoneme(symbol, features)
        self.phonemes[symbol] = segment
        return segment
    
    def add_allophone(self, symbol: str, base_phoneme: str) -> Segment:
        """Añadir un alófono al inventario."""
        if base_phoneme not in self.phonemes:
            raise ValueError(f"Base phoneme /{base_phoneme}/ not in inventory")
        
        features = get_features(symbol)
        segment = Segment.allophone(symbol, base_phoneme, features)
        
        if base_phoneme not in self.allophones:
            self.allophones[base_phoneme] = []
        self.allophones[base_phoneme].append(segment)
        
        return segment
    
    def is_phoneme(self, symbol: str) -> bool:
        """Verificar si un símbolo es fonema del inventario."""
        return symbol in self.phonemes
    
    def is_allophone(self, symbol: str) -> bool:
        """Verificar si un símbolo es alófono conocido."""
        for allos in self.allophones.values():
            if any(a.symbol == symbol for a in allos):
                return True
        return False
    
    def get_base_phoneme(self, symbol: str) -> Optional[str]:
        """Obtener el fonema base de un alófono."""
        for base, allos in self.allophones.items():
            if any(a.symbol == symbol for a in allos):
                return base
        # Si es fonema, retornarse a sí mismo
        if symbol in self.phonemes:
            return symbol
        return None
    
    def get_allophones_of(self, phoneme: str) -> List[Segment]:
        """Obtener todos los alófonos de un fonema."""
        return self.allophones.get(phoneme, [])
    
    def get_all_phonemes(self) -> List[str]:
        """Obtener lista de todos los fonemas."""
        return list(self.phonemes.keys())
    
    def get_all_phones(self) -> Set[str]:
        """Obtener todos los sonidos (fonemas + alófonos)."""
        phones = set(self.phonemes.keys())
        for allos in self.allophones.values():
            phones.update(a.symbol for a in allos)
        return phones
    
    def collapse_to_phoneme(self, phone: str) -> str:
        """Colapsar un fono a su fonema base.
        
        Si es fonema, retorna el mismo.
        Si es alófono, retorna el fonema base.
        Si es desconocido, retorna el mismo.
        """
        base = self.get_base_phoneme(phone)
        return base if base else phone
    
    @classmethod
    def from_yaml(cls, path: Path) -> "PhoneticInventory":
        """Cargar inventario desde archivo YAML."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        inv = cls(
            language=data.get("language", ""),
            dialect=data.get("dialect", data.get("accent", "")),
        )
        
        # Cargar fonemas
        inventory_data = data.get("inventory", {})
        for symbol in inventory_data.get("consonants", []):
            inv.add_phoneme(symbol)
        for symbol in inventory_data.get("vowels", []):
            inv.add_phoneme(symbol)
        
        # Cargar alófonos si se definen
        allophone_data = data.get("allophones", {})
        for base, allos in allophone_data.items():
            for allo in allos:
                inv.add_allophone(allo, base)
        
        # Cargar aliases como alófonos
        alias_data = data.get("aliases", {})
        for allo, base in alias_data.items():
            if base in inv.phonemes:
                inv.add_allophone(allo, base)
        
        return inv
    
    def to_yaml(self) -> str:
        """Serializar a YAML."""
        consonants = [s for s, seg in self.phonemes.items() 
                      if seg.features and seg.features.is_positive("consonantal")]
        vowels = [s for s, seg in self.phonemes.items()
                  if seg.features and seg.features.is_positive("syllabic")]
        
        data = {
            "language": self.language,
            "dialect": self.dialect,
            "inventory": {
                "consonants": consonants,
                "vowels": vowels,
            },
            "allophones": {
                base: [a.symbol for a in allos]
                for base, allos in self.allophones.items()
            },
        }
        return yaml.dump(data, allow_unicode=True, sort_keys=False)

    # ── Bridge con normalization.inventory.Inventory ──

    @classmethod
    def from_norm_inventory(cls, norm_inv: "Inventory") -> "PhoneticInventory":
        """Construir un PhoneticInventory desde un Inventory de normalización.

        Reutiliza el set de consonantes/vocales ya cargado y añade
        features SPE a cada símbolo.  El Inventory original se almacena
        como ``_norm_inventory`` para delegar alias y OOV handling.
        """
        inv = cls(
            language=norm_inv.language,
            dialect=norm_inv.accent or norm_inv.language,
            _norm_inventory=norm_inv,
        )
        for symbol in norm_inv.consonants | norm_inv.vowels:
            try:
                inv.add_phoneme(symbol)
            except Exception:  # noqa: BLE001
                # Símbolos sin features definidas todavía — skip silently
                pass
        return inv

    def get_canonical(self, token: str) -> str:
        """Resolve aliases delegando al Inventory de normalización si existe."""
        if self._norm_inventory is not None:
            from ipa_core.normalization.inventory import Inventory

            assert isinstance(self._norm_inventory, Inventory)
            return self._norm_inventory.get_canonical(token)
        # Fallback: fonema → sí mismo, alófono → base
        return self.collapse_to_phoneme(token)

    def normalize_sequence(
        self,
        tokens: list[str],
        *,
        oov_strategy: str = "mark",
    ) -> tuple[list[str], list[str]]:
        """Delegación al Inventory de normalización si existe."""
        if self._norm_inventory is not None:
            from ipa_core.normalization.inventory import Inventory

            assert isinstance(self._norm_inventory, Inventory)
            return self._norm_inventory.normalize_sequence(
                tokens, oov_strategy=oov_strategy,
            )
        # Fallback simple: collapse to phoneme, no OOV tracking
        return [self.collapse_to_phoneme(t) for t in tokens], []


__all__ = ["PhoneticInventory"]
