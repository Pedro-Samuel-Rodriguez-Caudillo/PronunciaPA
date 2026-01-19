"""Representación de segmentos fonológicos.

Un segmento puede ser un fonema (abstracto) o un alófono (realización).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ipa_core.phonology.features import FeatureBundle


@dataclass
class Segment:
    """Segmento fonológico (fonema o alófono).
    
    Atributos
    ---------
    symbol : str
        Símbolo IPA del segmento.
    is_phoneme : bool
        True si es fonema (subyacente), False si es alófono (superficial).
    base_phoneme : Optional[str]
        Si es alófono, el fonema del cual deriva.
    features : Optional[FeatureBundle]
        Rasgos distintivos del segmento.
    """
    symbol: str
    is_phoneme: bool = True
    base_phoneme: Optional[str] = None
    features: Optional["FeatureBundle"] = None
    
    def __post_init__(self) -> None:
        if not self.is_phoneme and self.base_phoneme is None:
            raise ValueError(f"Allophone {self.symbol} must have a base_phoneme")
    
    def __hash__(self) -> int:
        return hash((self.symbol, self.is_phoneme))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Segment):
            return False
        return self.symbol == other.symbol and self.is_phoneme == other.is_phoneme
    
    def __str__(self) -> str:
        return self.symbol
    
    def __repr__(self) -> str:
        if self.is_phoneme:
            return f"/{self.symbol}/"
        return f"[{self.symbol}]"
    
    def to_dict(self) -> dict:
        """Serializar a diccionario."""
        return {
            "symbol": self.symbol,
            "is_phoneme": self.is_phoneme,
            "base_phoneme": self.base_phoneme,
        }
    
    @classmethod
    def phoneme(cls, symbol: str, features: Optional["FeatureBundle"] = None) -> "Segment":
        """Crear un fonema."""
        return cls(symbol=symbol, is_phoneme=True, features=features)
    
    @classmethod
    def allophone(
        cls, 
        symbol: str, 
        base_phoneme: str,
        features: Optional["FeatureBundle"] = None,
    ) -> "Segment":
        """Crear un alófono."""
        return cls(
            symbol=symbol, 
            is_phoneme=False, 
            base_phoneme=base_phoneme,
            features=features,
        )


@dataclass
class SegmentSequence:
    """Secuencia de segmentos con nivel de representación.
    
    Atributos
    ---------
    segments : List[Segment]
        Lista de segmentos.
    level : str
        Nivel de representación: "phonemic" o "phonetic".
    """
    segments: List[Segment] = field(default_factory=list)
    level: str = "phonemic"  # "phonemic" | "phonetic"
    
    def __post_init__(self) -> None:
        if self.level not in ("phonemic", "phonetic"):
            raise ValueError(f"Invalid level: {self.level}")
    
    def to_ipa(self) -> str:
        """Convertir a string IPA con delimitadores apropiados."""
        ipa = "".join(s.symbol for s in self.segments)
        if self.level == "phonemic":
            return f"/{ipa}/"
        return f"[{ipa}]"
    
    @classmethod
    def from_string(
        cls, 
        ipa: str, 
        level: str = "phonemic",
        segment_map: Optional[dict] = None,
    ) -> "SegmentSequence":
        """Crear desde string IPA.
        
        Parámetros
        ----------
        ipa : str
            String IPA (sin delimitadores /.../ o [...]).
        level : str
            Nivel de representación.
        segment_map : dict
            Mapeo opcional de símbolos a Segment.
        """
        # Remover delimitadores si existen
        ipa = ipa.strip("/[]")
        
        segments = []
        i = 0
        while i < len(ipa):
            # Intentar match de 2 caracteres primero (dígrafos como tʃ)
            if i + 1 < len(ipa) and ipa[i:i+2] in ("tʃ", "dʒ", "ts", "dz"):
                symbol = ipa[i:i+2]
                i += 2
            else:
                symbol = ipa[i]
                i += 1
            
            if segment_map and symbol in segment_map:
                segments.append(segment_map[symbol])
            else:
                # Crear segmento simple (siempre como fonema base)
                # El nivel se indica en la secuencia, no en cada segmento
                segments.append(Segment(symbol=symbol, is_phoneme=True))
        
        return cls(segments=segments, level=level)
    
    def __len__(self) -> int:
        return len(self.segments)
    
    def __iter__(self):
        return iter(self.segments)
    
    def __getitem__(self, idx: int) -> Segment:
        return self.segments[idx]


__all__ = [
    "Segment",
    "SegmentSequence",
]
