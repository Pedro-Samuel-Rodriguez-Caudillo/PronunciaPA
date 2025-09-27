from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class CompareResult:
    per: float
    ops: List[Tuple[str, str, str]]  # (op, ref_tok, hyp_tok)

class Comparator(ABC):
    @abstractmethod
    def compare(self, ref_ipa: str, hyp_ipa: str) -> CompareResult:
        """Compara dos cadenas IPA y retorna métricas y operaciones."""
        raise NotImplementedError
