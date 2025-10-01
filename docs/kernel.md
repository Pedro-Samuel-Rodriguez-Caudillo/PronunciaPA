# Núcleo y configuración de plugins

El **Kernel** de PronunciaPA actúa como orquestador de los plugins que
componen el pipeline principal (ASR → TextRef → Comparator). Esta versión
implementa un *stub* de ejecución que valida la configuración y carga los
plugins registrados mediante *entry points* de Python.

## KernelConfig

La clase `KernelConfig` se define como un `dataclass` con los campos:

| Campo         | Descripción                                             | Valor por defecto |
|---------------|---------------------------------------------------------|-------------------|
| `asr_backend` | Backend ASR que convierte audio a IPA (`ipa_core.backends.asr`) | `null`            |
| `textref`     | Conversor de texto a IPA (`ipa_core.plugins.textref`)   | `noop`            |
| `comparator`  | Comparador de cadenas IPA (`ipa_core.plugins.compare`)  | `noop`            |
| `preprocessor`| Preprocesador opcional (`ipa_core.plugins.preprocess`)  | `None`            |

La configuración puede declararse directamente en YAML usando un bloque
`plugins` o en formato plano. Ejemplo:

```yaml
plugins:
  asr_backend: null
  textref: noop
  comparator: noop
  preprocessor: null
```

El método `KernelConfig.from_yaml` carga el archivo y valida que contenga un
mapeo. Para inspeccionar la configuración efectiva se puede invocar
`KernelConfig.to_mapping()`.

## Gestión de plugins

Los plugins se descubren mediante los *entry points* definidos en
`pyproject.toml`. Los grupos actualmente soportados son:

- `ipa_core.backends.asr` (alias CLI `asr`)
- `ipa_core.plugins.textref` (alias CLI `textref`)
- `ipa_core.plugins.compare` (alias CLI `comparator`)
- `ipa_core.plugins.preprocess` (alias CLI `preprocessor`)

La utilidad `ipa plugins list` muestra los plugins disponibles, permitiendo
filtrar por grupo con `--group`.

## Ejecución del pipeline (stub)

El comando `ipa run` instancia el kernel usando el archivo de configuración y
recorre el directorio de entrada indicado. Como aún no existe lógica de
procesamiento fonético, la salida se limita a un reporte con la configuración
activa y los archivos detectados. Para validar únicamente la configuración se
puede usar `--dry-run`.

Ejemplo:

```bash
ipa run --config config/ipa_kernel.yaml --input inputs/ --dry-run --show-config
```

Esta ejecución no procesa audio, pero garantiza que los plugins se cargan de
forma correcta y que la configuración es válida.
