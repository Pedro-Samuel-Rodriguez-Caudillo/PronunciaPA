"""Módulo de normalización IPA.

Proporciona herramientas para normalizar tokens IPA de diferentes
proveedores a un formato consistente basado en el inventario del pack.
"""
from ipa_core.normalization.normalizer import IPANormalizer
from ipa_core.normalization.inventory import Inventory
from ipa_core.normalization.mappings import UNICODE_MAPPINGS, normalize_unicode

__all__ = [
    "IPANormalizer",
    "Inventory",
    "UNICODE_MAPPINGS",
    "normalize_unicode",
]
