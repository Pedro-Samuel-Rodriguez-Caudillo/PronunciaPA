# TODO - api

- [ ] Validar que el archivo de audio exista y sea soportado antes de invocar el kernel.
- [ ] Permitir configuracion desde archivo o banderas para seleccionar backend, textref y comparador.
- [ ] Anadir un comando/interfaz para grabar audio desde el microfono y guardarlo como entrada del backend.
- [ ] Capturar y formatear errores del kernel para que el CLI entregue mensajes claros al usuario.
- [ ] Agregar opcion para exportar resultados (JSON o tabla) y facilitar integracion con otras herramientas.
- [ ] Escribir pruebas end-to-end del CLI usando Typer CLIRunner.

## Módulos propuestos

- ipa_core/api/cli.py (Typer)
  - Comando `compare`: `--audio PATH --text "..." --lang es [--backend.name --textref.name --comparator.name]`.
  - Opción `--config PATH` para YAML.
  - Opción `--json` para salida en `CompareResult`.
- ipa_core/api/http.py (FastAPI)
  - Rutas v1 y manejo de errores comunes.

## Contratos CLI

- Entrada válida:
  - Audio: ruta a `.wav|.mp3` existente (validado).
  - Texto: no vacío; `--lang` requerido si no está en config.
- Salida:
  - `--json`: `CompareResult` (ver raíz `TODO.md`).
  - por defecto: tabla con PER y primeras N operaciones.

## Contratos HTTP

- `GET /health`
  - 200: `{ "status": "ok" }`.
- `POST /v1/compare`
  - Request (multipart):
    - `audio` (file)
    - `payload` (application/json):
      - `text: str`, `lang: str`, `backend?: {name, params}`, `textref?: {name, params}`, `comparator?: {name, params}`
  - Response 200 (application/json): `CompareResult`.
  - 4xx/5xx: `{ "error": { "code": str, "message": str } }`.

## Errores (mapping estándar)

- `FileNotFound` → 400 (CLI: exit code 2)
- `UnsupportedFormat` → 415
- `ValidationError` → 422
- `InternalError` → 500
