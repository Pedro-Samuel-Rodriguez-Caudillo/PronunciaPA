"""Language Pack Plugin - Carga configuración fonológica de un dialecto.

Un Language Pack contiene:
- Inventario fonético (fonemas/alófonos válidos)
- Gramática fonológica (reglas de derivación/colapso)
- Perfiles de scoring por modo
- Excepciones léxicas
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from ipa_core.plugins.base import BasePlugin
from ipa_core.phonology.inventory import PhoneticInventory
from ipa_core.phonology.grammar import PhonologicalGrammar
from ipa_core.errors import NotReadyError, ValidationError


@dataclass
class ScoringProfile:
    """Perfil de scoring para un modo específico.
    
    Atributos
    ---------
    mode : str
        Nombre del modo (casual, objective, phonetic).
    phoneme_error_weight : float
        Peso para errores de fonema.
    allophone_error_weight : float
        Peso para errores de alófono (menor que fonema).
    prosody_weight : float
        Peso para errores prosódicos.
    acceptable_variants : Set[tuple]
        Pares (target, variant) que se aceptan como equivalentes.
    tolerance : str
        Nivel de tolerancia: low, medium, high.
    """
    mode: str
    phoneme_error_weight: float = 1.0
    allophone_error_weight: float = 0.3
    prosody_weight: float = 0.5
    acceptable_variants: Set[tuple] = field(default_factory=set)
    tolerance: str = "medium"
    
    @classmethod
    def from_yaml(cls, path: Path, mode: str) -> "ScoringProfile":
        """Cargar perfil desde YAML."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        variants = set()
        for pair in data.get("acceptable_variants", []):
            if len(pair) == 2:
                variants.add((pair[0], pair[1]))
        
        return cls(
            mode=mode,
            phoneme_error_weight=data.get("phoneme_error_weight", 1.0),
            allophone_error_weight=data.get("allophone_error_weight", 0.3),
            prosody_weight=data.get("prosody_weight", 0.5),
            acceptable_variants=variants,
            tolerance=data.get("tolerance", "medium"),
        )
    
    @classmethod
    def default(cls, mode: str) -> "ScoringProfile":
        """Perfil por defecto para un modo."""
        defaults = {
            "casual": cls(
                mode="casual",
                phoneme_error_weight=1.0,
                allophone_error_weight=0.1,  # Muy permisivo
                prosody_weight=0.2,
                tolerance="high",
            ),
            "objective": cls(
                mode="objective",
                phoneme_error_weight=1.0,
                allophone_error_weight=0.3,
                prosody_weight=0.5,
                tolerance="medium",
            ),
            "phonetic": cls(
                mode="phonetic",
                phoneme_error_weight=1.0,
                allophone_error_weight=0.8,  # Casi igual que fonema
                prosody_weight=0.7,
                tolerance="low",
            ),
        }
        return defaults.get(mode, cls(mode=mode))


@dataclass
class LanguagePackManifest:
    """Metadata del Language Pack."""
    id: str
    version: str
    language: str
    dialect: str
    description: str = ""
    license: str = ""
    sources: List[Dict[str, str]] = field(default_factory=list)
    
    @classmethod
    def from_yaml(cls, path: Path) -> "LanguagePackManifest":
        """Cargar manifest desde YAML."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return cls(
            id=data.get("id", ""),
            version=data.get("version", "0.0.0"),
            language=data.get("language", ""),
            dialect=data.get("dialect", ""),
            description=data.get("description", ""),
            license=data.get("license", ""),
            sources=data.get("sources", []),
        )


class LanguagePackPlugin(BasePlugin):
    """Plugin para cargar y gestionar un Language Pack.
    
    Un Language Pack provee la configuración fonológica completa
    para un idioma/dialecto específico.
    """
    
    def __init__(self, pack_path: Path) -> None:
        """Inicializar plugin.
        
        Parámetros
        ----------
        pack_path : Path
            Ruta al directorio del pack.
        """
        self._path = Path(pack_path)
        self._manifest: Optional[LanguagePackManifest] = None
        self._inventory: Optional[PhoneticInventory] = None
        self._grammar: Optional[PhonologicalGrammar] = None
        self._scoring_profiles: Dict[str, ScoringProfile] = {}
        self._exceptions: Dict[str, str] = {}
        self._ready = False
    
    async def setup(self) -> None:
        """Cargar todos los recursos del pack."""
        if not self._path.exists():
            raise ValidationError(f"Pack directory not found: {self._path}")
        
        # 1. Cargar manifest
        manifest_path = self._path / "manifest.yaml"
        if not manifest_path.exists():
            # Fallback a pack.yaml
            manifest_path = self._path / "pack.yaml"
        
        if manifest_path.exists():
            self._manifest = LanguagePackManifest.from_yaml(manifest_path)
        else:
            raise ValidationError(f"No manifest found in {self._path}")
        
        # 2. Cargar inventario
        inventory_path = self._path / "inventory.yaml"
        if inventory_path.exists():
            self._inventory = PhoneticInventory.from_yaml(inventory_path)
        
        # 3. Cargar gramática (reglas fonológicas)
        rules_path = None
        for rules_name in ["phonological_rules.yaml", "rules.yaml", "grammar.yaml"]:
            candidate = self._path / rules_name
            if candidate.exists():
                rules_path = candidate
                break
        
        if rules_path:
            self._grammar = PhonologicalGrammar.from_yaml(rules_path, self._inventory)
        else:
            # Crear gramática vacía
            self._grammar = PhonologicalGrammar(
                language=self._manifest.language,
                dialect=self._manifest.dialect,
                inventory=self._inventory,
            )
        
        # 4. Cargar perfiles de scoring
        scoring_dir = self._path / "scoring"
        if scoring_dir.exists():
            for mode in ["casual", "objective", "phonetic"]:
                mode_path = scoring_dir / f"{mode}.yaml"
                if mode_path.exists():
                    self._scoring_profiles[mode] = ScoringProfile.from_yaml(mode_path, mode)
                else:
                    self._scoring_profiles[mode] = ScoringProfile.default(mode)
        else:
            # Usar perfiles por defecto
            for mode in ["casual", "objective", "phonetic"]:
                self._scoring_profiles[mode] = ScoringProfile.default(mode)
        
        # 5. Cargar excepciones
        exceptions_path = self._path / "exceptions.yaml"
        if exceptions_path.exists():
            with open(exceptions_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self._exceptions = data.get("exceptions", {})
        
        self._ready = True
    
    async def teardown(self) -> None:
        """Liberar recursos."""
        self._ready = False
        self._manifest = None
        self._inventory = None
        self._grammar = None
        self._scoring_profiles = {}
        self._exceptions = {}
    
    def _check_ready(self) -> None:
        """Verificar que el plugin está listo."""
        if not self._ready:
            raise NotReadyError("LanguagePackPlugin not initialized. Call setup() first.")
    
    @property
    def id(self) -> str:
        """ID del pack."""
        self._check_ready()
        return self._manifest.id if self._manifest else ""
    
    @property
    def language(self) -> str:
        """Código de idioma."""
        self._check_ready()
        return self._manifest.language if self._manifest else ""
    
    @property
    def dialect(self) -> str:
        """Código de dialecto."""
        self._check_ready()
        return self._manifest.dialect if self._manifest else ""
    
    def get_inventory(self) -> PhoneticInventory:
        """Obtener inventario fonético."""
        self._check_ready()
        if self._inventory is None:
            raise ValidationError("Inventory not loaded")
        return self._inventory
    
    def get_grammar(self) -> PhonologicalGrammar:
        """Obtener gramática fonológica."""
        self._check_ready()
        if self._grammar is None:
            raise ValidationError("Grammar not loaded")
        return self._grammar
    
    def get_scoring_profile(self, mode: str) -> ScoringProfile:
        """Obtener perfil de scoring para un modo."""
        self._check_ready()
        if mode not in self._scoring_profiles:
            return ScoringProfile.default(mode)
        return self._scoring_profiles[mode]
    
    def get_exception(self, word: str) -> Optional[str]:
        """Obtener IPA de excepción para una palabra."""
        self._check_ready()
        return self._exceptions.get(word.lower())
    
    def derive(self, phonemic: str, *, mode: str = "objective") -> str:
        """Derivar forma fonética desde fonémica.
        
        Convenience method que delega a la gramática.
        """
        self._check_ready()
        return self._grammar.derive(phonemic, mode=mode)
    
    def collapse(self, phonetic: str, *, mode: str = "objective") -> str:
        """Colapsar forma fonética a fonémica.
        
        Convenience method que delega a la gramática.
        """
        self._check_ready()
        return self._grammar.collapse(phonetic, mode=mode)


__all__ = [
    "ScoringProfile",
    "LanguagePackManifest",
    "LanguagePackPlugin",
]
