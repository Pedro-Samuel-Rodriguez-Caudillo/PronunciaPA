"""Puerto Preprocessor (audio/tokens -> normalización).

Patrón sugerido
---------------
- Chain of Responsibility: permite encadenar pasos simples de normalización.
- Template Method: define un esqueleto de pasos que pueden especializarse.

VAD básico en process_audio
---------------------------
Comportamiento recomendado:
1. NO recortar por defecto (VAD deshabilitado)
2. Si se habilita VAD: recortar silencios > 500ms al inicio/final
3. VAD avanzado (segmentación): solo cuando `segmentation=True`

Orden de normalización de tokens
--------------------------------
La normalización de tokens IPA DEBE seguir este orden:
1. Remover espacios duplicados y trim
2. Case-folding (IPA es case-sensitive para algunos símbolos)
3. Normalizar diacríticos a forma NFC unicode
4. Colapsar alófonos según Language Pack (si aplica)
5. Remover tokens OOV (out-of-vocabulary) o marcarlos

Garantía de idempotencia
------------------------
`normalize_tokens(normalize_tokens(tokens)) == normalize_tokens(tokens)`
Las implementaciones DEBEN garantizar que aplicar la función dos veces
produce el mismo resultado que aplicarla una vez.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ipa_core.types import AudioInput, PreprocessorResult, TokenSeq


@runtime_checkable
class Preprocessor(Protocol):
    """Define operaciones simples para preparar audio y tokens.

    Separar audio y tokens facilita pruebas y reemplazos puntuales.
    Debe soportar el ciclo de vida de `BasePlugin`.
    
    Idempotencia
    ------------
    `normalize_tokens` DEBE ser idempotente: llamarla dos veces
    produce el mismo resultado que llamarla una vez.
    """

    async def setup(self) -> None:
        """Configuración inicial del plugin (asíncrona)."""
        ...

    async def teardown(self) -> None:
        """Limpieza de recursos del plugin (asíncrona)."""
        ...

    async def process_audio(self, audio: AudioInput, **kw) -> PreprocessorResult:  # noqa: D401
        """Normalizar/validar formato del audio (SR, canales, contenedor).

        Retorna `PreprocessorResult` con la clave `audio` poblada.
        
        Opciones soportadas via **kw
        ----------------------------
        - vad: bool - Habilitar recorte de silencios (default: False)
        - target_sr: int - Re-sample a esta tasa (default: 16000)
        - mono: bool - Convertir a mono (default: True)
        """
        ...

    async def normalize_tokens(self, tokens: TokenSeq, **kw) -> PreprocessorResult:  # noqa: D401
        """Normalizar tokens IPA (espacios, unicode, diacríticos).

        Retorna `PreprocessorResult` con la clave `tokens` poblada.
        
        Esta operación es IDEMPOTENTE.
        """
        ...