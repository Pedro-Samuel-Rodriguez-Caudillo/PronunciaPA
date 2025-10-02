"""Paquete de conversión texto -> IPA."""

from .phonemizer_ref import PhonemizerTextRef
from .nop import NoopTextRef

__all__ = ["PhonemizerTextRef", "NoopTextRef"]
