# Sample dataset

Esta carpeta describe un dataset mínimo para validar el pipeline de extremo a
extremo sin necesidad de descargar datos adicionales.

## Estructura de directorios

```
data/
└── sample/
    ├── metadata.csv
    └── *.wav  # archivos generados localmente
```

Los audios WAV no se versionan en el repositorio para evitar binarios en los
commits. Puedes generarlos en cualquier momento con el script incluido en
`scripts/generate_sample_dataset.py`.

Cada archivo de audio es un tono sintético en formato WAV (PCM de 16 bits, 16
kHz, mono) con una duración inferior a 3 segundos. Los tonos sirven únicamente
como sustitutos ligeros de grabaciones reales para pruebas locales.

## Formato de metadatos

El archivo `metadata.csv` utiliza codificación UTF-8 y tiene las columnas:

- `audio_path`: Ruta relativa al directorio `data/sample/` del archivo de audio.
- `text`: Texto asociado al audio (en este ejemplo describe el tono).
- `lang`: Código de idioma ISO 639-1.

Ejemplo:

```
audio_path,text,lang
sample_01.wav,Tono de referencia en 440 Hz,es
```

## Generación de audios

1. Asegúrate de haber instalado las dependencias base del proyecto.
2. Ejecuta:

   ```bash
   python scripts/generate_sample_dataset.py
   ```

   El script crea tonos senoidales que cumplen con las especificaciones
   (16 kHz, 16-bit PCM). Usa `--overwrite` para regenerar los archivos si ya
   existen.

## Validación

Para comprobar que el dataset cumple los requisitos básicos se incluye el
script `scripts/validate_dataset.py`. Valida la estructura del CSV, la
existencia de los audios y sus propiedades principales.

```bash
python scripts/validate_dataset.py data/sample/metadata.csv
```

Si falta algún audio el script emitirá un error indicando que ejecutes el
script de generación. Cuando todo esté correcto el comando mostrará
`Validation passed ✅`.
