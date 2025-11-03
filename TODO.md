# TODO general (reset)

- [ ] Definir el microkernel mínimo (interfaz, ciclo de vida, carga de plugins) sin implementación funcional.
- [ ] Acordar los puertos (interfaces) iniciales: ASR, TextRef, Comparator y Preprocessor.
- [ ] Especificar formato de configuración (YAML) y validaciones mínimas.
- [ ] Diseñar el CLI mínimo (sin lógica): comandos y opciones esperadas.
- [ ] Definir API HTTP mínima (rutas y contratos) sin implementación.
- [ ] Documentar decisiones en `docs/backlog.md` y desglosar en TODOs por módulo.
- [ ] Alinear estructura de `frontend/` con la API (sin código aún).
- [ ] Criterios de “listo para empezar a codificar” (DoD v0): revisados y aprobados.

## Módulos mínimos (microkernel y puertos)

- ipa_core/kernel
  - `Kernel`: ciclo de vida y orquestación del pipeline.
  - `create_kernel(config) -> Kernel`: arma puertos y adapta plugins.
  - `run(audio: AudioInput, text: str, opts: RunOptions) -> CompareResult`.
- ipa_core/ports
  - `ASRBackend`: puerto de transcripción a IPA desde audio.
  - `TextRefProvider`: puerto de referencia texto→IPA.
  - `Comparator`: puerto de comparación (PER y alineación).
  - `Preprocessor`: normalización de audio y tokens IPA.
- ipa_core/config
  - Carga/validación de YAML y valores por defecto.
- ipa_core/plugins
  - Descubrimiento de entry points y registro manual.
- ipa_core/pipeline
  - Orquestador de pasos (preproceso→ASR→textref→comparación).
- ipa_core/errors
  - Excepciones específicas de kernel y puertos.

## Contratos globales (borrador)

```python
from typing import Protocol, TypedDict, Sequence, Literal, Optional

Token = str  # IPA token normalizado
TokenSeq = Sequence[Token]

class AudioInput(TypedDict):
    path: str  # ruta a archivo .wav/.mp3
    sample_rate: int
    channels: int

class ASRResult(TypedDict):
    tokens: list[Token]
    raw_text: str
    time_stamps: Optional[list[tuple[float, float]]]
    meta: dict

class CompareWeights(TypedDict, total=False):
    sub: float
    ins: float
    del_: float

class EditOp(TypedDict):
    op: Literal['eq','sub','ins','del']
    ref: Optional[Token]
    hyp: Optional[Token]

class CompareResult(TypedDict):
    per: float
    ops: list[EditOp]
    alignment: list[tuple[Optional[Token], Optional[Token]]]
    meta: dict

class Preprocessor(Protocol):
    def process_audio(self, audio: AudioInput) -> AudioInput: ...
    def normalize_tokens(self, tokens: TokenSeq) -> list[Token]: ...

class ASRBackend(Protocol):
    def transcribe(self, audio: AudioInput, *, lang: Optional[str] = None, **kw) -> ASRResult: ...

class TextRefProvider(Protocol):
    def to_ipa(self, text: str, *, lang: str, **kw) -> list[Token]: ...

class Comparator(Protocol):
    def compare(self, ref: TokenSeq, hyp: TokenSeq, *, weights: Optional[CompareWeights] = None, **kw) -> CompareResult: ...
```

## Configuración (YAML mínimo)

```yaml
version: 1
backend:
  name: whisper_ipa
  params:
    device: cpu  # cpu|cuda
textref:
  name: phonemizer
  params:
    lang: es
comparator:
  name: levenshtein
  params:
    sub: 1.0
    ins: 1.0
    del: 1.0
```

## API/CLI (contratos de alto nivel)

- CLI `ipa` (Typer):
  - `ipa compare --audio PATH --text "..." --lang es [--backend ... --textref ... --comparator ...]`
  - Salida: tabla o `--json` con `CompareResult`.
- API HTTP (FastAPI):
  - `POST /v1/compare` multipart (audio + JSON): responde `CompareResult`.
  - `GET /health` retorna `{status: "ok"}`.

## DoD v0 (criterios)

- Contratos anteriores están documentados en TODOs por paquete.
- Config YAML validado y ejemplos en `configs/`.
- CLI y API con rutas/comandos definidos (stubs) y pruebas de contrato.
