# TODO - ipa_core

- [ ] Definir entry points reales en pyproject.toml para los plugins disponibles.
- [ ] Crear configuracion centralizada para rutas de modelos y recursos externos.
- [ ] Integrar flujo de captura de audio (CLI/GUI) que grabe al usuario y ejecute el pipeline completo.
- [ ] Automatizar pruebas integrales que cubran audio -> IPA -> comparacion.
- [ ] Revisar licencias de modelos/recursos antes de integrarlos al microkernel.
- [ ] Publicar artefacto consolidado (rueda/imagen) para compartir con el equipo.

## Módulos propuestos (paquetes)

- ipa_core/kernel
  - `core.py`: `Kernel`, `create_kernel`, `run`.
  - `errors.py`: excepciones específicas.
- ipa_core/ports
  - `asr.py`: `ASRBackend`.
  - `textref.py`: `TextRefProvider`.
  - `compare.py`: `Comparator`.
  - `preprocess.py`: `Preprocessor`.
- ipa_core/pipeline
  - `runner.py`: orquestación audio→preprocess→asr→textref→compare.
- ipa_core/config
  - `schema.py`: TypedDict/`pydantic` para YAML.
  - `loader.py`: carga, validación, defaults.
- ipa_core/plugins
  - `discovery.py`: entry points / registro.
  - `registry.py`: resolución por `name`.

## Contratos (resumen)

- `Kernel.run(audio, text, opts) -> CompareResult` usa puertos:
  - `Preprocessor.process_audio(audio) -> audio'`
  - `ASRBackend.transcribe(audio', lang?) -> ASRResult.tokens`
  - `TextRefProvider.to_ipa(text, lang) -> ref_tokens`
  - `Preprocessor.normalize_tokens(tokens) -> tokens'`
  - `Comparator.compare(ref_tokens', hyp_tokens') -> CompareResult`

## Config (shape)

```yaml
version: 1
backend: {name: string, params: map}
textref: {name: string, params: map}
comparator: {name: string, params: map}
options:
  lang: es
  output: json  # json|table
```
