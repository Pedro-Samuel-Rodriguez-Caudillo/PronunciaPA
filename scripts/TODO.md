# TODO - scripts

- [ ] Script de bootstrap del entorno (solo cuando existan dependencias definidas).
- [ ] Scripts de mantenimiento (lint/test/build) una vez existan binarios/CLI.
- [ ] Generadores de datos de prueba (si aplica) fuera del repositorio principal.

## Scripts propuestos

- `scripts/bootstrap.sh`: crea venv, instala deps (cuando existan), valida Python>=3.10.
- `scripts/lint.sh`: hooks para ruff/black/mypy (si procede).
- `scripts/test.sh`: orquesta `pytest -q` con variables mínimas.
- `scripts/dev_api.sh`: arranca API (uvicorn) con reload.
