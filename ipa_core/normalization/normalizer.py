"""Normalizador IPA principal.

Proporciona la clase IPANormalizer que coordina la normalización
de tokens IPA usando mapeos Unicode y el inventario del pack.
"""
from __future__ import annotations

from typing import Any, List, Optional, Sequence

from ipa_core.normalization.inventory import Inventory
from ipa_core.normalization.mappings import normalize_unicode
from ipa_core.plugins.base import BasePlugin
from ipa_core.types import Token, TokenSeq


class IPANormalizer(BasePlugin):
    """Normalizador de tokens IPA.
    
    Coordina la normalización Unicode, validación contra inventario,
    y colapso alofónico según las reglas del pack.
    
    Parámetros
    ----------
    inventory : Inventory | None
        Inventario fonético para validación. Si es None, solo se
        aplica normalización Unicode básica.
    collapse_oov : bool
        Si True, los tokens OOV se marcan pero no se descartan.
    oov_marker : str
        Marcador para tokens fuera del vocabulario.
    """
    
    def __init__(
        self,
        inventory: Optional[Inventory] = None,
        *,
        collapse_oov: bool = True,
        oov_marker: str = "<?>"
    ) -> None:
        self._inventory = inventory
        self._collapse_oov = collapse_oov
        self._oov_marker = oov_marker
        
        # Reglas de colapso alofónico (phone -> fonema base)
        self._allophone_rules: dict[str, str] = {}
    
    def set_inventory(self, inventory: Inventory) -> None:
        """Establecer o cambiar el inventario.
        
        Parámetros
        ----------
        inventory : Inventory
            Nuevo inventario a usar.
        """
        self._inventory = inventory
    
    def add_allophone_rule(self, allophone: str, phoneme: str) -> None:
        """Agregar una regla de colapso alofónico.
        
        Parámetros
        ----------
        allophone : str
            Alófono a colapsar.
        phoneme : str
            Fonema base al que se colapsa.
        """
        self._allophone_rules[allophone] = phoneme
    
    def load_allophone_rules(self, rules: dict[str, str]) -> None:
        """Cargar múltiples reglas de colapso alofónico.
        
        Parámetros
        ----------
        rules : dict[str, str]
            Mapeo de alófonos a fonemas base.
        """
        self._allophone_rules.update(rules)
    
    async def normalize(
        self,
        tokens: TokenSeq,
        **kw: Any,
    ) -> list[Token]:
        """Normalizar una secuencia de tokens IPA.
        
        Parámetros
        ----------
        tokens : TokenSeq
            Secuencia de tokens a normalizar.
            
        Retorna
        -------
        list[Token]
            Tokens normalizados.
        """
        result: list[Token] = []
        
        for token in tokens:
            normalized = self._normalize_token(token)
            if normalized:
                result.append(normalized)
        
        return result
    
    def _normalize_token(self, token: Token) -> Optional[Token]:
        """Normalizar un token individual.
        
        Pasos:
        1. Normalización Unicode
        2. Mapeo canónico (si hay inventario)
        3. Colapso alofónico
        4. Validación OOV
        """
        # 1. Normalización Unicode básica
        normalized = normalize_unicode(str(token).strip())
        if not normalized:
            return None
        
        # 2. Mapeo canónico desde inventario
        if self._inventory:
            normalized = self._inventory.get_canonical(normalized)
        
        # 3. Colapso alofónico
        if normalized in self._allophone_rules:
            normalized = self._allophone_rules[normalized]
        
        # 4. Validación OOV
        if self._inventory and not self._inventory.is_valid_phone(normalized):
            if self._collapse_oov:
                # Marcar pero mantener
                return f"{self._oov_marker}{normalized}"
            # Token válido a pesar de OOV - mantener sin marcar
        
        return normalized
    
    async def collapse_allophones(
        self,
        tokens: TokenSeq,
        rules: Optional[dict[str, str]] = None,
        **kw: Any,
    ) -> list[Token]:
        """Colapsar alófonos según reglas específicas.
        
        Parámetros
        ----------
        tokens : TokenSeq
            Secuencia de tokens.
        rules : dict[str, str] | None
            Reglas de colapso. Si None, usa las reglas cargadas.
            
        Retorna
        -------
        list[Token]
            Tokens con alófonos colapsados.
        """
        collapse_rules = rules or self._allophone_rules
        
        result: list[Token] = []
        for token in tokens:
            token_str = str(token)
            if token_str in collapse_rules:
                result.append(collapse_rules[token_str])
            else:
                result.append(token_str)
        
        return result
    
    async def validate_tokens(
        self,
        tokens: TokenSeq,
        **kw: Any,
    ) -> dict[str, Any]:
        """Validar tokens contra el inventario.
        
        Parámetros
        ----------
        tokens : TokenSeq
            Secuencia de tokens a validar.
            
        Retorna
        -------
        dict
            Resultado con 'valid', 'oov_tokens', 'oov_count'.
        """
        if not self._inventory:
            return {
                "valid": True,
                "oov_tokens": [],
                "oov_count": 0,
                "message": "No inventory loaded - all tokens accepted",
            }
        
        oov = self._inventory.get_oov_phones(list(tokens))
        
        return {
            "valid": len(oov) == 0,
            "oov_tokens": oov,
            "oov_count": len(oov),
            "total_tokens": len(list(tokens)),
        }
    
    def normalize_sync(self, tokens: Sequence[str]) -> list[str]:
        """Versión síncrona de normalize para uso directo.
        
        Parámetros
        ----------
        tokens : Sequence[str]
            Secuencia de tokens.
            
        Retorna
        -------
        list[str]
            Tokens normalizados.
        """
        result: list[str] = []
        for token in tokens:
            normalized = self._normalize_token(token)
            if normalized:
                result.append(normalized)
        return result


# Reglas de colapso alofónico comunes para español
SPANISH_ALLOPHONE_RULES = {
    # Oclusivas sonoras en posición intervocálica → fricativas
    "β": "b",   # bilabial fricativa → oclusiva
    "ð": "d",   # dental fricativa → oclusiva
    "ɣ": "g",   # velar fricativa → oclusiva
    
    # NOTA: ɾ (tap) y r (trill) son fonemas DISTINTOS en español
    # (pero /ˈpeɾo/ ≠ perro /ˈpero/) — NO colapsar.
    
    # Nasales: ŋ es alofónico en español (solo ante velares)
    "ɱ": "m",   # labiodental nasal → bilabial
    "ŋ": "n",   # velar nasal → alveolar (ante velar)
}

# Reglas de colapso alofónico comunes para inglés
ENGLISH_ALLOPHONE_RULES = {
    # Aproximantes
    "ɾ": "t",   # flap → /t/ (ej: "butter")
    "ɫ": "l",   # dark L → clear L
    
    # Glotalización
    "ʔ": "t",   # glottal stop como alófono de /t/
    
    # NOTA: ŋ es un fonema DISTINTO en inglés
    # (sing /sɪŋ/ ≠ sin /sɪn/) — NO colapsar.
    
    # Nasales (solo alofónicas ante consonantes homorgánicas)
    "ɱ": "m",   # labiodental ante /f,v/
}


__all__ = [
    "IPANormalizer",
    "SPANISH_ALLOPHONE_RULES",
    "ENGLISH_ALLOPHONE_RULES",
]
