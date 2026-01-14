"""Tipos compartidos para el microkernel.

Descripción
-----------
Define tipos inmutables para el intercambio de datos entre puertos y el
`Kernel`.

Estado: Implementación pendiente de validación (se puede añadir más adelante).

TODO
----
- Mapear claves externas del YAML a nombres internos: `del` del YAML debe
  convertirse a `del_` en `CompareWeights` para evitar conflicto con palabras
  reservadas de Python.
- Añadir detalles básicos de audio que ayuden a depurar (por ejemplo,
  profundidad de bits y formato contenedor) sin complejidad extra.
- Documentar en una tabla los campos obligatorios y opcionales de cada tipo.
- Evaluar un validador de esquemas sencillo cuando exista lógica (por ejemplo,
  `pydantic`), manteniendo el código legible para principiantes.

Diseño sugerido
---------------
- Data Transfer Objects (DTO): estos `TypedDict` son estructuras de datos
  simples para transportar información entre capas sin lógica.
"""
from __future__ import annotations

from typing import Any, Literal, Optional, Sequence, TypedDict


Token = str  # Representa un símbolo o token IPA individual (por ejemplo, "a", "ʃ").
TokenSeq = Sequence[Token]  # Secuencia ordenada de tokens IPA (la transcripción).


class AudioInput(TypedDict):
    """Describe un audio de entrada para el sistema.

    - path: ruta al archivo de audio en disco.
    - sample_rate: frecuencia de muestreo en Hz (p. ej., 16000).
    - channels: número de canales (1 para mono, 2 para estéreo).
    """

    path: str
    sample_rate: int
    channels: int


class ASRResult(TypedDict, total=False):
    """Resultado producido por un backend de ASR.

    - tokens: lista de tokens IPA resultantes.
    - raw_text: texto sin procesar si el backend lo produce.
    - time_stamps: lista de tuplas (inicio, fin) por token o segmento.
    - meta: información adicional útil para depurar (modelo, versión, etc.).
    """

    tokens: list[Token]
    raw_text: str
    time_stamps: list[tuple[float, float]]
    meta: dict[str, Any]


class TextRefResult(TypedDict, total=False):
    """Resultado producido por un proveedor de texto de referencia.

    - tokens: lista de tokens IPA resultantes.
    - meta: información adicional útil para depurar.
    """

    tokens: list[Token]
    meta: dict[str, Any]


class TTSResult(TypedDict, total=False):
    """Resultado producido por un backend TTS.

    - audio: descriptor del archivo de audio generado.
    - meta: información adicional útil para depurar.
    """

    audio: AudioInput
    meta: dict[str, Any]


class PreprocessorResult(TypedDict, total=False):
    """Resultado producido por un preprocesador.

    - audio: audio procesado (si aplica).
    - tokens: tokens procesados (si aplica).
    - meta: información adicional útil para depurar.
    """

    audio: AudioInput
    tokens: list[Token]
    meta: dict[str, Any]


class CompareWeights(TypedDict, total=False):
    """Pesos aplicados a cada operación de edición.

    - sub: costo de sustituciones.
    - ins: costo de inserciones.
    - del_: costo de eliminaciones (se usa `del_` para evitar conflicto con `del`).
    """

    sub: float
    ins: float
    del_: float  # alias interno para "del"


class EditOp(TypedDict):
    """Describe una operación de edición entre referencia y predicción.

    - op: tipo de operación: eq (=), sub (sustitución), ins (inserción), del (borrado).
    - ref: token de referencia (o None si es inserción).
    - hyp: token reconocido (o None si es borrado).
    """

    op: Literal["eq", "sub", "ins", "del"]
    ref: Optional[Token]
    hyp: Optional[Token]


class CompareResult(TypedDict, total=False):
    """Métricas y detalle de la comparación entre dos secuencias IPA.

    - per: Phone Error Rate en el rango [0, 1].
    - ops: lista con las operaciones de edición calculadas.
    - alignment: alineación paso a paso (pares ref/hyp o None).
    - meta: información adicional para trazabilidad y depuración.
    """

    per: float
    ops: list[EditOp]
    alignment: list[tuple[Optional[Token], Optional[Token]]]
    meta: dict[str, Any]


class RunOptions(TypedDict, total=False):
    """Opciones comunes para ejecutar el pipeline.

    - lang: código de idioma (por ejemplo, "es", "en").
    - weights: pesos para la comparación (si se usa un comparador).
    """

    lang: Optional[str]
    weights: CompareWeights
