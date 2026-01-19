"""Gestión de inventarios fonéticos desde packs.

Carga y valida inventarios IPA definidos en archivos YAML de los packs,
proporcionando métodos para verificar y mapear tokens.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Set

import yaml

from ipa_core.errors import ValidationError


class Inventory:
    """Inventario fonético cargado desde un pack.
    
    Atributos
    ---------
    language : str
        Código de idioma (ej: "en", "es").
    accent : str | None
        Variante/acento (ej: "en-us", "es-mx").
    consonants : set[str]
        Conjunto de consonantes válidas.
    vowels : set[str]
        Conjunto de vocales válidas.
    diphthongs : set[str]
        Conjunto de diptongos válidos.
    diacritics : set[str]
        Conjunto de diacríticos permitidos.
    suprasegmentals : set[str]
        Marcadores suprasegmentales (stress, pausa).
    """
    
    def __init__(
        self,
        language: str,
        consonants: Set[str],
        vowels: Set[str],
        *,
        accent: Optional[str] = None,
        diphthongs: Optional[Set[str]] = None,
        diacritics: Optional[Set[str]] = None,
        suprasegmentals: Optional[Set[str]] = None,
        aliases: Optional[Dict[str, str]] = None,
    ) -> None:
        self.language = language
        self.accent = accent
        self.consonants = consonants
        self.vowels = vowels
        self.diphthongs = diphthongs or set()
        self.diacritics = diacritics or set()
        self.suprasegmentals = suprasegmentals or set()
        self._aliases = aliases or {}
        
        # Construir conjunto completo de símbolos válidos
        self._all_phones = (
            self.consonants | self.vowels | self.diphthongs
        )
        self._all_symbols = (
            self._all_phones | self.diacritics | self.suprasegmentals
        )
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Inventory":
        """Cargar inventario desde archivo YAML.
        
        Parámetros
        ----------
        path : Path
            Ruta al archivo inventory.yaml.
            
        Retorna
        -------
        Inventory
            Inventario cargado y validado.
            
        Raises
        ------
        ValidationError
            Si el archivo no existe o tiene formato inválido.
        """
        if not path.exists():
            raise ValidationError(f"Inventory file not found: {path}")
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML in inventory: {e}") from e
        
        if not isinstance(data, dict):
            raise ValidationError("Inventory must be a YAML dictionary")
        
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "Inventory":
        """Construir desde diccionario."""
        language = data.get("language")
        if not language:
            raise ValidationError("Inventory must specify 'language'")
        
        inv = data.get("inventory", {})
        
        consonants = set(inv.get("consonants", []))
        vowels = set(inv.get("vowels", []))
        
        if not consonants and not vowels:
            raise ValidationError("Inventory must have consonants or vowels")
        
        return cls(
            language=language,
            consonants=consonants,
            vowels=vowels,
            accent=data.get("accent"),
            diphthongs=set(inv.get("diphthongs", [])),
            diacritics=set(inv.get("diacritics", [])),
            suprasegmentals=set(inv.get("suprasegmentals", [])),
            aliases=data.get("aliases"),
        )
    
    def is_valid_phone(self, phone: str) -> bool:
        """Verificar si un fonema es válido en este inventario.
        
        Parámetros
        ----------
        phone : str
            Fonema a verificar.
            
        Retorna
        -------
        bool
            True si el fonema está en el inventario.
        """
        return phone in self._all_phones
    
    def is_valid_symbol(self, symbol: str) -> bool:
        """Verificar si un símbolo (fonema o diacrítico) es válido.
        
        Parámetros
        ----------
        symbol : str
            Símbolo a verificar.
            
        Retorna
        -------
        bool
            True si el símbolo está en el inventario.
        """
        return symbol in self._all_symbols
    
    def get_canonical(self, token: str) -> str:
        """Obtener la forma canónica de un token.
        
        Si existe un alias definido, retorna el mapeo canónico.
        De lo contrario, retorna el token sin cambios.
        
        Parámetros
        ----------
        token : str
            Token a normalizar.
            
        Retorna
        -------
        str
            Forma canónica del token.
        """
        return self._aliases.get(token, token)
    
    def get_oov_phones(self, tokens: list[str]) -> list[str]:
        """Obtener tokens fuera del vocabulario (OOV).
        
        Parámetros
        ----------
        tokens : list[str]
            Lista de tokens a verificar.
            
        Retorna
        -------
        list[str]
            Tokens que no están en el inventario.
        """
        return [t for t in tokens if not self.is_valid_phone(t)]
    
    @property
    def all_phones(self) -> Set[str]:
        """Conjunto de todos los fonemas válidos."""
        return self._all_phones.copy()
    
    def __repr__(self) -> str:
        accent_str = f"/{self.accent}" if self.accent else ""
        return (
            f"Inventory({self.language}{accent_str}, "
            f"consonants={len(self.consonants)}, "
            f"vowels={len(self.vowels)})"
        )


__all__ = ["Inventory"]
