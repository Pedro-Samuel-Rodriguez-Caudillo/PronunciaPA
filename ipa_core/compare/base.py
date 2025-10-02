from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

AlignmentOp = Tuple[str, str, str]


@dataclass
class PhonemeStats:
    """Resumen de métricas por fonema."""

    matches: int = 0
    substitutions: int = 0
    deletions: int = 0
    insertions: int = 0

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions


@dataclass
class CompareResult:
    """Resultado de la comparación entre dos secuencias IPA."""

    per: float
    ops: List[AlignmentOp]
    total_ref_tokens: int
    matches: int
    substitutions: int
    insertions: int
    deletions: int
    per_class: Dict[str, PhonemeStats] = field(default_factory=dict)


class Comparator(ABC):
    @abstractmethod
    def compare(self, ref_ipa: str, hyp_ipa: str) -> CompareResult:
        """Compara dos cadenas IPA y retorna métricas y operaciones."""
        raise NotImplementedError
