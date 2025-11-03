# TODO - frontend

- [ ] Alinear contratos con la API HTTP (rutas, payloads, respuestas).
- [ ] Decidir stack (SPA mínima o server-rendered) y estructura.
- [ ] Definir flujos: carga de audio, ingreso de texto, visualización de métricas.
- [ ] Integrar diseño accesible y responsive.

## Contratos con API

- `POST /v1/compare` (multipart)
  - Envía `audio` + `payload{text,lang,backend?,textref?,comparator?}`.
  - Recibe `CompareResult` con `per`, `ops`, `alignment`.
- `GET /health` → `{status:"ok"}`.

## Módulos/Flujos propuestos

- `pages/Compare`:
  - Carga de audio, entrada de texto, selector de idioma.
  - Selector de backend/textref/comparator (opcional avanzado).
  - Vista de resultados (PER, alineación, detalles de ops).
- `lib/api.ts` o similar: cliente tipado de la API.
